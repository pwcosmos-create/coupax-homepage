"""
작업지시 연구·취합 — 담당 에이전트가 사이트 데이터를 조사해 보고서를 만듭니다.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))
ETF_JSON = BOARD / "data" / "monthly_dividend_etfs.json"

_KIWOM_AGENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kiwoom_privacy": ("개인정보", "pii", "비밀번호", "api키", "api"),
    "kiwoom_account": ("계좌", "예수금", "잔고", "주문가능", "입금", "출금", "평가금", "d+2"),
    "kiwoom_reader": ("차수", "전략", "수집", "카드", "1차", "2차", "3차"),
    "kiwoom_structurer": ("태그", "pack", "구조", "json", "export"),
    "kiwoom_risk": ("손절", "익절", "리스크", "분할", "모순"),
    "kiwoom_order": ("주문", "체결", "미체결", "호가"),
    "kiwoom_curator": ("확정", "검수", "승인", "반영"),
    "kiwoom_rl": ("피드백", "우선", "결론", "학습"),
    "kiwoom_error_fix": ("오류", "에러", "error", "500", "실패", "복구"),
}

_SAJU_AGENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "saju_privacy": ("개인정보", "pii", "이름", "생년", "연락처", "민감"),
    "saju_reader": ("풀이", "수집", "붙여", "import", "카드", "요약"),
    "saju_structurer": ("태그", "pack", "구조", "json", "export"),
    "saju_scholar": ("명리", "오행", "십신", "용신", "격국", "대운", "일주"),
    "saju_curator": ("확정", "검수", "승인", "반영"),
    "saju_rl": ("피드백", "우선", "결론", "학습"),
    "saju_reinspector": (
        "재점검",
        "재검증",
        "인증",
        "위원회",
        "강화",
        "recert",
        "reverify",
        "PASS",
    ),
    "saju_error_fix": ("오류", "에러", "error", "500", "실패", "복구", "고장", "끊김", "타임아웃"),
}

_DESIGN_AGENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "design_privacy": ("개인정보", "pii", "연락처", "이메일", "전화"),
    "design_token": ("토큰", "색", "palette", "copper", "midnight", "accent", "팔레트"),
    "design_typography": ("타이포", "폰트", "글꼴", "line-height", "본문", "제목"),
    "design_layout": ("레이아웃", "그리드", "간격", "반응형", "375", "모바일", "브레이크"),
    "design_component": ("컴포넌트", "버튼", "카드", "헤더", "네비", "푸터", "폼"),
    "design_a11y": ("접근성", "wcag", "대비", "aria", "키보드"),
    "design_handoff": ("핸드오프", "style.css", "css", "변수", ":root"),
    "design_ux_writer": ("카피", "cta", "문구", "placeholder", "마이크로"),
    "design_council": ("토론", "위원회", "합의", "debate"),
    "design_researcher": ("벤치마크", "레퍼런스", "참고", "목업"),
    "design_curator": ("확정", "pack", "플레이북", "export"),
    "design_catalog": ("카탈로그", "시드", "카드", "누락"),
}

_AGENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "privacy": ("개인정보", "pii", "보안", "민감", "필터"),
    "researcher": ("조사", "팩트", "금리", "이슈", "research", "발표", "경제"),
    "structurer": ("구조", "정리", "wiki", "메타", "카드", "취합"),
    "creator": ("글", "블로그", "작성", "문구", "안내", "초안"),
    "observer": ("차트", "화면", "ui", "관측", "레이아웃"),
    "listener": ("댓글", "질문", "톤", "faq"),
    "speaker": ("답변", "브리핑", "송출"),
    "rl": ("우선", "피드백", "순위", "결론"),
    "etf_sync": ("etf", "배당", "월배당", "종목", "시트", "배당률"),
}

_BLOG_KW = ("블로그", "글", "post", "게시")
_ETF_KW = ("etf", "배당", "월배당", "종목", "티커", "코드")


@dataclass
class ResearchNote:
    source: str
    title: str
    body: str


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[가-힣]{2,}|[a-zA-Z]{3,}|\d{4,}", (text or "").lower())
    stop = {"해주세요", "주세요", "관련", "오늘", "이슈", "정리", "조사"}
    return [t for t in raw if t not in stop][:12]


def pick_agent_for_instruction(
    body: str, assign_to: str = "all", *, division: str = "finance"
) -> str:
    assign = (assign_to or "all").strip()
    if assign and assign != "all":
        return assign

    text = (body or "").lower()
    scores: dict[str, int] = {}
    if division == "kiwoom-chasu":
        kw_map = _KIWOM_AGENT_KEYWORDS
    elif division == "saju-learn":
        kw_map = _SAJU_AGENT_KEYWORDS
    elif division == "homepage-design":
        kw_map = _DESIGN_AGENT_KEYWORDS
    else:
        kw_map = _AGENT_KEYWORDS
    for aid, kws in kw_map.items():
        scores[aid] = sum(2 if k in text else 0 for k in kws)

    if division == "kiwoom-chasu":
        if any(k in text for k in ("확정", "export", "pack")):
            scores["kiwoom_curator"] = scores.get("kiwoom_curator", 0) + 4
        if any(k in text for k in ("pii", "비밀번호", "api")):
            scores["kiwoom_privacy"] = scores.get("kiwoom_privacy", 0) + 4
        if any(k in text for k in ("계좌", "예수금", "잔고", "주문가능", "입금", "출금")):
            scores["kiwoom_account"] = scores.get("kiwoom_account", 0) + 5
        if any(k in text for k in ("오류", "에러", "error", "실패")):
            scores["kiwoom_error_fix"] = scores.get("kiwoom_error_fix", 0) + 5
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            return best[0]
        return "kiwoom_reader"

    if division == "saju-learn":
        if any(k in text for k in ("확정", "export", "pack")):
            scores["saju_curator"] = scores.get("saju_curator", 0) + 4
        if any(k in text for k in ("pii", "개인정보", "이름")):
            scores["saju_privacy"] = scores.get("saju_privacy", 0) + 4
        if any(k in text for k in ("오류", "에러", "error", "500", "실패", "복구", "끊김")):
            scores["saju_error_fix"] = scores.get("saju_error_fix", 0) + 5
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            return best[0]
        return "saju_reader"

    if division == "homepage-design":
        if any(k in text for k in ("확정", "export", "pack", "플레이북")):
            scores["design_curator"] = scores.get("design_curator", 0) + 4
        if any(k in text for k in ("토론", "위원회", "합의")):
            scores["design_council"] = scores.get("design_council", 0) + 5
        if any(k in text for k in ("pii", "개인정보", "연락처")):
            scores["design_privacy"] = scores.get("design_privacy", 0) + 4
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            return best[0]
        return "design_curator"

    if any(k in text for k in _ETF_KW):
        scores["etf_sync"] = scores.get("etf_sync", 0) + 5
    if any(k in text for k in _BLOG_KW):
        scores["creator"] = scores.get("creator", 0) + 3
        scores["researcher"] = scores.get("researcher", 0) + 2

    best = max(scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        return best[0]
    return "researcher"


def synthesizer_agent(primary: str, *, division: str = "finance") -> str:
    if division == "kiwoom-chasu":
        return "kiwoom_structurer" if primary != "kiwoom_structurer" else "kiwoom_risk"
    if division == "saju-learn":
        return "saju_structurer" if primary != "saju_structurer" else "saju_scholar"
    if division == "homepage-design":
        return "design_council" if primary != "design_council" else "design_curator"
    return "structurer" if primary != "structurer" else "researcher"


def agent_display(agent_id: str, registry: dict | None = None) -> str:
    if registry:
        for a in registry.get("agents") or []:
            if isinstance(a, dict) and a.get("id") == agent_id:
                emoji = a.get("emoji") or ""
                name = a.get("name") or agent_id
                return f"{emoji} {name}".strip()
    return agent_id


def _search_blog(keywords: list[str], limit: int = 8) -> list[ResearchNote]:
    if not DB_PATH.is_file():
        return []
    notes: list[ResearchNote] = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.created, p.views,
                   substr(p.content, 1, 400) AS excerpt,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS cc
            FROM posts p
            ORDER BY p.id DESC
            LIMIT 40
            """
        ).fetchall()

    for r in rows:
        blob = f"{r['title'] or ''} {r['excerpt'] or ''}".lower()
        if keywords and not any(k in blob for k in keywords):
            continue
        title = (r["title"] or "").strip()[:80]
        excerpt = re.sub(r"<[^>]+>", " ", r["excerpt"] or "")[:280].strip()
        notes.append(
            ResearchNote(
                source="blog",
                title=f"글 #{r['id']}: {title}",
                body=f"작성 {r['created']} · 조회 {r['views']} · 댓글 {r['cc']}\n{excerpt}",
            )
        )
        if len(notes) >= limit:
            break

    if not notes and rows:
        r = rows[0]
        notes.append(
            ResearchNote(
                source="blog",
                title=f"최신 글 #{r['id']}: {(r['title'] or '')[:60]}",
                body=f"조회 {r['views']} · 댓글 {r['cc']}",
            )
        )
    return notes


