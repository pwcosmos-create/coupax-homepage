"""
조사·시황 결과 → 블로그 초안 1건/일 (순차 발행 큐용).

  python scripts/blog_research_draft.py ensure   # 오늘 초안 없으면 생성
  python scripts/blog_research_draft.py status

발행은 blog_publish_scheduler.py (하루 1건·랜덤 시각·AdSense 보강).
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import board_env  # noqa: E402
import json_store  # noqa: E402
import blog_adsense_enrich as adsense  # noqa: E402

DB_PATH = board_env.resolve_db_path()
STATE_PATH = BOARD / "data" / "blog_research_draft.json"
RESEARCH_MARKER = "<!-- coupax-research-draft -->"
META_LINE = "조사 초안 · coupax-research-draft"


def _enabled() -> bool:
    return os.getenv("BLOG_RESEARCH_DRAFT_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(os.getenv("BLOG_PUBLISH_TZ", "Asia/Seoul"))
    except Exception:
        return ZoneInfo("Asia/Seoul")


def _today() -> str:
    return datetime.now(_tz()).strftime("%Y-%m-%d")


def _now_str() -> str:
    return datetime.now(_tz()).strftime("%Y-%m-%d %H:%M")


def _default_state() -> dict:
    return {"last_draft_date": "", "last_post_id": None, "last_source": ""}


def load_state() -> dict:
    try:
        return json_store.load_json(STATE_PATH, default=_default_state())
    except json_store.JsonStoreError:
        return _default_state()


def save_state(data: dict) -> None:
    json_store.save_json(STATE_PATH, data)


def _draft_password() -> str:
    if str(BOARD) not in sys.path:
        sys.path.insert(0, str(BOARD))
    import security_utils  # noqa: E402

    plain = os.getenv("AGENT_OFFICE_BLOG_DRAFT_PASSWORD", "coupax2026").strip()
    return security_utils.hash_password(plain or "coupax2026")


def _find_todays_research_draft(conn: sqlite3.Connection, today: str) -> int | None:
    row = conn.execute(
        """
        SELECT id FROM posts
        WHERE COALESCE(is_draft, 0) = 1
          AND content LIKE ?
          AND substr(created, 1, 10) = ?
        ORDER BY id DESC LIMIT 1
        """,
        (f"%{RESEARCH_MARKER}%", today),
    ).fetchone()
    return int(row[0]) if row else None


def _tasks_ready_for_draft() -> list[dict]:
    try:
        import agent_office_tasks
    except ImportError:
        return []
    tasks = agent_office_tasks.load_tasks()
    out: list[dict] = []
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        if (t.get("status") or "").strip() != "done":
            continue
        if t.get("blog_draft_id"):
            continue
        result = (t.get("result") or "").strip()
        if len(result) < 120:
            continue
        div = (t.get("division") or "finance").strip()
        if div not in ("finance", "stock-watch"):
            continue
        out.append(t)
    out.sort(key=lambda x: int(x.get("id") or 0), reverse=True)
    return out


def _create_from_task(task: dict) -> int | None:
    import agent_office_blog_draft as bd
    import agent_office_tasks

    result = (task.get("result") or "").strip()
    pid = bd.create_draft_from_task(task, result)
    if not pid:
        return None
    tid = int(task.get("id") or 0)
    if tid:
        agent_office_tasks.update_task(tid, blog_draft_id=pid)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT content FROM posts WHERE id=?", (pid,)).fetchone()
        body = (row[0] if row else "") or ""
        if RESEARCH_MARKER not in body:
            body = f"{RESEARCH_MARKER}\n<p><small>{META_LINE} · task_id={tid}</small></p>\n{body}"
            conn.execute("UPDATE posts SET content=? WHERE id=?", (body, pid))
            conn.commit()
    return pid


def _p(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def _li(text: str) -> str:
    return f"<li>{html.escape(text)}</li>"


def _build_stock_insights_html(today: str) -> tuple[str, str]:
    import agent_office_stock_watch as sw

    snap = sw.load_snapshot()
    ins = sw.load_insights()
    st = sw.stats()
    updated = st.get("updated_at") or snap.get("updated_at") or _now_str()

    title = (
        f"{today} 증시 종합 조사 — RL예측·시세·금리·채권·원유·원자재·"
        f"CEO·유튜브·애널리스트·공시"
    )
    parts = [
        RESEARCH_MARKER,
        f"<p><small>{META_LINE} · stock-watch · {updated}</small></p>",
        "[카테고리] ETF·주식",
        _p(
            "젬마24 주식 시황부가 수집·교차 검증한 내용을 바탕으로 한 "
            f"<strong>{today}</strong> 브리핑입니다. 투자 권유가 아니며, "
            "수치·뉴스는 발행 시점 기준입니다."
        ),
        "<h2>1. 오늘 시세 스냅샷</h2>",
    ]

    mk = snap.get("markets") or {}
    kr_mk = mk.get("kr") or {}
    n200 = len(kr_mk.get("kospi200") or [])
    n150 = len(kr_mk.get("kosdaq150") or [])
    if n200 or n150:
        parts.append(
            _p(f"국내 유니버스: 코스피200 풀 {n200}종목 · 코스닥150 풀 {n150}종목 (시총 순, 네이버 금융)")
        )
    for region, label in (("kr", "국내"), ("us", "미국")):
        block = mk.get(region) or {}
        quotes = (block.get("indices") or []) + (block.get("kospi200") or []) + (
            block.get("kosdaq150") or []
        ) + (block.get("watchlist") or [])
        if not quotes:
            parts.append(_p(f"{label}: 수집 데이터 없음"))
            continue
        parts.append(f"<h3>{label}</h3><ul>")
        for q in quotes[:8]:
            parts.append(
                _li(
                    f"{q.get('name', q.get('symbol'))}: {q.get('price')} "
                    f"({float(q.get('change_pct') or 0):+.2f}%)"
                )
            )
        parts.append("</ul>")

    chart = ins.get("chart") or {}
    parts.append("<h2>2. 차트·추세 신호</h2>")
    if chart.get("items"):
        parts.append("<ul>")
        for it in chart.get("items")[:8]:
            parts.append(_li(f"{it.get('name')}: {it.get('signal')} — {it.get('note')}"))
        parts.append("</ul>")
    else:
        parts.append(_p("차트젬마 분석 대기 중입니다."))

    rl = ins.get("rl_predictions") or {}
    parts.append("<h2>3. 오늘 종목 상승·하락 예측 (강화학습)</h2>")
    parts.append(
        _p(
            "컨텍스트 밴딧형 강화학습(선형 Q·ε-greedy)으로 관심종목·지수의 "
            "<strong>다음 구간 방향</strong>을 점수화합니다. "
            "과거 예측 적중 여부로 가중치를 갱신하며, 투자 권유·확정 전망이 아닙니다."
        )
    )
    model = html.escape(str(rl.get("model") or "contextual_bandit_linear_q"))
    eps = rl.get("epsilon")
    stats = rl.get("stats") if isinstance(rl.get("stats"), dict) else {}
    hit = int(stats.get("hits") or 0)
    settled = int(stats.get("settled") or 0)
    if settled:
        parts.append(
            _p(
                f"모델 {model} · ε={eps} · 누적 정산 {settled}건 중 적중 {hit}건 "
                f"({hit / max(settled, 1) * 100:.0f}%)"
            )
        )
    rl_items = [it for it in (rl.get("items") or []) if isinstance(it, dict)]
    watch = [
        it
        for it in rl_items
        if it.get("bucket") in ("kospi200", "kosdaq150", "watchlist")
    ]
    indices = [it for it in rl_items if it.get("bucket") == "indices"]
    show = watch if watch else rl_items
    if show:
        parts.append("<table class=\"stock-rl-table\"><thead><tr>"
                     "<th>종목</th><th>예측</th><th>신뢰도</th><th>당일</th><th>근거</th></tr></thead><tbody>")
        for it in show[:30]:
            name = html.escape(str(it.get("name") or it.get("symbol") or ""))
            pred = html.escape(str(it.get("predicted_ko") or ""))
            conf = float(it.get("confidence") or 0) * 100
            pct = float(it.get("change_pct") or 0)
            reason = html.escape(str(it.get("reason") or "")[:120])
            pred_cls = html.escape(str(it.get("predicted") or "flat"))
            parts.append(
                f"<tr class=\"rl-{pred_cls}\"><td>{name}</td><td><strong>{pred}</strong></td>"
                f"<td>{conf:.0f}%</td><td>{pct:+.2f}%</td><td><small>{reason}</small></td></tr>"
            )
        parts.append("</tbody></table>")
        if indices:
            parts.append("<p><small>지수: ")
            idx_bits = [
                f"{html.escape(str(i.get('name') or ''))} "
                f"{html.escape(str(i.get('predicted_ko') or ''))}"
                for i in indices[:4]
            ]
            parts.append(", ".join(idx_bits))
            parts.append("</small></p>")
        if rl.get("summary"):
            parts.append(f"<p><small>{html.escape(str(rl.get('summary'))[:400])}</small></p>")
    else:
        parts.append(_p("RL예측젬마 실행 대기 — 시황부 동기화 후 예측이 생성됩니다."))

    fin = ins.get("finance") or {}
    parts.append("<h2>4. 제무·밸류에이션 참고</h2>")
    if fin.get("items"):
        parts.append("<ul>")
        for it in fin.get("items")[:5]:
            parts.append(_li(f"{it.get('name', '')}: {it.get('title', '')[:80]}"))
        parts.append("</ul>")
        parts.append(_p("※ 웹 검색 스니펫이며 공식 공시·재무제표로 재확인하세요."))
    else:
        parts.append(_p("제무젬마 조사 항목 없음"))

    analyst = ins.get("analyst_reports") or {}
    parts.append("<h2>5. 증권사 애널리스트 리포트·목표가</h2>")
    parts.append(
        _p(
            "관심종목에 대한 애널리스트 리포트·투자의견·목표가 관련 검색 결과입니다. "
            "증권사 리포트는 투자 권유가 아니며, 공시·재무·당일 시세와 교차 확인하세요."
        )
    )
    if analyst.get("items"):
        parts.append("<ul>")
        for it in analyst.get("items")[:10]:
            tit = html.escape((it.get("title") or "")[:110])
            snip = html.escape((it.get("snippet") or "")[:180])
            url = it.get("url") or ""
            company = html.escape(it.get("company") or "")
            broker = html.escape(it.get("broker") or "")
            topic = html.escape(it.get("topic") or "")
            tp = html.escape(it.get("target_price") or "")
            chg = it.get("market_change_pct")
            chg_s = f" ({float(chg):+.2f}%)" if chg is not None else ""
            head = f"<strong>{company}</strong>{chg_s}" if company else ""
            if broker:
                head += f" · {broker}"
            if tp:
                head += f" · 목표가 {tp}"
            if url:
                parts.append(
                    f"<li>{head} <em>[{topic}]</em> "
                    f'<a href="{html.escape(url)}" rel="noopener noreferrer">{tit}</a>'
                    f"<br><span class=\"stock-snippet\">{snip}</span></li>"
                )
            else:
                parts.append(f"<li>{head} <em>[{topic}]</em> {tit}<br>{snip}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("애널리스트젬마 조사 대기"))

    disc = ins.get("disclosure") or {}
    parts.append("<h2>6. 전자공시 (DART·SEC)</h2>")
    parts.append(_p("공식 전자공시·공시 채널 검색 결과입니다. 투자 판단 전 원문을 확인하세요."))
    if disc.get("items"):
        parts.append("<ul>")
        for it in disc.get("items")[:6]:
            url = html.escape(it.get("url") or "#")
            tit = html.escape((it.get("title") or "")[:100])
            st = html.escape(it.get("source_type") or "")
            parts.append(
                f'<li><span>[{st}]</span> <a href="{url}" rel="noopener noreferrer">{tit}</a></li>'
            )
        parts.append("</ul>")
    else:
        parts.append(_p("공시젬마 수집 대기"))

    gov = ins.get("government") or {}
    parts.append("<h2>7. 정부·중앙은행 보도자료</h2>")
    if gov.get("items"):
        parts.append("<ul>")
        for it in gov.get("items")[:6]:
            url = html.escape(it.get("url") or "#")
            tit = html.escape((it.get("title") or "")[:100])
            parts.append(f'<li><a href="{url}" rel="noopener noreferrer">{tit}</a></li>')
        parts.append("</ul>")
    else:
        parts.append(_p("정부발표젬마 수집 대기"))

    macro = ins.get("rates_dollar") or {}
    parts.append("<h2>8. 금리·달러(환율)와 증시 영향</h2>")
    usdkrw = macro.get("usdkrw") or {}
    if usdkrw.get("price"):
        parts.append(
            _p(
                f"USD/KRW {usdkrw.get('price')} (당일 {float(usdkrw.get('change_pct') or 0):+.2f}%). "
                "환율·금리는 증시에 동시에 작용하며, 아래는 일반 시사와 당일 스냅샷 대조입니다."
            )
        )
    else:
        parts.append(_p("금리·환율 스냅샷 수집 대기 — 한은·연준 보도와 함께 확인하세요."))
    if macro.get("items"):
        parts.append("<ul>")
        for it in macro.get("items")[:8]:
            tit = html.escape((it.get("title") or "")[:110])
            snip = html.escape((it.get("snippet") or "")[:200])
            url = it.get("url") or ""
            topic = html.escape(it.get("topic") or "")
            if url:
                parts.append(
                    f'<li><strong>[{topic}]</strong> <a href="{html.escape(url)}" '
                    f'rel="noopener noreferrer">{tit}</a><br><span class="stock-snippet">{snip}</span></li>'
                )
            else:
                parts.append(f"<li><strong>[{topic}]</strong> {tit}<br>{snip}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("금리·달러젬마 조사 대기"))

    bonds = ins.get("bonds") or {}
    parts.append("<h2>9. 채권·국채 수익률과 증시 영향</h2>")
    bond_quotes = [q for q in (bonds.get("quotes") or []) if q.get("kind") == "yield"]
    if bond_quotes:
        parts.append("<ul>")
        for q in bond_quotes[:8]:
            unit = q.get("unit") or "%"
            parts.append(
                _li(
                    f"{q.get('name', q.get('symbol'))}: {q.get('price')}{unit} "
                    f"({float(q.get('change_pct') or 0):+.2f}%)"
                )
            )
        parts.append("</ul>")
        parts.append(
            _p(
                "국채 수익률 상승은 일반적으로 채권 가격 하락·주식 할인율 부담으로 해석됩니다. "
                "장단기 금리차(곡선)·한·미 스프레드·회사채 신용과 함께 보세요."
            )
        )
    else:
        parts.append(_p("채권 수익률 스냅샷 수집 대기"))
    if bonds.get("items"):
        parts.append("<ul>")
        for it in bonds.get("items")[:8]:
            tit = html.escape((it.get("title") or "")[:110])
            snip = html.escape((it.get("snippet") or "")[:200])
            url = it.get("url") or ""
            topic = html.escape(it.get("topic") or "")
            if url:
                parts.append(
                    f'<li><strong>[{topic}]</strong> <a href="{html.escape(url)}" '
                    f'rel="noopener noreferrer">{tit}</a><br><span class="stock-snippet">{snip}</span></li>'
                )
            else:
                parts.append(f"<li><strong>[{topic}]</strong> {tit}<br>{snip}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("채권젬마 조사 대기"))

    oil_war = ins.get("oil_war") or {}
    parts.append("<h2>10. 원유·전쟁(지정학)과 증시 영향</h2>")
    ow_quotes = oil_war.get("oil_quotes") or []
    if ow_quotes:
        parts.append("<ul>")
        for q in ow_quotes:
            parts.append(
                _li(
                    f"{q.get('name')}: {q.get('price')} "
                    f"({float(q.get('change_pct') or 0):+.2f}%)"
                )
            )
        parts.append("</ul>")
        parts.append(
            _p(
                "분쟁·제재·공급 차질 뉴스는 단기 유가·안전자산·방산·정유 업종에 영향을 줄 수 있습니다. "
                "헤드라인만으로 매매하지 말고 재고·OPEC·환율·금리를 함께 확인하세요."
            )
        )
    else:
        parts.append(_p("원유 시세·지정학 조사 대기"))
    if oil_war.get("items"):
        parts.append("<ul>")
        for it in oil_war.get("items")[:8]:
            tit = html.escape((it.get("title") or "")[:110])
            snip = html.escape((it.get("snippet") or "")[:200])
            url = it.get("url") or ""
            topic = html.escape(it.get("topic") or "")
            if url:
                parts.append(
                    f'<li><strong>[{topic}]</strong> <a href="{html.escape(url)}" '
                    f'rel="noopener noreferrer">{tit}</a><br><span class="stock-snippet">{snip}</span></li>'
                )
            else:
                parts.append(f"<li><strong>[{topic}]</strong> {tit}<br>{snip}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("원유·전쟁젬마 조사 대기"))

    comm = ins.get("commodities") or {}
    parts.append("<h2>11. 원자재 동향과 증시 영향</h2>")
    comm_quotes = comm.get("quotes") or []
    if comm_quotes:
        parts.append("<ul>")
        for q in comm_quotes[:8]:
            parts.append(
                _li(
                    f"{q.get('name', q.get('symbol'))}: {q.get('price')} "
                    f"({float(q.get('change_pct') or 0):+.2f}%)"
                )
            )
        parts.append("</ul>")
        parts.append(
            _p(
                "유가·금속·에너지는 정유·화학·철강·항공·2차전지 등 업종별로 "
                "영향 방향이 다릅니다. 아래 해석·기사와 함께 보세요."
            )
        )
    else:
        parts.append(_p("원자재 시세 수집 대기"))
    if comm.get("items"):
        parts.append("<ul>")
        for it in comm.get("items")[:8]:
            tit = html.escape((it.get("title") or "")[:110])
            snip = html.escape((it.get("snippet") or "")[:200])
            url = it.get("url") or ""
            topic = html.escape(it.get("topic") or "")
            if url:
                parts.append(
                    f'<li><strong>[{topic}]</strong> <a href="{html.escape(url)}" '
                    f'rel="noopener noreferrer">{tit}</a><br><span class="stock-snippet">{snip}</span></li>'
                )
            else:
                parts.append(f"<li><strong>[{topic}]</strong> {tit}<br>{snip}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("원자재젬마 조사 대기"))

    yt = ins.get("youtube") or {}
    parts.append("<h2>12. 유튜브·영상 브리핑 (참고)</h2>")
    parts.append(
        _p(
            "증시·매크로·종목 관련 유튜브 영상 링크입니다. "
            "채널 의견은 사실·공시·당일 시세와 반드시 교차하세요."
        )
    )
    if yt.get("items"):
        parts.append("<ul>")
        for it in yt.get("items")[:10]:
            if not it.get("url") and not it.get("title"):
                continue
            tit = html.escape((it.get("title") or "")[:100])
            topic = html.escape(it.get("topic") or "")
            url = it.get("url") or ""
            snip = html.escape((it.get("snippet") or "")[:120])
            if url:
                parts.append(
                    f'<li><strong>[{topic}]</strong> '
                    f'<a href="{html.escape(url)}" rel="noopener noreferrer">{tit}</a>'
                    + (f"<br><span class=\"stock-snippet\">{snip}</span>" if snip else "")
                    + "</li>"
                )
            else:
                parts.append(f"<li><strong>[{topic}]</strong> {tit}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("유튜브젬마 조사 대기"))

    ceo = ins.get("ceo_remarks") or {}
    parts.append("<h2>13. 기업 CEO·경영진 발언</h2>")
    parts.append(
        _p(
            "실적 발표·IR·인터뷰에서 나온 경영진 코멘트입니다. "
            "투자 권유가 아니며, 아래는 검색·보도 기준이며 공시·컨센서스와 반드시 대조하세요."
        )
    )
    if ceo.get("items"):
        parts.append("<ul>")
        for it in ceo.get("items")[:10]:
            tit = html.escape((it.get("title") or "")[:110])
            snip = html.escape((it.get("snippet") or "")[:180])
            quote = html.escape((it.get("quote") or "")[:160])
            url = it.get("url") or ""
            company = html.escape(it.get("company") or "")
            executive = html.escape(it.get("executive") or "")
            topic = html.escape(it.get("topic") or "")
            chg = it.get("market_change_pct")
            chg_s = f" ({float(chg):+.2f}%)" if chg is not None else ""
            head = f"<strong>{company}</strong>"
            if executive:
                head += f" · {executive}"
            if chg_s:
                head += chg_s
            body = f"<br><span class=\"stock-snippet\">「{quote}」</span>" if quote else f"<br>{snip}"
            if url:
                parts.append(
                    f"<li>{head} <em>[{topic}]</em> "
                    f'<a href="{html.escape(url)}" rel="noopener noreferrer">{tit}</a>{body}</li>'
                )
            else:
                parts.append(f"<li>{head} <em>[{topic}]</em> {tit}{body}</li>")
        parts.append("</ul>")
    else:
        parts.append(_p("CEO멘트젬마 조사 대기"))

    press = ins.get("press") or {}
    parts.append("<h2>14. 주요 언론 기사</h2>")
    if press.get("items"):
        parts.append("<ul>")
        for it in press.get("items")[:6]:
            url = html.escape(it.get("url") or "#")
            tit = html.escape((it.get("title") or "")[:100])
            parts.append(f'<li><a href="{url}" rel="noopener noreferrer">{tit}</a></li>')
        parts.append("</ul>")
    else:
        parts.append(_p("기사젬마 수집 대기"))

    news = ins.get("news") or {}
    parts.append("<h2>15. 시장 속보·이슈</h2>")
    if news.get("items"):
        parts.append("<ul>")
        for it in news.get("items")[:6]:
            url = html.escape(it.get("url") or "#")
            tit = html.escape((it.get("title") or "")[:100])
            parts.append(f'<li><a href="{url}" rel="noopener noreferrer">{tit}</a></li>')
        parts.append("</ul>")
    else:
        parts.append(_p("최신정보젬마 뉴스 수집 대기"))

    comments = ins.get("comments") or {}
    parts.append("<h2>16. 증시 댓글 검증 (참고)</h2>")
    parts.append(
        _p(
            "커뮤니티·블로그 댓글은 사실이 아닐 수 있습니다. "
            "댓글검증젬마가 웹·당일 시세와 대조한 요약입니다."
        )
    )
    if comments.get("items"):
        parts.append("<ul>")
        for it in comments.get("items")[:5]:
            parts.append(
                _li(
                    f"[{it.get('verdict')}] 글#{it.get('post_id')} — "
                    f"{(it.get('excerpt') or '')[:60]}…"
                )
            )
        parts.append("</ul>")
    else:
        parts.append(_p("최근 증시 관련 댓글 검증 건 없음"))

    risk = ins.get("risk") or {}
    if risk.get("items"):
        parts.append("<h2>17. 변동·리스크 메모</h2><ul>")
        for it in risk.get("items")[:6]:
            parts.append(_li(f"{it.get('name')}: {it.get('change_pct')}%"))
        parts.append("</ul>")

    parts.append(
        "<h2>자주 묻는 질문</h2>"
        "<p><strong>Q.</strong> 이 글만 보고 매매해도 되나요?</p>"
        "<p><strong>A.</strong> 아닙니다. 조사 요약이며 개인 상황·리스크에 따라 다릅니다.</p>"
        "<p><strong>Q.</strong> 숫자는 실시간인가요?</p>"
        "<p><strong>A.</strong> 스냅샷 시각 기준입니다. 중요한 주문 전 HTS·공식 출처를 확인하세요.</p>"
        '<p class="post-disclaimer"><strong>면책</strong> '
        "본 글은 일반 정보 제공 목적이며 투자·세무·법률 자문이 아닙니다.</p>"
    )
    return title, "\n\n".join(parts)


def _run_full_stock_research() -> None:
    """주식 시황부 전 항목 수집·조사."""
    import agent_office_stock_watch as sw

    if not sw.load_snapshot().get("updated_at"):
        sw.sync_market_data(force=True)
    try:
        import agent_office_stock_jobs as sj

        sj.run_chart_insights()
        sj.run_news_insights()
        sj.run_finance_insights()
        sj.run_risk_scan()
    except Exception:
        pass
    try:
        import agent_office_stock_official as off

        off.run_all_official()
    except Exception:
        pass
    try:
        import agent_office_stock_macro as macro

        macro.run_rates_dollar_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_commodities as comm

        comm.run_commodities_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_bonds as bonds

        bonds.run_bonds_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_oil_war as ow

        ow.run_oil_war_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_ceo_remarks as ceo

        ceo.run_ceo_remarks_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_youtube as yt

        yt.run_youtube_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_analyst as an

        an.run_analyst_insights()
    except Exception:
        pass
    try:
        import agent_office_stock_comments as sc

        sc.run_comment_verify()
    except Exception:
        pass
    try:
        import agent_office_stock_rl_predict as rl

        rl.run_predictions()
    except Exception:
        pass


def _run_quick_stock_research() -> None:
    """시세·차트·뉴스만 갱신 (공시·매크로 대량 크롤 생략)."""
    import agent_office_stock_watch as sw

    if not sw.load_snapshot().get("updated_at"):
        sw.sync_market_data(force=True)
    else:
        sw.sync_market_data(force=False)
    try:
        import agent_office_stock_jobs as sj

        sj.run_chart_insights()
        sj.run_news_insights()
        sj.run_finance_insights()
        sj.run_risk_scan()
    except Exception:
        pass
    try:
        import agent_office_stock_rl_predict as rl

        rl.run_predictions()
    except Exception:
        pass


def _build_stock_draft_content(*, full_research: bool = True) -> tuple[str, str] | None:
    if full_research:
        _run_full_stock_research()
    else:
        _run_quick_stock_research()
    today = _today()
    title, content = _build_stock_insights_html(today)
    if len(adsense._strip_html(content)) < 400:
        return None
    return title, content


def _update_draft(post_id: int, title: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE posts SET title=?, content=? WHERE id=?",
            (title[:120], content, post_id),
        )
        conn.commit()


def _insert_draft(title: str, content: str) -> int | None:
    import agent_office_blog_draft as bd

    if not DB_PATH.is_file():
        return None
    bd.ensure_posts_schema()
    author = os.getenv("AGENT_OFFICE_BLOG_AUTHOR", "머니인사이트").strip() or "머니인사이트"
    now = _now_str()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO posts (title, author, content, password, created, views, is_draft)
            VALUES (?,?,?,?,?,0,1)
            """,
            (title[:120], author, content, _draft_password(), now),
        )
        conn.commit()
        return int(cur.lastrowid)


