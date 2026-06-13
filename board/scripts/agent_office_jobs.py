"""
에이전트별 주기 작업 구현 (worker 가 호출).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
SCRIPTS = BOARD / "scripts"
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))

if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

GEMMA24_AUTHOR = os.environ.get("HOME_QA_REPLY_AUTHOR", "젬마24").strip() or "젬마24"

_PII_PATTERNS = (
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "이메일"),
    (re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"), "전화번호"),
    (re.compile(r"\d{6}-?\d{7}"), "주민번호형"),
)


def _py() -> str:
    venv = BOARD / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _run_script(script_name: str, *, timeout_sec: int | None = None) -> subprocess.CompletedProcess:
    if timeout_sec is None:
        timeout_sec = int(os.getenv("AGENT_OFFICE_SUBPROCESS_TIMEOUT", "600"))
    return subprocess.run(
        [_py(), str(SCRIPTS / script_name)],
        cwd=BOARD,
        timeout=max(30, timeout_sec),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def job_pii_scan(agent: dict) -> tuple[bool, str]:
    """최근 댓글·작업지시에서 개인정보 패턴 탐지."""
    hits: list[str] = []
    if DB_PATH.is_file():
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, content FROM comments ORDER BY id DESC LIMIT 30"
            ).fetchall()
        for cid, text in rows:
            for rx, label in _PII_PATTERNS:
                if rx.search(text or ""):
                    hits.append(f"댓글#{cid} {label} 의심")
                    break

    tasks_path = BOARD / "data" / "agent_office_tasks.json"
    if tasks_path.is_file():
        data = json.loads(tasks_path.read_text(encoding="utf-8"))
        for t in (data.get("tasks") or [])[-5:]:
            body = (t.get("body") or "") if isinstance(t, dict) else ""
            for rx, label in _PII_PATTERNS:
                if rx.search(body):
                    hits.append(f"지시#{t.get('id')} {label} 의심")
                    break

    if hits:
        msg = "PII 스캔: " + "; ".join(hits[:5])
        if len(hits) > 5:
            msg += f" 외 {len(hits) - 5}건"
        return False, msg
    return True, "PII 스캔: 최근 30댓글·지시 — 이상 없음"


def job_fact_pulse(agent: dict) -> tuple[bool, str]:
    """블로그·ETF 요약 + (선택) 웹 팩트 스냅샷."""
    post_n = 0
    if DB_PATH.is_file():
        with sqlite3.connect(DB_PATH) as conn:
            post_n = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    etf_n = 0
    etf_path = BOARD / "data" / "monthly_dividend_etfs.json"
    if etf_path.is_file():
        data = json.loads(etf_path.read_text(encoding="utf-8"))
        rows = data.get("rows") if isinstance(data, dict) else []
        etf_n = len(rows) if isinstance(rows, list) else 0

    base = f"팩트 펄스: 블로그 글 {post_n}건, 월배당 ETF {etf_n}종목"
    if os.getenv("AGENT_OFFICE_WEB_PULSE_ENABLED", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        try:
            import agent_office_web_search as ws

            if ws.web_search_enabled():
                hits = ws.search_web("한국 금융 시장 주요 이슈", limit=2)
                if hits:
                    bits = [f"{h.title[:40]} ({h.provider})" for h in hits[:2]]
                    return True, f"{base} · 웹 {len(hits)}건: {'; '.join(bits)} ({_now()})"
                return True, f"{base} · {ws.provider_status()} 결과 없음 ({_now()})"
        except Exception:
            pass
    return True, f"{base} ({_now()})"


def job_meta_digest(agent: dict) -> tuple[bool, str]:
    """피드 최근 메시지 구조화 요약."""
    import agent_office_log

    feed = agent_office_log.load_feed()
    msgs = feed.get("messages") or []
    recent = [m for m in msgs if isinstance(m, dict)][-8:]
    kinds: dict[str, int] = {}
    for m in recent:
        k = m.get("kind") or "chat"
        kinds[k] = kinds.get(k, 0) + 1
    summary = ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
    return True, f"메타 요약: 최근 {len(recent)}건 — {summary or '없음'}"


def job_draft_check(agent: dict) -> tuple[bool, str]:
    """최근 글·댓글 활동 — 글감 후보."""
    if not DB_PATH.is_file():
        return True, "DB 없음 — 글감 점검 스킵"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.created,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS cc
            FROM posts p ORDER BY p.id DESC LIMIT 5
            """
        ).fetchall()
    lines = [f"최근 글 {len(rows)}건:"]
    for r in rows:
        lines.append(f"  #{r['id']} {(r['title'] or '')[:50]} (댓글 {r['cc']})")
    return True, "\n".join(lines)