def _search_etf(keywords: list[str], limit: int = 8) -> list[ResearchNote]:
    try:
        import etf_ops_policy

        if not etf_ops_policy.etf_ops_enabled():
            return [
                ResearchNote(
                    "etf",
                    "ETF 데이터",
                    "ETF 파이프라인·공개 페이지가 중지되어 시트를 조회하지 않습니다.",
                )
            ]
    except ImportError:
        pass
    if not ETF_JSON.is_file():
        return [ResearchNote("etf", "ETF 데이터", "monthly_dividend_etfs.json 없음 — sync 필요")]
    data = json.loads(ETF_JSON.read_text(encoding="utf-8"))
    rows = data.get("rows") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return []

    notes: list[ResearchNote] = []
    etf_context = any(k in _ETF_KW for k in keywords)
    for it in rows:
        if not isinstance(it, dict):
            continue
        sym = str(it.get("code") or it.get("symbol") or "")
        name = str(it.get("name") or it.get("title") or "")
        blob = f"{sym} {name}".lower()
        if keywords and not etf_context and not any(k in blob for k in keywords):
            continue
        if keywords and etf_context and not any(k in blob for k in keywords):
            continue
        div = it.get("dividend_yield") or it.get("yield") or it.get("monthly_dividend") or "—"
        ytd = it.get("ytd_return") or it.get("return_ytd") or "—"
        notes.append(
            ResearchNote(
                source="etf",
                title=f"{sym} {name[:36]}",
                body=f"배당/수익: yield={div} · ytd={ytd}",
            )
        )
        if len(notes) >= limit:
            break

    if not notes:
        notes.append(
            ResearchNote("etf", f"월배당 ETF {len(rows)}종목", "키워드 일치 없음 — 전체 시트 참고")
        )
    return notes