def _create_from_stock_insights() -> int | None:
    import agent_office_stock_watch as sw

    if not sw.load_snapshot().get("updated_at"):
        sync = sw.sync_market_data(force=True)
        if not sync.get("ok"):
            return None
    pair = _build_stock_draft_content(full_research=False)
    if not pair:
        return None
    title, content = pair
    return _insert_draft(title, content)


def create_new_stock_report(
    *, full_research: bool = False, publish: bool = False
) -> dict:
    """새 주식 종합 보고서 초안 1건 생성 (기존 오늘 글과 무관하게 INSERT)."""
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    pair = _build_stock_draft_content(full_research=full_research)
    if not pair:
        return {"ok": False, "error": "empty_content"}

    title, content = pair
    plain_len = len(adsense._strip_html(content))
    post_id = _insert_draft(title, content)
    if not post_id:
        return {"ok": False, "error": "insert_failed"}

    enrich = adsense.enrich_post(post_id, db_path=DB_PATH)
    today = _today()
    state = load_state()
    state["last_draft_date"] = today
    state["last_post_id"] = post_id
    state["last_source"] = (
        "stock_insights_full" if full_research else "stock_insights_snapshot"
    )
    save_state(state)

    try:
        import blog_publish_scheduler as bps

        bps.queue_priority(post_id)
    except Exception:
        pass

    out: dict = {
        "ok": True,
        "action": "created_new",
        "post_id": post_id,
        "title": title[:80],
        "chars": plain_len,
        "enrich": enrich,
        "full_research": full_research,
    }

    if publish:
        try:
            import blog_publish_scheduler as bps

            pub = bps.publish_post_now(post_id, refresh_research=False)
            out["publish"] = pub
            if not pub.get("ok"):
                out["ok"] = False
        except Exception as e:
            out["publish"] = {"ok": False, "error": str(e)[:120]}
            out["ok"] = False

    return out