def job_site_watch(agent: dict) -> tuple[bool, str]:
    """ETF JSON·시트 데이터 신선도."""
    import etf_ops_policy

    if not etf_ops_policy.etf_ops_enabled():
        return True, "ETF 파이프라인 중지 — 신선도 점검 스킵 (" + etf_ops_policy.block_message()[:80] + "…)"
    etf_path = BOARD / "data" / "monthly_dividend_etfs.json"
    if not etf_path.is_file():
        return False, "monthly_dividend_etfs.json 없음"
    mtime = datetime.fromtimestamp(etf_path.stat().st_mtime)
    age_h = (datetime.now() - mtime).total_seconds() / 3600
    data = json.loads(etf_path.read_text(encoding="utf-8"))
    n = len(data.get("rows") or [])
    ok = age_h < 48
    msg = f"ETF 데이터 {n}종목, 마지막 수정 {mtime:%m-%d %H:%M} ({age_h:.0f}h 전)"
    return ok, msg


def job_comment_scan(agent: dict) -> tuple[bool, str]:
    """댓글 톤·FAQ 후보 (PII 제외 요약)."""
    if not DB_PATH.is_file():
        return True, "댓글 DB 없음"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT c.id, c.post_id, c.content, c.created
            FROM comments c ORDER BY c.id DESC LIMIT 10
            """
        ).fetchall()
    if not rows:
        return True, "신규 댓글 없음 — FAQ 큐 비어 있음"
    lines = [f"최근 댓글 {len(rows)}건 요약:"]
    for r in rows:
        t = re.sub(r"\s+", " ", (r["content"] or ""))[:60]
        lines.append(f"  글#{r['post_id']} 댓글#{r['id']}: {t}")
    return True, "\n".join(lines)


def job_comment_bot(agent: dict) -> tuple[bool, str]:
    if os.getenv("COMMENT_BOT_ENABLED", "0").strip() != "1":
        return True, "COMMENT_BOT_ENABLED≠1 — 스킵"
    try:
        r = _run_script("comment_reply_bot.py", timeout_sec=120)
        msg = "댓글 봇 " + ("완료" if r.returncode == 0 else f"실패({r.returncode})")
        return r.returncode == 0, msg
    except subprocess.TimeoutExpired:
        return False, "댓글 봇 timeout"


def job_etf_sync(agent: dict) -> tuple[bool, str]:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import etf_ops_policy

    if not etf_ops_policy.etf_ops_enabled():
        return True, etf_ops_policy.block_message()
    import search_etf_policy

    if not search_etf_policy.search_etf_calls_allowed():
        return True, search_etf_policy.block_message()
    if os.getenv("AGENT_OFFICE_ACTIVATE_LIGHT", "").strip() in ("1", "true", "yes"):
        return True, "ETF sync — 일일 cron(06:15)에 위임. 에이전트 ON 상태만 확인."
    try:
        r = _run_script("sync_daily_monthly_etfs.py", timeout_sec=900)
        msg = "ETF 일일 sync " + ("완료" if r.returncode == 0 else f"실패(code={r.returncode})")
        return r.returncode == 0, msg
    except subprocess.TimeoutExpired:
        return False, "ETF sync timeout"


def job_daily_conclusion(agent: dict) -> tuple[bool, str]:
    import agent_office_log
    import agent_office_tasks

    queued = len(agent_office_tasks.list_queued_tasks())
    feed = agent_office_log.load_feed()
    n = len(feed.get("messages") or [])
    return True, (
        f"일일 결론 ({_now()}): 피드 {n}건, 대기 지시 {queued}건. "
        "내일 우선 — ETF sync · 댓글 FAQ · 대표님 지시 큐."
    )


def job_heartbeat(agent: dict) -> tuple[bool, str]:
    return True, f"{agent.get('name') or agent.get('id')}: ON — {agent.get('role')}"


def _saju_stats() -> dict:
    import agent_office_saju_learn

    return agent_office_saju_learn.stats()


def job_saju_pii_scan(agent: dict) -> tuple[bool, str]:
    """검수 대기 카드에서 PII 패턴 탐지."""
    import agent_office_saju_learn

    hits: list[str] = []
    for c in agent_office_saju_learn.list_cards(status="pending", limit=20):
        body = c.get("body") or ""
        for rx, label in _PII_PATTERNS:
            if rx.search(body):
                hits.append(f"카드#{c.get('id')} {label}")
                break
    st = _saju_stats()
    if hits:
        return False, f"사주 PII: {len(hits)}건 — " + "; ".join(hits[:5])
    return True, f"사주 PII: 대기 {st['pending']}건 — 이상 없음"


def job_saju_card_pulse(agent: dict) -> tuple[bool, str]:
    st = _saju_stats()
    return True, (
        f"풀이 카드: 전체 {st['total']} · 대기 {st['pending']} · 확정 {st['confirmed']} ({_now()})"
    )


def job_saju_tag_digest(agent: dict) -> tuple[bool, str]:
    import agent_office_saju_learn

    tags: dict[str, int] = {}
    for c in agent_office_saju_learn.list_cards(limit=40):
        for t in c.get("tags") or []:
            tags[t] = tags.get(t, 0) + 1
    top = sorted(tags.items(), key=lambda x: -x[1])[:8]
    summary = ", ".join(f"{k}×{v}" for k, v in top) if top else "태그 없음"
    return True, f"명리 태그 분포: {summary}"


def job_saju_review_hint(agent: dict) -> tuple[bool, str]:
    import agent_office_saju_learn

    pending = agent_office_saju_learn.list_cards(status="pending", limit=5)
    if not pending:
        return True, "검수 대기 카드 없음"
    lines = []
    for c in pending:
        tags = c.get("tags") or []
        miss = [k for k in ("오행", "일주", "십신") if k not in tags]
        hint = f"태그 보완: {', '.join(miss)}" if miss else "태그 양호"
        lines.append(f"  #{c.get('id')} {hint}")
    return True, "명리 검수 힌트:\n" + "\n".join(lines)


def job_saju_pack_sync(agent: dict) -> tuple[bool, str]:
    import agent_office_saju_learn

    pack = agent_office_saju_learn.export_pack()
    agent_office_saju_learn.render_cursor_md()
    return True, f"pack {pack.get('card_count', 0)}건 · CURSOR_SAJU_LEARN.md 갱신"


def job_saju_daily_conclusion(agent: dict) -> tuple[bool, str]:
    st = _saju_stats()
    return True, (
        f"사주 학습 결론 ({_now()}): 확정 {st['confirmed']} · 대기 {st['pending']}. "
        "다음 — 대기 카드 검수·확정 후 pack export."
    )


def job_saju_gap_autofill(agent: dict) -> tuple[bool, str]:
    """갭 탐지 → RL 우선순위 → 카드 자동 제작·위원회."""
    try:
        import saju_card_rl_autofill as rl

        max_add = max(1, int(os.getenv("SAJU_RL_MAX_ADD", "3") or "3"))
        out = rl.run(max_add=max_add, dry_run=False)
        gaps = out.get("gaps") or {}
        added = out.get("added") or []
        planned = out.get("planned") or []
        rl_stats = out.get("rl") or {}
        titles = ", ".join(a.get("title", "")[:24] for a in added[:4]) or "(없음)"
        msg = (
            f"카드 RL ({_now()}): 갭 {gaps.get('missing_count', '?')} · "
            f"계획 {len(planned)} · 추가 {len(added)} · "
            f"누적+{rl_stats.get('added', 0)} PASS {rl_stats.get('pass', 0)} · "
            f"오늘운 llm={gaps.get('daily', {}).get('llm_required')} · "
            f"추가분: {titles}"
        )
        return True, msg
    except Exception as e:
        return False, f"카드 RL 실패: {e}"


def job_saju_cert_reverify(agent: dict) -> tuple[bool, str]:
    """명리위원회 인증 재점검 — 1장 실제 검증 + 큐 상태."""
    try:
        import agent_office_saju_card_council as council

        st_before = council.council_stats()
        rot = council._load_rotation()
        idx = int(rot.get("pass_reverify_index") or 0)
        total = int(rot.get("pass_reverify_total") or st_before.get("council_pass") or 0)
        fail_n = st_before.get("council_fail") or 0
        pend = st_before.get("council_pending") or 0
        strong = st_before.get("council_strengthened") or 0

        tick = council.verify_one_card_cycle()
        tick_line = ""
        if tick:
            cid = tick.get("card_id")
            passed = tick.get("passed")
            mode = tick.get("mode") or "?"
            tick_line = f" · 이번 #{cid} {mode} {'PASS' if passed else 'FAIL'}"
        else:
            tick_line = " · 이번 턴 처리 없음"

        st = council.council_stats()
        msg = (
            f"인증 재점검 ({_now()}): PASS {st.get('council_pass', 0)} · "
            f"미검증 {pend} · FAIL {fail_n} · 강화 {strong} · "
            f"순환 {idx}/{total}{tick_line}"
        )
        return True, msg
    except Exception as e:
        return False, f"재점검 실패: {e}"


from agent_office_workisus_jobs import (  # noqa: E402
    job_workisus_atr_pulse,
    job_workisus_atr_rl_autofill,
    job_workisus_auto_pulse,
    job_workisus_balance_pulse,
    job_workisus_card_compose,
    job_workisus_catalog_maintain,
    job_workisus_error_resolve,
    job_workisus_error_seed,
    job_workisus_hts_pulse,
    job_workisus_mode_pulse,
    job_workisus_multi_pulse,
    job_workisus_ops_pulse,
    job_workisus_order_pulse,
    job_workisus_pack_sync,
    job_workisus_pulse,
    job_workisus_rebalance_pulse,
    job_workisus_reconcile_pulse,
    job_workisus_risk_pulse,
    job_workisus_rules_pulse,
    job_workisus_slots_pulse,
    job_workisus_stocks_pulse,
    job_workisus_token_pulse,
    job_workisus_watch_pulse,
    job_workisus_wiki_pulse,
)
from agent_office_gwansang_jobs import (  # noqa: E402
    job_gwansang_card_compose,
    job_gwansang_catalog_maintain,
    job_gwansang_daily_conclusion,
    job_gwansang_error_fix,
    job_gwansang_features_pulse,
    job_gwansang_fortune_pulse,
    job_gwansang_gap_autofill,
    job_gwansang_pack_sync,
    job_gwansang_pii_scan,
    job_gwansang_reader_pulse,
    job_gwansang_review_hint,
    job_gwansang_scholar_pulse,
    job_gwansang_seo_pulse,
    job_gwansang_structurer_pulse,
    job_gwansang_tag_digest,
    job_gwansang_watch_pulse,
    job_gwansang_wiki_sync,
)
from agent_office_homepage_design_jobs import (  # noqa: E402
    job_homepage_design_a11y_pulse,
    job_homepage_design_catalog_maintain,
    job_homepage_design_component_pulse,
    job_homepage_design_council_debate,
    job_homepage_design_handoff_pulse,
    job_homepage_design_layout_pulse,
    job_homepage_design_pack_sync,
    job_homepage_design_pii_scan,
    job_homepage_design_pulse,
    job_homepage_design_research_pulse,
    job_homepage_design_token_pulse,
    job_homepage_design_typography_pulse,
    job_homepage_design_ux_pulse,
)
from office_web_research_jobs import (  # noqa: E402
    job_office_web_research_pulse,
)
from agent_office_kiwoom_jobs import (  # noqa: E402
    job_kiwoom_account_pulse,
    job_kiwoom_card_pulse,
    job_kiwoom_card_compose,
    job_kiwoom_daily_conclusion,
    job_kiwoom_error_resolve,
    job_kiwoom_catalog_maintain,
    job_kiwoom_wonhero_monitor,
    job_kiwoom_gap_autofill,
    job_kiwoom_rl_train,
    job_kiwoom_pack_sync,
    job_kiwoom_pii_scan,
    job_kiwoom_review_hint,
    job_kiwoom_tag_digest,
)


def job_saju_error_resolve(agent: dict) -> tuple[bool, str]:
    """사무실·학습부·서비스 오류 점검 (health + 누락 젬마 답변)."""
    issues: list[str] = []
    try:
        import agent_office_health

        report = agent_office_health.run_checks()
        for c in report.get("checks") or []:
            if isinstance(c, dict) and not c.get("ok"):
                issues.append(f"{c.get('name')}: {str(c.get('detail') or '')[:72]}")
    except Exception as e:
        issues.append(f"health 실행 실패: {e}")

    try:
        st = _saju_stats()
        if int(st.get("pending") or 0) > 25:
            issues.append(f"학습 대기 카드 과다: {st['pending']}건")
    except Exception as e:
        issues.append(f"학습부 통계: {e}")

    if DB_PATH.is_file():
        try:
            import home_qa_reply

            gemma = GEMMA24_AUTHOR
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                posts = conn.execute(
                    "SELECT id, title FROM posts WHERE content LIKE '[질문]%' ORDER BY id DESC LIMIT 15"
                ).fetchall()
                for p in posts:
                    pid = int(p["id"])
                    rows = conn.execute(
                        "SELECT id, author, content FROM comments WHERE post_id=? ORDER BY id",
                        (pid,),
                    ).fetchall()
                    title = p["title"] or ""
                    m = re.search(r"\[([^\]]+)\]", title)
                    topic = m.group(1) if m else "기타"
                    for row in rows:
                        if row["author"] == gemma:
                            continue
                        cid = int(row["id"])
                        if not home_qa_reply.user_comment_needs_reply(conn, pid, cid):
                            continue
                        try:
                            home_qa_reply.attach_reply(
                                conn,
                                pid,
                                cid,
                                row["author"],
                                row["content"] or "",
                                title,
                                topic,
                            )
                        except Exception as fix_err:
                            issues.append(
                                f"글#{pid} 댓글#{row['id']} 답변 누락(복구실패: {fix_err!s})"[:80]
                            )
                    if len(issues) >= 8:
                        break
                conn.commit()
        except Exception as e:
            issues.append(f"답변 점검: {e}")

    if issues:
        msg = "오류 점검 ⚠ " + "; ".join(issues[:6])
        if len(issues) > 6:
            msg += f" 외 {len(issues) - 6}건"
        return False, msg
    return True, f"오류 점검 ({_now()}): 학습부·health·질문 답변 — 이상 없음"


def job_stock_watch_sync(agent: dict) -> tuple[bool, str]:
    """국내·미국 시세 스냅샷 수집."""
    import agent_office_stock_watch as sw

    if not sw._enabled():
        return True, "주식 시황 수집 비활성(STOCK_WATCH_ENABLED=0)"
    r = sw.sync_market_data()
    if not r.get("ok"):
        err = r.get("error") or r.get("errors") or "sync_failed"
        return False, f"주식 시황 수집 실패 ({_now()}): {err}"
    wiki_note = ""
    try:
        import agent_office_stock_wiki as stock_wiki

        wr = stock_wiki.sync_to_knowledge()
        if wr.get("ok") and not wr.get("skipped"):
            wiki_note = " · 젬마지식 반영"
    except Exception:
        pass
    return True, sw.summary_text() + wiki_note


def job_stock_watch_comment(agent: dict) -> tuple[bool, str]:
    """레거시 job — 지역 브리핑으로 위임."""
    aid = (agent.get("id") or "").strip()
    import agent_office_stock_jobs as sj

    if aid == "stock_kr":
        return sj.job_stock_kr_brief(agent)
    if aid == "stock_us":
        return sj.job_stock_us_brief(agent)
    import agent_office_stock_watch as sw

    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        return True, f"주식 시황 ({_now()}): 아직 스냅샷 없음 — stock_radar 수집 대기"
    return True, sw.summary_text()


try:
    import agent_office_stock_jobs as _stock_jobs
except ImportError:
    _stock_jobs = None

_STOCK_JOB_HANDLERS: dict = {}
if _stock_jobs:
    _STOCK_JOB_HANDLERS = {
        "stock_chart_pulse": _stock_jobs.job_stock_chart_pulse,
        "stock_rl_predict": _stock_jobs.job_stock_rl_predict,
        "stock_finance_pulse": _stock_jobs.job_stock_finance_pulse,
        "stock_news_pulse": _stock_jobs.job_stock_news_pulse,
        "stock_risk_scan": _stock_jobs.job_stock_risk_scan,
        "stock_kr_brief": _stock_jobs.job_stock_kr_brief,
        "stock_us_brief": _stock_jobs.job_stock_us_brief,
        "stock_blog_hints": _stock_jobs.job_stock_blog_hints,
        "stock_comment_verify": _stock_jobs.job_stock_comment_verify,
        "stock_disclosure_pulse": _stock_jobs.job_stock_disclosure_pulse,
        "stock_government_pulse": _stock_jobs.job_stock_government_pulse,
        "stock_press_pulse": _stock_jobs.job_stock_press_pulse,
        "stock_rates_dollar_pulse": _stock_jobs.job_stock_rates_dollar_pulse,
        "stock_commodities_pulse": _stock_jobs.job_stock_commodities_pulse,
        "stock_bonds_pulse": _stock_jobs.job_stock_bonds_pulse,
        "stock_oil_war_pulse": _stock_jobs.job_stock_oil_war_pulse,
        "stock_ceo_remarks_pulse": _stock_jobs.job_stock_ceo_remarks_pulse,
        "stock_youtube_pulse": _stock_jobs.job_stock_youtube_pulse,
        "stock_analyst_pulse": _stock_jobs.job_stock_analyst_pulse,
    }

try:
    from agent_office_chief_dev_jobs import (
        job_chief_arch_review,
        job_chief_rag_crawler,
        job_chief_devops_monitor,
    )
except ImportError:
    job_chief_arch_review = lambda a: (True, "chief-dev jobs 미구현")
    job_chief_rag_crawler = lambda a: (True, "chief-dev jobs 미구현")
    job_chief_devops_monitor = lambda a: (True, "chief-dev jobs 미구현")


JOB_HANDLERS = {
    "stock_watch_sync": job_stock_watch_sync,
    "stock_watch_comment": job_stock_watch_comment,
    **_STOCK_JOB_HANDLERS,
    "pii_scan": job_pii_scan,
    "fact_pulse": job_fact_pulse,
    "meta_digest": job_meta_digest,
    "draft_check": job_draft_check,
    "site_watch": job_site_watch,
    "comment_scan": job_comment_scan,
    "comment_bot": job_comment_bot,
    "etf_sync": job_etf_sync,
    "daily_conclusion": job_daily_conclusion,
    "heartbeat": job_heartbeat,
    "saju_pii_scan": job_saju_pii_scan,
    "saju_card_pulse": job_saju_card_pulse,
    "saju_tag_digest": job_saju_tag_digest,
    "saju_review_hint": job_saju_review_hint,
    "saju_pack_sync": job_saju_pack_sync,
    "saju_daily_conclusion": job_saju_daily_conclusion,
    "saju_gap_autofill": job_saju_gap_autofill,
    "saju_cert_reverify": job_saju_cert_reverify,
    "saju_error_resolve": job_saju_error_resolve,
    "kiwoom_pii_scan": job_kiwoom_pii_scan,
    "kiwoom_account_pulse": job_kiwoom_account_pulse,
    "kiwoom_card_pulse": job_kiwoom_card_pulse,
    "kiwoom_card_compose": job_kiwoom_card_compose,
    "kiwoom_tag_digest": job_kiwoom_tag_digest,
    "kiwoom_review_hint": job_kiwoom_review_hint,
    "kiwoom_pack_sync": job_kiwoom_pack_sync,
    "kiwoom_daily_conclusion": job_kiwoom_daily_conclusion,
    "kiwoom_gap_autofill": job_kiwoom_gap_autofill,
    "kiwoom_rl_train": job_kiwoom_rl_train,
    "kiwoom_error_resolve": job_kiwoom_error_resolve,
    "kiwoom_catalog_maintain": job_kiwoom_catalog_maintain,
    "kiwoom_wonhero_monitor": job_kiwoom_wonhero_monitor,
    "homepage_design_pulse": job_homepage_design_pulse,
    "homepage_design_pack_sync": job_homepage_design_pack_sync,
    "homepage_design_catalog_maintain": job_homepage_design_catalog_maintain,
    "homepage_design_council_debate": job_homepage_design_council_debate,
    "homepage_design_token_pulse": job_homepage_design_token_pulse,
    "homepage_design_typography_pulse": job_homepage_design_typography_pulse,
    "homepage_design_layout_pulse": job_homepage_design_layout_pulse,
    "homepage_design_component_pulse": job_homepage_design_component_pulse,
    "homepage_design_a11y_pulse": job_homepage_design_a11y_pulse,
    "homepage_design_handoff_pulse": job_homepage_design_handoff_pulse,
    "homepage_design_ux_pulse": job_homepage_design_ux_pulse,
    "homepage_design_research_pulse": job_homepage_design_research_pulse,
    "office_web_research_pulse": job_office_web_research_pulse,
    "gwansang_web_research_pulse": job_office_web_research_pulse,
    "kiwoom_web_research_pulse": job_office_web_research_pulse,
    "saju_web_research_pulse": job_office_web_research_pulse,
    "stock_web_research_pulse": job_office_web_research_pulse,
    "finance_web_research_pulse": job_office_web_research_pulse,
    "workisus_web_research_pulse": job_office_web_research_pulse,
    "homepage_design_pii_scan": job_homepage_design_pii_scan,
    "workisus_pulse": job_workisus_pulse,
    "workisus_pack_sync": job_workisus_pack_sync,
    "workisus_card_compose": job_workisus_card_compose,
    "workisus_catalog_maintain": job_workisus_catalog_maintain,
    "workisus_wiki_pulse": job_workisus_wiki_pulse,
    "workisus_atr_pulse": job_workisus_atr_pulse,
    "workisus_ops_pulse": job_workisus_ops_pulse,
    "workisus_atr_rl_autofill": job_workisus_atr_rl_autofill,
    "workisus_error_resolve": job_workisus_error_resolve,
    "workisus_error_seed": job_workisus_error_seed,
    "workisus_watch_pulse": job_workisus_watch_pulse,
    "workisus_mode_pulse": job_workisus_mode_pulse,
    "workisus_balance_pulse": job_workisus_balance_pulse,
    "workisus_stocks_pulse": job_workisus_stocks_pulse,
    "workisus_rules_pulse": job_workisus_rules_pulse,
    "workisus_risk_pulse": job_workisus_risk_pulse,
    "workisus_rebalance_pulse": job_workisus_rebalance_pulse,
    "workisus_token_pulse": job_workisus_token_pulse,
    "workisus_reconcile_pulse": job_workisus_reconcile_pulse,
    "workisus_order_pulse": job_workisus_order_pulse,
    "workisus_auto_pulse": job_workisus_auto_pulse,
    "workisus_multi_pulse": job_workisus_multi_pulse,
    "workisus_slots_pulse": job_workisus_slots_pulse,
    "workisus_hts_pulse": job_workisus_hts_pulse,
    "gwansang_watch_pulse": job_gwansang_watch_pulse,
    "gwansang_pack_sync": job_gwansang_pack_sync,
    "gwansang_card_compose": job_gwansang_card_compose,
    "gwansang_catalog_maintain": job_gwansang_catalog_maintain,
    "gwansang_seo_pulse": job_gwansang_seo_pulse,
    "gwansang_scholar_pulse": job_gwansang_scholar_pulse,
    "gwansang_features_pulse": job_gwansang_features_pulse,
    "gwansang_fortune_pulse": job_gwansang_fortune_pulse,
    "gwansang_reader_pulse": job_gwansang_reader_pulse,
    "gwansang_structurer_pulse": job_gwansang_structurer_pulse,
    "gwansang_pii_scan": job_gwansang_pii_scan,
    "gwansang_gap_autofill": job_gwansang_gap_autofill,
    "gwansang_wiki_sync": job_gwansang_wiki_sync,
    "gwansang_error_fix": job_gwansang_error_fix,
    "gwansang_daily_conclusion": job_gwansang_daily_conclusion,
    "gwansang_review_hint": job_gwansang_review_hint,
    "gwansang_tag_digest": job_gwansang_tag_digest,
    "chief_arch_review": job_chief_arch_review,
    "chief_rag_crawler": job_chief_rag_crawler,
    "chief_devops_monitor": job_chief_devops_monitor,
}


def run_job(agent: dict) -> tuple[bool, str]:
    job = (agent.get("job") or "heartbeat").strip()
    fn = JOB_HANDLERS.get(job, job_heartbeat)
    return fn(agent)