def _search_web(title: str, body: str, keywords: list[str]) -> list[ResearchNote]:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return [ResearchNote("web", "웹 검색", "agent_office_web_search 모듈 없음")]

    if not ws.web_search_enabled():
        return []

    query = ws.build_query(title, body, keywords)
    hits = ws.search_web(query)
    if not hits:
        return [
            ResearchNote(
                "web",
                "웹 검색",
                f"결과 없음 — {ws.provider_status()} · 쿼리: {query[:80]}",
            )
        ]
    notes: list[ResearchNote] = []
    for h in hits:
        lines = [h.snippet] if h.snippet else []
        if h.url:
            lines.append(f"출처: {h.url}")
        notes.append(
            ResearchNote(
                source="web",
                title=f"[{h.provider}] {h.title[:80]}",
                body="\n".join(lines)[:500],
            )
        )
    return notes


def _search_web_blog_topics(
    primary_id: str, title: str, body: str, keywords: list[str]
) -> list[ResearchNote]:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return []

    if not ws.should_pick_blog_topics(primary_id, title, body):
        return []

    suggestions = ws.suggest_blog_topics(title, body, keywords)
    if not suggestions:
        return [
            ResearchNote(
                "web_topic",
                "웹 글감",
                f"글감 후보 없음 — {ws.provider_status()}",
            )
        ]
    notes: list[ResearchNote] = []
    for i, s in enumerate(suggestions, 1):
        notes.append(
            ResearchNote(
                source="web_topic",
                title=f"글감 후보 {i}: {s.topic[:70]}",
                body=f"{s.reason}\n출처: {s.url} ({s.provider})"[:500],
            )
        )
    return notes