def refresh_stock_research_draft() -> dict:
    """전체 주식 조사 실행 후 오늘 조사 초안 생성·갱신."""
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    pair = _build_stock_draft_content(full_research=True)
    if not pair:
        return {"ok": False, "error": "empty_content"}

    title, content = pair
    today = _today()
    plain_len = len(adsense._strip_html(content))

    with sqlite3.connect(DB_PATH) as conn:
        existing = _find_todays_research_draft(conn, today)

    if existing:
        _update_draft(existing, title, content)
        post_id = existing
        action = "updated"
    else:
        post_id = _insert_draft(title, content)
        action = "created" if post_id else "failed"

    if not post_id:
        return {"ok": False, "error": "insert_failed"}

    enrich = adsense.enrich_post(post_id, db_path=DB_PATH)
    state = load_state()
    state["last_draft_date"] = today
    state["last_post_id"] = post_id
    state["last_source"] = "stock_insights_full"
    save_state(state)

    try:
        import blog_publish_scheduler as bps

        bps.queue_priority(post_id)
    except Exception:
        pass

    return {
        "ok": True,
        "action": action,
        "post_id": post_id,
        "title": title[:80],
        "chars": plain_len,
        "enrich": enrich,
    }


def ensure_daily_research_draft(*, force: bool = False) -> dict:
    """오늘 조사 초안 1건 확보 (이미 있으면 스킵)."""
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    today = _today()
    state = load_state()
    if state.get("last_draft_date") == today and not force:
        pid = state.get("last_post_id")
        if pid and DB_PATH.is_file():
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT 1 FROM posts WHERE id=? AND COALESCE(is_draft,0)=1",
                    (pid,),
                ).fetchone()
                if row:
                    return {
                        "ok": True,
                        "action": "already_today",
                        "post_id": pid,
                        "source": state.get("last_source"),
                    }

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    with sqlite3.connect(DB_PATH) as conn:
        existing = _find_todays_research_draft(conn, today)
        if existing and not force:
            state["last_draft_date"] = today
            state["last_post_id"] = existing
            save_state(state)
            return {"ok": True, "action": "found_existing", "post_id": existing}

    prefer = (os.getenv("BLOG_RESEARCH_DRAFT_PREFER", "both") or "both").strip().lower()
    post_id: int | None = None
    source = ""

    if prefer in ("both", "task"):
        tasks = _tasks_ready_for_draft()
        if tasks:
            post_id = _create_from_task(tasks[0])
            source = "office_task"

    if not post_id and prefer in ("both", "stock", "insights"):
        post_id = _create_from_stock_insights()
        source = "stock_insights"

    if not post_id:
        tasks = _tasks_ready_for_draft()
        if tasks and prefer == "stock":
            post_id = _create_from_task(tasks[0])
            source = "office_task"

    if not post_id:
        return {"ok": True, "action": "nothing_to_draft", "message": "조사 원천 없음"}

    state["last_draft_date"] = today
    state["last_post_id"] = post_id
    state["last_source"] = source
    save_state(state)

    try:
        import blog_publish_scheduler as bps

        bps.queue_priority(post_id)
    except Exception:
        pass

    return {"ok": True, "action": "created", "post_id": post_id, "source": source}


def status() -> dict:
    st = load_state()
    today = _today()
    draft_today = None
    if DB_PATH.is_file():
        with sqlite3.connect(DB_PATH) as conn:
            draft_today = _find_todays_research_draft(conn, today)
    return {
        "enabled": _enabled(),
        "today": today,
        "draft_today": draft_today,
        "state": st,
        "tasks_ready": len(_tasks_ready_for_draft()),
    }


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass

    p = argparse.ArgumentParser()
    p.add_argument(
        "cmd",
        choices=["ensure", "status", "refresh", "new"],
        nargs="?",
        default="ensure",
    )
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--full",
        action="store_true",
        help="new/refresh: 공시·매크로·CEO 등 전체 조사 포함 (수 분 소요)",
    )
    p.add_argument(
        "--publish",
        action="store_true",
        help="new: 초안 작성 후 즉시 공개",
    )
    args = p.parse_args()
    if args.cmd == "status":
        out = status()
    elif args.cmd == "refresh":
        out = refresh_stock_research_draft()
    elif args.cmd == "new":
        out = create_new_stock_report(
            full_research=args.full, publish=args.publish
        )
    else:
        out = ensure_daily_research_draft(force=args.force)
    print(out)
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