def _search_comments(limit: int = 5) -> list[ResearchNote]:
    if not DB_PATH.is_file():
        return []
    notes: list[ResearchNote] = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT c.id, c.post_id, c.content, c.created FROM comments c ORDER BY c.id DESC LIMIT 15"
        ).fetchall()
    try:
        from agent_office_wiki_store import _redact_pii as redact
    except ImportError:
        redact = lambda s: s  # noqa: E731

    for r in rows[:limit]:
        text = redact(re.sub(r"\s+", " ", (r["content"] or ""))[:120])
        notes.append(
            ResearchNote(
                source="comment",
                title=f"댓글 #{r['id']} (글 #{r['post_id']})",
                body=f"{r['created']}: {text}",
            )
        )
    return notes


def _job_for_agent(agent_id: str) -> str:
    return {
        "privacy": "pii_scan",
        "researcher": "fact_pulse",
        "structurer": "meta_digest",
        "creator": "draft_check",
        "observer": "site_watch",
        "listener": "comment_scan",
        "speaker": "comment_scan",
        "rl": "daily_conclusion",
        "etf_sync": "site_watch",
        "saju_privacy": "saju_pii_scan",
        "saju_reader": "saju_card_pulse",
        "saju_structurer": "saju_tag_digest",
        "saju_scholar": "saju_review_hint",
        "saju_curator": "saju_pack_sync",
        "saju_rl": "saju_gap_autofill",
        "saju_reinspector": "saju_cert_reverify",
        "saju_error_fix": "saju_error_resolve",
    }.get(agent_id, "fact_pulse")


def _agent_special_research(agent_id: str) -> list[ResearchNote]:
    try:
        import agent_office_jobs

        ok, msg = agent_office_jobs.run_job({"id": agent_id, "job": _job_for_agent(agent_id)})
        return [
            ResearchNote(
                source="agent",
                title=f"{agent_id} 전문 점검",
                body=f"{'✓' if ok else '⚠'} {msg[:500]}",
            )
        ]
    except Exception as e:
        return [ResearchNote("agent", agent_id, f"전문 점검 스킵: {e}")]


def _search_saju_cards(keywords: list[str], limit: int = 8) -> list[ResearchNote]:
    try:
        import agent_office_saju_learn
    except ImportError:
        return [ResearchNote("saju", "학습부", "agent_office_saju_learn 없음")]

    notes: list[ResearchNote] = []
    for c in agent_office_saju_learn.list_cards(limit=30):
        blob = f"{c.get('title') or ''} {c.get('body') or ''} {' '.join(c.get('tags') or [])}".lower()
        if keywords and not any(k in blob for k in keywords):
            continue
        notes.append(
            ResearchNote(
                source="saju_card",
                title=f"카드 #{c.get('id')} [{c.get('status')}] {(c.get('title') or '')[:40]}",
                body=f"{c.get('summary') or ''}\n태그: {', '.join(c.get('tags') or [])}",
            )
        )
        if len(notes) >= limit:
            break
    if not notes:
        st = agent_office_saju_learn.stats()
        notes.append(
            ResearchNote(
                "saju",
                f"학습 카드 {st['total']}건",
                f"대기 {st['pending']} · 확정 {st['confirmed']}",
            )
        )
    return notes


def gather_research(task: dict, primary_id: str) -> list[ResearchNote]:
    division = (task.get("division") or "finance").strip()
    if division == "kiwoom-chasu" or (primary_id or "").startswith("kiwoom_"):
        return gather_kiwoom_research(task, primary_id)
    if division == "saju-learn" or (primary_id or "").startswith("saju_"):
        return gather_saju_research(task, primary_id)

    body = task.get("body") or ""
    title = task.get("title") or ""
    keywords = _tokens(f"{title} {body}")
    notes: list[ResearchNote] = [
        ResearchNote(
            source="instruction",
            title="지시 요약",
            body=f"제목: {title or '(없음)'}\n내용: {body[:600]}",
        )
    ]

    body_l = body.lower()
    want_blog = primary_id in ("creator", "researcher", "listener") or any(
        k in body_l for k in _BLOG_KW
    )
    want_etf = primary_id == "etf_sync" or any(k in body_l for k in _ETF_KW)
    want_comments = primary_id in ("listener", "speaker", "researcher")

    if want_blog:
        notes.extend(_search_blog(keywords))
    if want_etf:
        notes.extend(_search_etf(keywords))
    if want_comments:
        notes.extend(_search_comments())
    try:
        import agent_office_web_search as ws

        if ws.should_search_web(primary_id, title, body):
            notes.extend(_search_web(title, body, keywords))
        if ws.should_pick_blog_topics(primary_id, title, body):
            notes.extend(_search_web_blog_topics(primary_id, title, body, keywords))
    except ImportError:
        pass
    notes.extend(_agent_special_research(primary_id))
    return notes


def _search_saju_pack() -> list[ResearchNote]:
    pack_path = BOARD / "data" / "saju_learning" / "saju_knowledge_pack.json"
    if not pack_path.is_file():
        return []
    try:
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        cards = data.get("cards") or []
        if not cards:
            return []
        titles = ", ".join(
            (c.get("title") or f"#{c.get('id')}")[:30] for c in cards[:5] if isinstance(c, dict)
        )
        return [
            ResearchNote(
                source="saju_pack",
                title=f"확정 pack {len(cards)}건",
                body=f"최근 확정: {titles}",
            )
        ]
    except Exception:
        return []


def _search_kiwoom_cards(keywords: list[str], limit: int = 6) -> list[ResearchNote]:
    try:
        import agent_office_kiwoom_learn
    except Exception:
        return []
    notes: list[ResearchNote] = []
    for c in agent_office_kiwoom_learn.list_cards(limit=30):
        blob = f"{c.get('title') or ''} {c.get('body') or ''}".lower()
        if keywords and not any(k in blob for k in keywords):
            continue
        notes.append(
            ResearchNote(
                source="kiwoom_card",
                title=f"카드 #{c.get('id')} [{c.get('status')}] {(c.get('title') or '')[:40]}",
                body=f"{c.get('summary') or ''}\n태그: {', '.join(c.get('tags') or [])}",
            )
        )
        if len(notes) >= limit:
            break
    if not notes:
        st = agent_office_kiwoom_learn.stats()
        notes.append(
            ResearchNote(
                "kiwoom",
                f"학습 카드 {st['total']}건",
                f"대기 {st['pending']} · 확정 {st['confirmed']}",
            )
        )
    return notes


def _search_kiwoom_pack() -> list[ResearchNote]:
    pack_path = BOARD / "data" / "kiwoom_learning" / "kiwoom_knowledge_pack.json"
    if not pack_path.is_file():
        return []
    try:
        data = json.loads(pack_path.read_text(encoding="utf-8"))
        cards = data.get("cards") or []
        if not cards:
            return []
        titles = ", ".join(
            (c.get("title") or f"#{c.get('id')}")[:30] for c in cards[:5] if isinstance(c, dict)
        )
        return [
            ResearchNote(
                source="kiwoom_pack",
                title=f"확정 pack {len(cards)}건",
                body=f"최근 확정: {titles}",
            )
        ]
    except Exception:
        return []


def _search_kiwoom_account_snapshot() -> list[ResearchNote]:
    try:
        import agent_office_kiwoom_account

        agent_office_kiwoom_account.import_from_env_file()
        st = agent_office_kiwoom_account.stats()
        if not st.get("has_data"):
            return [
                ResearchNote(
                    source="kiwoom_account",
                    title="계좌 스냅샷 없음",
                    body="HTS에서 잔고 확인 후 사무실 「계좌 현황」 갱신 필요",
                )
            ]
        return [
            ResearchNote(
                source="kiwoom_account",
                title=f"{st.get('broker')} 잔고 ({st.get('updated_at')})",
                body=agent_office_kiwoom_account.summary_text(),
            )
        ]
    except Exception:
        return []


def gather_kiwoom_research(task: dict, primary_id: str) -> list[ResearchNote]:
    body = task.get("body") or ""
    title = task.get("title") or ""
    keywords = _tokens(f"{title} {body}")
    notes: list[ResearchNote] = [
        ResearchNote(
            source="instruction",
            title="지시 요약",
            body=f"제목: {title or '(없음)'}\n내용: {body[:600]}",
        )
    ]
    if primary_id in ("kiwoom_account", "kiwoom_order", "kiwoom_risk") or any(
        k in (body + title).lower() for k in ("계좌", "예수금", "잔고", "평가")
    ):
        notes.extend(_search_kiwoom_account_snapshot())
    notes.extend(_search_kiwoom_cards(keywords))
    notes.extend(_search_kiwoom_pack())
    notes.extend(_agent_special_research(primary_id))
    return notes


def gather_saju_research(task: dict, primary_id: str) -> list[ResearchNote]:
    body = task.get("body") or ""
    title = task.get("title") or ""
    keywords = _tokens(f"{title} {body}")
    notes: list[ResearchNote] = [
        ResearchNote(
            source="instruction",
            title="지시 요약",
            body=f"제목: {title or '(없음)'}\n내용: {body[:600]}",
        )
    ]
    notes.extend(_search_saju_cards(keywords))
    notes.extend(_search_saju_pack())
    notes.extend(_agent_special_research(primary_id))
    return notes


def synthesize_report(
    task: dict,
    primary_id: str,
    synth_id: str,
    notes: list[ResearchNote],
    registry: dict | None = None,
) -> str:
    division = (task.get("division") or "finance").strip()
    if division == "kiwoom-chasu":
        return synthesize_kiwoom_report(task, primary_id, synth_id, notes, registry)
    if division == "saju-learn":
        return synthesize_saju_report(task, primary_id, synth_id, notes, registry)

    tid = task.get("id") or "?"
    title = task.get("title") or ""
    body = task.get("body") or ""
    primary_name = agent_display(primary_id, registry)
    synth_name = agent_display(synth_id, registry)

    lines = [
        f"【작업 #{tid} 완료 보고】",
        f"담당: {primary_name} → 취합: {synth_name}",
        "",
        "■ 지시",
        f"{title + chr(10) if title else ''}{body[:400]}",
        "",
        "■ 연구 수집",
    ]
    idx = 0
    for n in notes:
        if n.source == "instruction":
            continue
        idx += 1
        lines.append(f"  {idx}. [{n.source}] {n.title}")
        for part in (n.body or "").split("\n"):
            part = part.strip()
            if part:
                lines.append(f"     {part[:200]}")

    lines.extend(["", "■ 취합 결론"])
    findings = [n for n in notes if n.source != "instruction"]
    if not findings:
        lines.append(
            "  · 사이트·DB에서 바로 매칭되는 자료가 없습니다. 키워드를 구체화하거나 ETF/블로그 관련 용어를 넣어 주세요."
        )
    else:
        blog_n = sum(1 for n in findings if n.source == "blog")
        etf_n = sum(1 for n in findings if n.source == "etf")
        cmt_n = sum(1 for n in findings if n.source == "comment")
        web_n = sum(1 for n in findings if n.source == "web")
        topic_notes = [n for n in findings if n.source == "web_topic"]
        if blog_n:
            lines.append(f"  · 블로그 {blog_n}건을 참고했습니다.")
        if etf_n:
            lines.append(f"  · 월배당 ETF {etf_n}건을 대조했습니다.")
        if cmt_n:
            lines.append(f"  · 최근 댓글 {cmt_n}건의 질문 톤을 반영했습니다.")
        if web_n:
            lines.append(
                f"  · 웹 검색 {web_n}건을 수집했습니다 (공식·언론 출처 URL은 보고 본문 참고)."
            )
        if topic_notes:
            lines.append(f"  · 웹 글감 후보 {len(topic_notes)}건을 선정했습니다 (아래 목록).")
        agent_bits = [n.body[:120] for n in findings if n.source == "agent"]
        if agent_bits:
            lines.append(f"  · {primary_name} 전문 점검: {agent_bits[0]}")

    topic_notes = [n for n in notes if n.source == "web_topic"]
    if topic_notes:
        lines.extend(["", "■ 제안 글감 (웹 검색)"])
        for n in topic_notes:
            lines.append(f"  · {n.title.replace('글감 후보 ', '')}")
            for part in (n.body or "").split("\n"):
                part = part.strip()
                if part:
                    lines.append(f"     {part[:200]}")

    lines.extend(
        [
            "",
            "■ 제안 다음 단계",
            "  · Wiki/메타 카드 초안 → 사서 젬마에게 구조화 지시",
            "  · 블로그 초안 → 작업 완료 시 자동 생성(미공개), 사무실에서 발행",
            "  · 데이터 갱신 → ETF 동기화 지시",
        ]
    )
    if topic_notes:
        top = topic_notes[0].title
        if ":" in top:
            top = top.split(":", 1)[-1].strip()
        lines.append(f"  · [추천] 위 「{top[:50]}」 주제로 창조 젬마에게 장문 초안 지시")
    if task.get("priority") == "high":
        lines.append("  · [긴급] RL 젬마 — 내일 우선순위 큐 상단 반영 권장")

    return "\n".join(lines)[:4000]


def synthesize_saju_report(
    task: dict,
    primary_id: str,
    synth_id: str,
    notes: list[ResearchNote],
    registry: dict | None = None,
) -> str:
    tid = task.get("id") or "?"
    title = task.get("title") or ""
    body = task.get("body") or ""
    primary_name = agent_display(primary_id, registry)
    synth_name = agent_display(synth_id, registry)
    try:
        import agent_office_saju_learn

        st = agent_office_saju_learn.stats()
    except Exception:
        st = {"total": 0, "pending": 0, "confirmed": 0}

    lines = [
        f"【사주 학습 #{tid} 완료】",
        f"담당: {primary_name} → 취합: {synth_name}",
        "",
        "■ 지시",
        f"{title + chr(10) if title else ''}{body[:400]}",
        "",
        f"■ 학습부 현황 — 전체 {st['total']} · 대기 {st['pending']} · 확정 {st['confirmed']}",
        "",
        "■ 조사",
    ]
    idx = 0
    for n in notes:
        if n.source == "instruction":
            continue
        idx += 1
        lines.append(f"  {idx}. [{n.source}] {n.title}")
        for part in (n.body or "").split("\n"):
            part = part.strip()
            if part:
                lines.append(f"     {part[:200]}")

    lines.extend(
        [
            "",
            "■ 취합",
            "  · 풀이 카드 검수 후 「확정」→ saju_knowledge_pack.json",
            "  · saju-v2 웹 연동 없음 — 본문 붙여넣기만",
            "  · Cursor: CURSOR_SAJU_LEARN.md 참고",
        ]
    )
    return "\n".join(lines)[:4000]


def synthesize_kiwoom_report(
    task: dict,
    primary_id: str,
    synth_id: str,
    notes: list[ResearchNote],
    registry: dict | None = None,
) -> str:
    tid = task.get("id") or "?"
    title = task.get("title") or ""
    body = task.get("body") or ""
    primary_name = agent_display(primary_id, registry)
    synth_name = agent_display(synth_id, registry)
    try:
        import agent_office_kiwoom_learn

        st = agent_office_kiwoom_learn.stats()
    except Exception:
        st = {"total": 0, "pending": 0, "confirmed": 0}

    lines = [
        f"【차수거래 학습 #{tid} 완료】",
        f"담당: {primary_name} → 취합: {synth_name}",
        "",
        "■ 지시",
        f"{title + chr(10) if title else ''}{body[:400]}",
        "",
        f"■ 학습부 현황 — 전체 {st['total']} · 대기 {st['pending']} · 확정 {st['confirmed']}",
        "",
        "■ 조사",
    ]
    idx = 0
    for n in notes:
        if n.source == "instruction":
            continue
        idx += 1
        lines.append(f"  {idx}. [{n.source}] {n.title}")
        for part in (n.body or "").split("\n"):
            part = part.strip()
            if part:
                lines.append(f"     {part[:200]}")

    lines.extend(
        [
            "",
            "■ 취합",
            "  · 차수거래 카드 검수 후 「확정」→ kiwoom_knowledge_pack.json",
            "  · 실제 주문은 키움 HTS/영웅문에서 실행 (자동 매매 없음)",
            "  · Cursor: CURSOR_KIWOM_LEARN.md 참고",
        ]
    )
    return "\n".join(lines)[:4000]
