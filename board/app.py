from flask import Flask, render_template, request, redirect, url_for, flash, g, Response, session, abort, jsonify, send_from_directory
from functools import wraps
import csv
import io
import json
import re
import secrets
import sqlite3
import os
import sys
from datetime import datetime, timedelta

import security_utils
import home_qa_reply

app = Flask(__name__)
_default_secret = "board-secret-key-2026"
app.secret_key = os.environ.get("FLASK_SECRET_KEY", _default_secret)
app.permanent_session_lifetime = timedelta(days=14)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "1").strip().lower()
    in ("1", "true", "yes"),
    MAX_CONTENT_LENGTH=int(os.environ.get("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024))),
)

if security_utils.using_default_flask_secret(app.secret_key):
    app.logger.warning(
        "FLASK_SECRET_KEY is not set or uses the default. Set a strong secret in production."
    )


@app.after_request
def _security_after_request(response):
    return security_utils.apply_security_headers(response)


_CSRF_EXEMPT_ENDPOINTS = frozenset({
    "agent_office_local_code_sync",
    "shorts_stripe_webhook",
})


@app.before_request
def _security_before_request():
    security_utils.ensure_csrf_token()
    if request.method in security_utils.UNSAFE_METHODS:
        if request.endpoint in _CSRF_EXEMPT_ENDPOINTS:
            return
        security_utils.validate_csrf_request()


@app.context_processor
def _security_context():
    return {
        "csrf_token": security_utils.ensure_csrf_token(),
        "blog_write_allowed": _blog_write_allowed(),
    }


@app.template_filter("nl2br")
def nl2br_filter(value):
    return security_utils.nl2br(value)


@app.template_filter("safe_post_html")
def safe_post_html_filter(value):
    return security_utils.safe_post_html(value)


@app.template_filter("intcomma")
def intcomma_filter(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


DB_PATH = os.environ.get(
    "BOARD_DB_PATH",
    os.path.join(os.path.dirname(__file__), "board.db"),
)
SITE_NAME = os.environ.get("SITE_NAME", "머니인사이트")
SITE_CONTACT_EMAIL = os.environ.get("SITE_CONTACT_EMAIL", "admin@coupax.co.kr")
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "").strip()
AGENT_OFFICE_CONTROL_TOKEN = os.environ.get("AGENT_OFFICE_CONTROL_TOKEN", "").strip()
AGENT_OFFICE_ACCESS_PASSWORD = (
    os.environ.get("AGENT_OFFICE_ACCESS_PASSWORD", "").strip()
    or AGENT_OFFICE_CONTROL_TOKEN
)
SHORTS_ADMIN_PASSWORD = (
    os.environ.get("SHORTS_ADMIN_PASSWORD", "").strip()
    or AGENT_OFFICE_ACCESS_PASSWORD
)

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import agent_office_tasks as _agent_office_tasks
import etf_ops_policy


def etf_ops_enabled() -> bool:
    return etf_ops_policy.etf_ops_enabled()


@app.context_processor
def inject_etf_ops():
    return {"etf_ops_enabled": etf_ops_enabled()}


def _etf_public_blocked():
    if etf_ops_enabled():
        return None
    return render_template("etf_suspended.html"), 503


# 시드 글 등 본문에 붙는 카테고리 태그 (deploy/seed_adsense_posts.py 와 동일)
ETF_CATEGORY_MARKER = "[카테고리] ETF·주식"
ETF_THEME_ORDER = (
    "월배당·현금흐름",
    "적립식·매수·리스크",
    "해외·환율·글로벌",
    "배당·분배금",
    "세금·비용·계좌",
    "기타 ETF 주제",
)

BLOG_PER_PAGE = 15

HOME_QA_POST_TITLE = os.environ.get(
    "HOME_QA_POST_TITLE", "머니인사이트 질문·답변"
).strip()
HOME_QA_TOPICS = (
    "ETF·주식",
    "연금·보험",
    "절세·세금",
    "부동산·청약",
    "예적금·금리",
    "기타",
)
HOME_QUESTION_MARKER = "[질문]"


def _post_content(post) -> str:
    if not post:
        return ""
    if isinstance(post, dict):
        return str(post.get("content") or "")
    try:
        keys = post.keys() if hasattr(post, "keys") else []
        if "content" in keys:
            return str(post["content"] or "")
    except Exception:
        pass
    return ""


def _is_home_question_post(post) -> bool:
    return _post_content(post).strip().startswith(HOME_QUESTION_MARKER)


def _post_display_author(post, *, is_question: bool | None = None) -> str:
    is_q = is_question if is_question is not None else _is_home_question_post(post)
    if is_q:
        name = (post.get("author") if isinstance(post, dict) else post["author"]) or ""
        name = str(name).strip()
        if name:
            return name
    pid = post.get("id") if isinstance(post, dict) else post["id"]
    return blog_pen_name(int(pid or 0))


def _question_post_title(content: str, topic: str) -> str:
    line = re.sub(r"\s+", " ", content.strip().replace("\n", " "))[:56]
    if len(content.strip()) > 56:
        line += "…"
    prefix = f"[{topic}] " if topic else ""
    title = f"{prefix}{line}" if line else "질문"
    if not title.startswith("Q."):
        title = f"Q. {title}"
    return title[:120]


def _question_post_body(author: str, content: str, topic: str) -> str:
    from markupsafe import escape as html_escape

    topic = topic or "기타"
    q = html_escape(content.strip())
    who = html_escape(author.strip())
    cat = html_escape(topic)
    return (
        f"{HOME_QUESTION_MARKER}\n"
        f'<div class="question-post-card">\n'
        f'<p class="question-post-topic"><strong>주제</strong> {cat}</p>\n'
        f'<p class="question-post-text">{q}</p>\n'
        f'<p class="question-post-meta">{who} 님 · 홈 질문창</p>\n'
        "</div>\n"
        '<p class="question-post-hint">젬마24 답변과 추가 질문은 아래 <strong>대화</strong> 댓글에서 이어집니다.</p>'
    )


def _create_question_post(
    db, author: str, content: str, password: str, topic: str = ""
) -> tuple[int, str, str]:
    """홈 질문 → 새 블로그 글. (post_id, title, created)"""
    topic = (topic or "").strip() or "기타"
    title = _question_post_title(content, topic)
    body = _question_post_body(author, content, topic)
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = db.execute(
        "INSERT INTO posts (title, author, content, password, created) VALUES (?,?,?,?,?)",
        (
            title,
            author.strip(),
            body,
            security_utils.hash_password(password),
            created,
        ),
    )
    post_id = int(cur.lastrowid)
    db.commit()
    return post_id, title, created

# 글 ID 기준 고정 필명 (목록·본문 동일)
BLOG_PEN_NAMES = (
    "재테크왈라",
    "머니로드",
    "절세메이트",
    "ETF살펴보기",
    "배당플로우",
    "연금탐구",
    "청약체크",
    "금융한줄",
    "투자습관",
    "현금흐름랩",
    "코드노트",
    "살림손익",
    "자산지도",
    "월급쪼개기",
    "복리메모",
    "세금노트",
    "주식습관",
    "펀드체크",
    "배당일기",
    "재무설계",
    "경제읽기",
    "포트폴리오랩",
    "절약실험",
    "투자기록",
    "자산성장",
)


def blog_pen_name(post_id: int) -> str:
    pid = int(post_id or 0)
    return BLOG_PEN_NAMES[(pid * 2654435761) % len(BLOG_PEN_NAMES)]


@app.template_filter("blog_pen_name")
def blog_pen_name_filter(post_id):
    return blog_pen_name(post_id)


def format_agent_interval(agent: dict) -> str:
    if not isinstance(agent, dict):
        return "—"
    label = (agent.get("interval_label") or "").strip()
    if label:
        return label
    try:
        minutes = int(agent.get("interval_minutes"))
    except (TypeError, ValueError):
        minutes = 120
    if minutes <= 0:
        return "항상"
    return f"{minutes}분마다"


@app.template_filter("agent_interval")
def agent_interval_filter(agent):
    return format_agent_interval(agent)

def _sort_etf_rows_by_total_return(rows: list) -> None:
    """총 수익률(total_return_pct) 내림차순. 값 없음은 맨 아래."""

    def _key(row: dict) -> float:
        if not isinstance(row, dict):
            return -999.0
        v = row.get("total_return_pct")
        try:
            return float(v) if v is not None else -999.0
        except (TypeError, ValueError):
            return -999.0

    rows.sort(key=_key, reverse=True)
    for i, row in enumerate(rows, start=1):
        if isinstance(row, dict):
            row["no"] = i


def parse_market_cap_억(value) -> float | None:
    """시가총액 문자열(예: 1,183억, 56552억) → 억 단위 숫자."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "").replace(" ", "")
    if not s or s == "—":
        return None
    s = s.replace("억", "")
    s = re.sub(r"만", "", s)
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def build_brand_summaries(rows: list) -> list[dict]:
    """브랜드별 종목 수·평균 배당수익률·시총 합 등 요약."""
    buckets: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        brand = (row.get("brand") or "").strip() or "기타"
        b = buckets.setdefault(
            brand,
            {
                "brand": brand,
                "count": 0,
                "mcap_sum": 0.0,
                "mcap_n": 0,
                "yield_sum": 0.0,
                "yield_n": 0,
                "div_sum": 0.0,
                "div_n": 0,
            },
        )
        b["count"] += 1
        mcap = parse_market_cap_억(row.get("market_cap"))
        if mcap is not None:
            b["mcap_sum"] += mcap
            b["mcap_n"] += 1
        try:
            yf = float(row.get("dividend_yield_pct"))
        except (TypeError, ValueError):
            yf = None
        if yf is not None:
            b["yield_sum"] += yf
            b["yield_n"] += 1
        months = row.get("months") if isinstance(row.get("months"), list) else []
        for m in months:
            if m is not None:
                try:
                    b["div_sum"] += float(m)
                    b["div_n"] += 1
                except (TypeError, ValueError):
                    pass

    out: list[dict] = []
    for b in buckets.values():
        avg_yield = round(b["yield_sum"] / b["yield_n"], 2) if b["yield_n"] else None
        dn = b["div_n"]
        avg_div = round(b["div_sum"] / dn, 0) if dn else None
        mcap_label = f"{int(b['mcap_sum']):,}억" if b["mcap_n"] else "—"
        if b["mcap_n"] and dn < b["count"]:
            mcap_label += f" ({b['mcap_n']}종 합산)"
        out.append(
            {
                "brand": b["brand"],
                "count": b["count"],
                "mcap_sum_label": mcap_label,
                "avg_yield_pct": avg_yield,
                "avg_monthly_div": avg_div,
            }
        )
    out.sort(key=lambda x: (-x["count"], x["brand"]))
    return out


AGENT_OFFICE_KIND_LABELS = {
    "chat": "잡담",
    "task": "작업",
    "handoff": "핸드오프",
    "debate": "토론",
    "system": "시스템",
    "conclusion": "결론",
}


def load_agent_office_feed():
    """에이전트 사무실 피드 JSON."""
    path = os.path.join(os.path.dirname(__file__), "data", "agent_office_feed.json")
    empty = {
        "office_name": "젬마24 에이전트 사무실",
        "office_tagline": "주제는 무엇이든 물어보세요",
        "description": "",
        "updated_at": "",
        "agents": [],
        "messages": [],
    }
    if not os.path.isfile(path):
        return empty
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return empty
        data.setdefault("office_name", empty["office_name"])
        data.setdefault("office_tagline", empty["office_tagline"])
        data.setdefault("description", "")
        data.setdefault("updated_at", "")
        agents = data.get("agents")
        data["agents"] = agents if isinstance(agents, list) else []
        messages = data.get("messages")
        if isinstance(messages, list):
            messages.sort(
                key=lambda m: (
                    (m.get("ts") or "") if isinstance(m, dict) else "",
                    (m.get("id") or 0) if isinstance(m, dict) else 0,
                ),
                reverse=True,
            )
        else:
            data["messages"] = []
        return data
    except (OSError, json.JSONDecodeError):
        return empty


def agent_office_roster_map(agents: list) -> dict:
    """agent id → agent dict (스킬·mode 포함)."""
    out: dict = {}
    for a in agents or []:
        if not isinstance(a, dict):
            continue
        aid = (a.get("id") or "").strip()
        if aid:
            out[aid] = a
    return out


AGENT_OFFICE_TASK_STATUS_LABELS = {
    "queued": "대기",
    "in_progress": "진행 중",
    "done": "완료",
    "cancelled": "취소",
}


def load_agent_office_tasks() -> list:
    path = os.path.join(os.path.dirname(__file__), "data", "agent_office_tasks.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        tasks = data.get("tasks") if isinstance(data, dict) else []
        if not isinstance(tasks, list):
            return []
        tasks.sort(key=lambda t: (t.get("id") or 0) if isinstance(t, dict) else 0, reverse=True)
        return tasks
    except (OSError, json.JSONDecodeError):
        return []


def _filter_office_messages(messages: list, agents: list, division: str) -> list:
    import agent_registry

    saju_ids = agent_registry.agent_ids_for_division(agents, agent_registry.DIVISION_SAJU)
    kiwoom_ids = agent_registry.agent_ids_for_division(agents, agent_registry.DIVISION_KIWOM)
    stock_ids = agent_registry.agent_ids_for_division(agents, agent_registry.DIVISION_STOCK)
    design_ids = agent_registry.agent_ids_for_division(agents, agent_registry.DIVISION_DESIGN)
    workisus_ids = agent_registry.agent_ids_for_division(agents, agent_registry.DIVISION_WORKISUS)
    gwansang_ids = agent_registry.agent_ids_for_division(agents, agent_registry.DIVISION_GWANSANG)
    other_ids = saju_ids | kiwoom_ids | stock_ids | design_ids | workisus_ids | gwansang_ids
    out: list = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        d = (m.get("division") or "").strip()
        if d:
            if d == division:
                out.append(m)
            continue
        fr = (m.get("from") or "").strip()
        to = (m.get("to") or "").strip()
        if division == agent_registry.DIVISION_SAJU:
            if fr in saju_ids or (to and to in saju_ids):
                out.append(m)
        elif division == agent_registry.DIVISION_KIWOM:
            if fr in kiwoom_ids or (to and to in kiwoom_ids):
                out.append(m)
        elif division == agent_registry.DIVISION_STOCK:
            if fr in stock_ids or (to and to in stock_ids):
                out.append(m)
        elif division == agent_registry.DIVISION_DESIGN:
            if fr in design_ids or (to and to in design_ids):
                out.append(m)
        elif division == agent_registry.DIVISION_WORKISUS:
            if fr in workisus_ids or (to and to in workisus_ids):
                out.append(m)
        elif division == agent_registry.DIVISION_GWANSANG:
            if fr in gwansang_ids or (to and to in gwansang_ids):
                out.append(m)
        else:
            if fr not in other_ids and (not to or to not in other_ids):
                out.append(m)
    return out


def _filter_office_tasks(tasks: list, division: str) -> list:
    out: list = []
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        td = (t.get("division") or "finance").strip()
        if td == division:
            out.append(t)
    return out


def _agent_office_context():
    import agent_registry

    feed = load_agent_office_feed()
    registry = agent_registry.load_registry()
    agents = agent_registry.merge_agents_for_office(feed, registry)
    finance_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_FINANCE
    )
    saju_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_SAJU
    )
    kiwoom_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_KIWOM
    )
    stock_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_STOCK
    )
    design_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_DESIGN
    )
    workisus_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_WORKISUS
    )
    gwansang_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_GWANSANG
    )
    chief_dev_agents = agent_registry.filter_agents_by_division(
        agents, agent_registry.DIVISION_CHIEF_DEV
    )
    roster = agent_office_roster_map(agents)
    roster["ceo"] = {"id": "ceo", "name": "대표님", "emoji": "👤", "role": "작업 지시"}
    messages = feed.get("messages") if isinstance(feed.get("messages"), list) else []
    tasks = load_agent_office_tasks()
    finance_messages = _filter_office_messages(
        messages, agents, agent_registry.DIVISION_FINANCE
    )
    saju_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_SAJU)
    kiwoom_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_KIWOM)
    stock_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_STOCK)
    design_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_DESIGN)
    workisus_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_WORKISUS)
    gwansang_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_GWANSANG)
    chief_dev_messages = _filter_office_messages(messages, agents, agent_registry.DIVISION_CHIEF_DEV)
    finance_tasks = _filter_office_tasks(tasks, agent_registry.DIVISION_FINANCE)
    saju_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_SAJU),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    kiwoom_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_KIWOM),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    stock_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_STOCK),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    design_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_DESIGN),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    workisus_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_WORKISUS),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    gwansang_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_GWANSANG),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    chief_dev_tasks = sorted(
        _filter_office_tasks(tasks, agent_registry.DIVISION_CHIEF_DEV),
        key=lambda t: t.get("id") or 0,
        reverse=True,
    )
    finance_queue = {"mode": "reserved", "active": 0, "target": 3, "label": "예약"}
    saju_queue = {"mode": "reserved", "active": 0, "target": 3, "label": "명리 예약"}
    try:
        import agent_office_council

        finance_queue = agent_office_council.queue_status(agent_registry.DIVISION_FINANCE)
        saju_queue = agent_office_council.queue_status(agent_registry.DIVISION_SAJU)
    except Exception:
        pass
    kiwoom_queue = {"mode": "reserved", "active": 0, "target": 3, "label": "차수 예약"}
    try:
        import agent_office_kiwoom_reserved_tasks as kiwoom_reserved

        kiwoom_queue = {
            "mode": "reserved",
            "active": kiwoom_reserved.count_reserved_active(),
            "target": max(1, int(os.getenv("AGENT_OFFICE_KIWOM_RESERVED_QUEUE", "3") or "3")),
            "label": "차수 예약",
        }
    except Exception:
        pass
    return {
        "office": feed,
        "registry": registry,
        "agents": agents,
        "finance_agents": finance_agents,
        "saju_agents": saju_agents,
        "kiwoom_agents": kiwoom_agents,
        "stock_agents": stock_agents,
        "design_agents": design_agents,
        "workisus_agents": workisus_agents,
        "gwansang_agents": gwansang_agents,
        "chief_dev_agents": chief_dev_agents,
        "roster": roster,
        "messages": finance_messages,
        "finance_messages": finance_messages,
        "saju_messages": saju_messages,
        "kiwoom_messages": kiwoom_messages,
        "stock_messages": stock_messages,
        "design_messages": design_messages,
        "workisus_messages": workisus_messages,
        "gwansang_messages": gwansang_messages,
        "chief_dev_messages": chief_dev_messages,
        "tasks": finance_tasks,
        "finance_tasks": finance_tasks,
        "saju_tasks": saju_tasks,
        "kiwoom_tasks": kiwoom_tasks,
        "stock_tasks": stock_tasks,
        "design_tasks": design_tasks,
        "workisus_tasks": workisus_tasks,
        "gwansang_tasks": gwansang_tasks,
        "chief_dev_tasks": chief_dev_tasks,
        "task_status_labels": AGENT_OFFICE_TASK_STATUS_LABELS,
        "kind_labels": AGENT_OFFICE_KIND_LABELS,
        "office_control_enabled": _office_session_ok(),
        "office_always_on": bool(registry.get("office_always_on") or registry.get("global_always_on")),
        "global_always_on": bool(registry.get("global_always_on")),
        "reserved_queue_target": finance_queue["target"],
        "reserved_queue_active": finance_queue["active"],
        "reserved_queue_label": finance_queue["label"],
        "reserved_queue_mode": finance_queue["mode"],
        "saju_reserved_queue_target": saju_queue["target"],
        "saju_reserved_active": saju_queue["active"],
        "saju_reserved_queue_label": saju_queue["label"],
        "saju_reserved_queue_mode": saju_queue["mode"],
        "saju_council_verified": saju_queue.get("verified", 0),
        "saju_council_total": saju_queue.get("total", 0),
        "kiwoom_reserved_queue_target": kiwoom_queue["target"],
        "kiwoom_reserved_active": kiwoom_queue["active"],
        "kiwoom_reserved_queue_label": kiwoom_queue["label"],
        "kiwoom_reserved_queue_mode": kiwoom_queue["mode"],
        "knowledge": load_gemma_knowledge_summary(),
        "saju_knowledge": _load_saju_knowledge_summary(),
        "saju_learn": _load_saju_learn_summary(),
        "kiwoom_knowledge": _load_kiwoom_knowledge_summary(),
        "kiwoom_learn": _load_kiwoom_learn_summary(),
        "kiwoom_account": _load_kiwoom_account_summary(),
        "stock_watch": _load_stock_watch_summary(),
        "design_knowledge": _load_design_knowledge_summary(),
        "design_learn": _load_design_learn_summary(),
        "workisus_knowledge": _load_workisus_knowledge_summary(),
        "workisus_learn": _load_workisus_learn_summary(),
        "gwansang_knowledge": _load_gwansang_knowledge_summary(),
        "gwansang_learn": _load_gwansang_learn_summary(),
        "division_meta": agent_registry.DIVISION_META,
    }


def _load_stock_watch_summary() -> dict:
    try:
        import agent_office_stock_watch as sw

        snap = sw.load_snapshot()
        st = sw.stats()
        st["snapshot"] = snap
        st["summary"] = sw.summary_text()
        mk = snap.get("markets") or {}
        kr_mk = mk.get("kr") or {}
        us_mk = mk.get("us") or {}
        st["kr_quotes"] = sw.iter_kr_quotes(snap)
        st["us_quotes"] = list(us_mk.get("indices") or []) + list(
            us_mk.get("watchlist") or []
        )
        st["alerts"] = snap.get("alerts") or []
        st["insights"] = sw.load_insights()
        return st
    except Exception:
        return {
            "updated_at": "",
            "last_sync_ok": False,
            "kr_indices": 0,
            "kr_kospi200": 0,
            "kr_kosdaq150": 0,
            "kr_watchlist": 0,
            "us_indices": 0,
            "us_watchlist": 0,
            "snapshot": {},
            "summary": "",
            "kr_quotes": [],
            "us_quotes": [],
            "alerts": [],
            "insights": {},
        }


def _load_saju_learn_summary() -> dict:
    try:
        import agent_office_saju_learn

        st = agent_office_saju_learn.stats()
        st["cards"] = agent_office_saju_learn.list_cards(limit=100)
        st["pack_path"] = "board/data/saju_learning/saju_knowledge_pack.json"
        return st
    except Exception:
        return {"total": 0, "pending": 0, "confirmed": 0, "cards": [], "updated_at": ""}


def _load_kiwoom_learn_summary() -> dict:
    try:
        import agent_office_kiwoom_learn

        st = agent_office_kiwoom_learn.stats()
        st["cards"] = agent_office_kiwoom_learn.list_cards(limit=30)
        st["pack_path"] = "board/data/kiwoom_learning/kiwoom_knowledge_pack.json"
        return st
    except Exception:
        return {"total": 0, "pending": 0, "confirmed": 0, "cards": [], "updated_at": ""}


def _load_design_learn_summary() -> dict:
    try:
        import agent_office_homepage_design_learn as dl

        st = dl.stats()
        st["cards"] = dl.list_cards(limit=40)
        st["pack_path"] = "board/data/homepage_design_learning/homepage_design_knowledge_pack.json"
        return st
    except Exception:
        return {
            "total": 0,
            "pending": 0,
            "confirmed": 0,
            "debate_cards": 0,
            "cards": [],
            "updated_at": "",
        }


def _load_gwansang_learn_summary() -> dict:
    try:
        import agent_office_gwansang_learn as gl

        st = gl.stats()
        st["cards"] = gl.list_cards(limit=40)
        st["pack_path"] = "board/data/gwansang_learning/gwansang_knowledge_pack.json"
        return st
    except Exception:
        return {"total": 0, "pending": 0, "confirmed": 0, "cards": [], "updated_at": ""}


def _load_gwansang_knowledge_summary() -> dict:
    try:
        import agent_office_wiki_store

        return agent_office_wiki_store.knowledge_stats(agent_office_wiki_store.DOMAIN_GWANSANG)
    except Exception:
        return {"updated_at": "", "wiki_count": 0, "meta_count": 0, "recent_wiki": []}


def _load_design_knowledge_summary() -> dict:
    try:
        import agent_office_wiki_store

        return agent_office_wiki_store.knowledge_stats(agent_office_wiki_store.DOMAIN_DESIGN)
    except Exception:
        return {
            "updated_at": "",
            "wiki_count": 0,
            "meta_count": 0,
            "recent_wiki": [],
        }


def _workisus_card_production_blocked_response():
    import workisus_learn_policy as wlp

    return Response(
        json.dumps({"ok": False, "error": wlp.disabled_message()}, ensure_ascii=False),
        status=403,
        mimetype="application/json; charset=utf-8",
    )


def _load_workisus_learn_summary() -> dict:
    try:
        import agent_office_workisus_learn as wl
        import workisus_learn_policy as wlp

        st = wl.stats()
        st["cards"] = wl.list_cards(limit=40)
        st["pack_path"] = "board/data/workisus_learning/workisus_knowledge_pack.json"
        st["card_production_enabled"] = wlp.is_card_production_enabled()
        import workisus_wiki_rules as wr

        st["wiki_rules"] = wr.wiki_status()
        return st
    except Exception:
        return {
            "total": 0,
            "pending": 0,
            "confirmed": 0,
            "cards": [],
            "updated_at": "",
            "card_production_enabled": False,
            "wiki_rules": {"ok": False, "wiki_id": "wonkisus-grid-trading-rules"},
        }


def _load_workisus_knowledge_summary() -> dict:
    try:
        import agent_office_wiki_store

        return agent_office_wiki_store.knowledge_stats(agent_office_wiki_store.DOMAIN_WORKISUS)
    except Exception:
        return {
            "updated_at": "",
            "wiki_count": 0,
            "meta_count": 0,
            "recent_wiki": [],
        }


def _load_kiwoom_account_summary() -> dict:
    try:
        import agent_office_kiwoom_account

        agent_office_kiwoom_account.import_from_env_file()
        snap = agent_office_kiwoom_account.load_snapshot()
        st = agent_office_kiwoom_account.stats()
        acct = {}
        accounts = snap.get("accounts") or []
        if accounts and isinstance(accounts[0], dict):
            acct = accounts[0]
        return {
            "snapshot": snap,
            "stats": st,
            "account": acct,
            "summary_lines": agent_office_kiwoom_account.summary_lines(),
            "positions": snap.get("positions") or [],
        }
    except Exception:
        return {
            "snapshot": {},
            "stats": {"has_data": False, "stale": True},
            "account": {},
            "summary_lines": [],
            "positions": [],
        }


def _load_kiwoom_knowledge_summary() -> dict:
    try:
        import agent_office_wiki_store

        return agent_office_wiki_store.knowledge_stats(agent_office_wiki_store.DOMAIN_KIWOM)
    except Exception:
        return {
            "updated_at": "",
            "wiki_count": 0,
            "meta_count": 0,
            "recent_wiki": [],
        }


def _office_access_configured() -> bool:
    return bool(AGENT_OFFICE_ACCESS_PASSWORD)


def _office_session_ok() -> bool:
    return session.get("agent_office_auth") is True


def _shorts_admin_ok() -> bool:
    return session.get("shorts_admin_auth") is True or _office_session_ok()


def _shorts_admin_configured() -> bool:
    return bool(SHORTS_ADMIN_PASSWORD)


def _blog_write_allowed() -> bool:
    if security_utils.blog_write_open():
        return True
    return _office_session_ok()


def _verify_post_password(db, post_id: int, plain: str, stored: str | None) -> bool:
    if not security_utils.verify_password(plain, stored):
        return False
    security_utils.upgrade_password_if_legacy(db, "posts", post_id, plain, stored)
    return True


def _home_qa_post_id(db) -> int:
    """홈 질문창이 연결되는 Q&A 전용 글 ID (없으면 생성)."""
    env_id = os.environ.get("HOME_QA_POST_ID", "").strip()
    if env_id.isdigit():
        row = db.execute(
            f"SELECT id FROM posts WHERE id = ? AND {_POST_PUBLISHED_SQL}",
            (int(env_id),),
        ).fetchone()
        if row:
            return int(row["id"])

    row = db.execute(
        f"""
        SELECT id FROM posts
        WHERE title LIKE ? AND {_POST_PUBLISHED_SQL}
        ORDER BY id DESC LIMIT 1
        """,
        (f"%{HOME_QA_POST_TITLE}%",),
    ).fetchone()
    if row:
        return int(row["id"])

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    intro = (
        "ETF·연금·절세·청약·예적금 등 머니인사이트 주제에 대한 질문을 받는 공간입니다.\n"
        "홈 화면 질문창 또는 아래 질문란에 남겨 주시면 참고 답변을 드립니다.\n"
        "답변은 일반 정보 제공 목적이며, 투자·세무·법률 자문이 아닙니다."
    )
    draft_pw = os.environ.get("HOME_QA_POST_PASSWORD") or secrets.token_urlsafe(16)
    cur = db.execute(
        "INSERT INTO posts (title, author, content, password, created) VALUES (?,?,?,?,?)",
        (
            HOME_QA_POST_TITLE,
            SITE_NAME,
            intro,
            security_utils.hash_password(draft_pw),
            now,
        ),
    )
    db.commit()
    return int(cur.lastrowid)


def _insert_question_comment(
    db,
    post_id: int,
    author: str,
    content: str,
    password: str,
    topic: str = "",
) -> int:
    body = content.strip()
    topic = (topic or "").strip()
    if topic and topic in HOME_QA_TOPICS and not body.startswith("["):
        body = f"[{topic}] {body}"
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = db.execute(
        "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
        (
            post_id,
            author.strip(),
            body,
            security_utils.hash_password(password),
            created,
        ),
    )
    db.commit()
    return int(cur.lastrowid)


def _verify_comment_password(db, comment_id: int, plain: str, stored: str | None) -> bool:
    if not security_utils.verify_password(plain, stored):
        return False
    security_utils.upgrade_password_if_legacy(db, "comments", comment_id, plain, stored)
    return True


def require_office_access(view):
    """대표님·젬마24 전용 사무실 — 비밀번호 세션 필요."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not _office_access_configured():
            return Response(
                "에이전트 사무실 접근 비밀번호가 서버에 설정되지 않았습니다.",
                status=503,
                mimetype="text/plain; charset=utf-8",
            )
        if not _office_session_ok():
            if request.path.startswith("/api/agents/"):
                return Response(
                    json.dumps({"ok": False, "error": "login_required"}, ensure_ascii=False),
                    status=401,
                    mimetype="application/json; charset=utf-8",
                )
            nxt = request.url
            return redirect(url_for("agent_office_login", next=nxt))
        return view(*args, **kwargs)

    return wrapped


def _check_office_control_token() -> bool:
    if not AGENT_OFFICE_CONTROL_TOKEN:
        return False
    supplied = (
        request.headers.get("X-Office-Token")
        or request.form.get("token")
        or (request.get_json(silent=True) or {}).get("token")
        or ""
    )
    return supplied.strip() == AGENT_OFFICE_CONTROL_TOKEN


def _office_mode_control_allowed() -> bool:
    """사무실 로그인 세션이면 ON/OFF 변경 허용 (별도 제어 토큰 불필요)."""
    return _office_session_ok()


def load_monthly_dividend_sheet():
    """스프레드시트 형식 월배당 데이터(JSON). 파일이 없거나 오류 시 빈 시트."""
    path = os.path.join(os.path.dirname(__file__), "data", "monthly_dividend_etfs.json")
    if not os.path.isfile(path):
        return {
            "year": 2026,
            "rows": [],
            "dividend_unit": "",
            "note": "",
            "pipeline_note": "",
            "data_sources": [],
        }
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {
                "year": 2026,
                "rows": [],
                "dividend_unit": "",
                "note": "",
                "pipeline_note": "",
                "data_sources": [],
            }
        data.setdefault("year", 2026)
        data.setdefault("rows", [])
        data.setdefault("dividend_unit", "")
        data.setdefault("note", "")
        data.setdefault("pipeline_note", "")
        data.setdefault("data_sources", [])
        rows = data.get("rows")
        if isinstance(rows, list):
            _sort_etf_rows_by_total_return(rows)
        return data
    except (OSError, json.JSONDecodeError):
        return {
            "year": 2026,
            "rows": [],
            "dividend_unit": "",
            "note": "",
            "pipeline_note": "",
            "data_sources": [],
        }


def fetch_etf_related_posts(db):
    """제목·본문의 ETF 언급 또는 시드 카테고리 태그로 관련 글 수집."""
    return db.execute(
        """
        SELECT * FROM posts
        WHERE content LIKE ?
           OR instr(lower(title), 'etf') > 0
           OR instr(lower(content), 'etf') > 0
        ORDER BY id DESC
        """,
        (f"%{ETF_CATEGORY_MARKER}%",),
    ).fetchall()


def extract_post_keywords_line(content: str) -> str:
    """시드 글의 [키워드] 블록 첫 줄 — 본문 공통 면책 문구와 섞이지 않게 분류에만 사용."""
    if not content or "[키워드]" not in content:
        return ""
    tail = content.split("[키워드]", 1)[1]
    for line in tail.splitlines():
        s = line.strip()
        if s and not s.startswith("["):
            return s
    return ""


def classify_etf_theme(title: str, content: str) -> str:
    blob = f"{title}\n{extract_post_keywords_line(content)}"
    if "월배당" in blob or "월 배당" in blob:
        return "월배당·현금흐름"
    if any(
        k in blob
        for k in (
            "적립",
            "매수 규칙",
            "분할매수",
            "손실",
            "리밸런싱",
            "낙폭",
            "DCA",
        )
    ):
        return "적립식·매수·리스크"
    if any(
        k in blob
        for k in (
            "해외ETF",
            "해외 ETF",
            "미국",
            "S&P",
            "나스닥",
            "달러",
            "환전",
            "환율",
            "글로벌",
            "환헤지",
        )
    ):
        return "해외·환율·글로벌"
    if "배당" in blob or "분배" in blob:
        return "배당·분배금"
    if any(
        k in blob
        for k in (
            "세금",
            "과세",
            "ISA",
            "양도",
            "절세",
            "소득세",
            "배당소득",
        )
    ):
        return "세금·비용·계좌"
    return "기타 ETF 주제"


def group_etf_posts_by_theme(rows):
    buckets = {k: [] for k in ETF_THEME_ORDER}
    for row in rows:
        theme = classify_etf_theme(row["title"], row["content"])
        if theme not in buckets:
            theme = "기타 ETF 주제"
        buckets[theme].append(row)
    return [(k, buckets[k]) for k in ETF_THEME_ORDER if buckets[k]]


def fetch_monthly_dividend_posts(db):
    return db.execute(
        """
        SELECT * FROM posts
        WHERE title LIKE '%월배당%'
           OR content LIKE '%월배당%'
           OR title LIKE '%월 배당%'
           OR content LIKE '%월 배당%'
        ORDER BY id DESC
        """
    ).fetchall()


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        _ensure_posts_columns(g.db)
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


def _ensure_posts_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
    if "is_draft" not in cols:
        conn.execute("ALTER TABLE posts ADD COLUMN is_draft INTEGER DEFAULT 0")


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                title    TEXT NOT NULL,
                author   TEXT NOT NULL,
                content  TEXT NOT NULL,
                password TEXT NOT NULL,
                views    INTEGER DEFAULT 0,
                created  TEXT NOT NULL,
                is_draft INTEGER DEFAULT 0
            )
        ''')
        _ensure_posts_columns(db)
        db.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id  INTEGER NOT NULL,
                author   TEXT NOT NULL,
                content  TEXT NOT NULL,
                password TEXT NOT NULL,
                created  TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')
        db.commit()
    import shorts_subscription as _ss

    with sqlite3.connect(DB_PATH) as db:
        _ss.ensure_tables(db)


@app.context_processor
def inject_site_settings():
    return {
        "site_name": SITE_NAME,
        "site_contact_email": SITE_CONTACT_EMAIL,
        "adsense_client": ADSENSE_CLIENT,
        "agent_office_session": _office_session_ok(),
    }


# ── 홈(랜딩) / 블로그 목록 / ETF 허브 ─────────────────────────────────────────
_POST_PUBLISHED_SQL = "COALESCE(is_draft, 0) = 0"
_POST_PUBLISHED_WHERE = "COALESCE(p.is_draft, 0) = 0"

_POST_LIST_SQL = f"""
    SELECT p.*,
           (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
    FROM posts p
    WHERE {_POST_PUBLISHED_WHERE}
"""


def _blog_list_context():
    """글 목록·검색·페이지네이션에 필요한 값만 계산."""
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    per_page = BLOG_PER_PAGE
    db = get_db()
    if q:
        total = db.execute(
            f"SELECT COUNT(*) FROM posts p WHERE {_POST_PUBLISHED_WHERE} AND (p.title LIKE ? OR p.author LIKE ?)",
            (f"%{q}%", f"%{q}%"),
        ).fetchone()[0]
        rows = db.execute(
            _POST_LIST_SQL
            + " AND (p.title LIKE ? OR p.author LIKE ?) ORDER BY p.id DESC LIMIT ? OFFSET ?",
            (f"%{q}%", f"%{q}%", per_page, (page - 1) * per_page),
        ).fetchall()
    else:
        total = db.execute(
            f"SELECT COUNT(*) FROM posts p WHERE {_POST_PUBLISHED_WHERE}"
        ).fetchone()[0]
        rows = db.execute(
            _POST_LIST_SQL + " ORDER BY p.id DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page),
        ).fetchall()
    total_pages = (total + per_page - 1) // per_page
    list_base = total - (page - 1) * per_page
    posts = []
    for i, row in enumerate(rows):
        item = dict(row)
        item["list_no"] = list_base - i
        item["display_author"] = _post_display_author(
            item, is_question=_is_home_question_post(item)
        )
        posts.append(item)
    return {
        "posts": posts,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "total": total,
        "q": q,
    }


@app.route("/")
def index():
    """메인 랜딩. 예전 북마크용 `/?page=`·`?q=` 는 블로그로 넘깁니다."""
    if request.args.get("page") is not None or request.args.get("q", "").strip():
        safe = {}
        p = request.args.get("page", type=int)
        if p is not None and p > 0:
            safe["page"] = p
        qv = request.args.get("q", "").strip()
        if qv:
            safe["q"] = qv
        return redirect(url_for("blog", **safe))
    db = get_db()
    total = db.execute(
        f"SELECT COUNT(*) FROM posts p WHERE {_POST_PUBLISHED_WHERE}"
    ).fetchone()[0]
    return render_template(
        "home.html",
        total=total,
        qa_topics=HOME_QA_TOPICS,
        gemma24_author=home_qa_reply.GEMMA24_AUTHOR,
    )


@app.route("/shorts")
@app.route("/숏폼공장")
def shorts_page():
    import shorts_locale as sl
    import shorts_subscription as ss

    site_base = os.getenv("SHORTS_SITE_URL", "https://coupax.co.kr").rstrip("/")
    page_lang = sl.detect_locale(request)
    locale_meta = sl.meta_for(page_lang)
    detected_country = sl._country_from_request(request)
    token = request.cookies.get(ss.COOKIE_NAME, "")
    db = get_db()
    ss.ensure_tables(db)
    sub = ss.get_subscriber_by_token(db, token)
    if sub:
        sub = ss._sync_daily_usage(db, sub)
    sub = ss.subscriber_status(sub)
    if sub and sub.get("active"):
        sub = dict(sub)
        sub["plan_name"] = ss.plan_display_name(sub["plan"], page_lang)
    static_dir = os.path.join(app.root_path, "static")
    shorts_asset_ver = max(
        int(os.path.getmtime(os.path.join(static_dir, name)))
        for name in ("shorts.js", "shorts_home.css")
        if os.path.isfile(os.path.join(static_dir, name))
    )
    return render_template(
        "shorts.html",
        plans=ss.list_plans_public(),
        stripe_enabled=ss.stripe_enabled() or ss.DEV_SUBSCRIBE,
        subscription=sub,
        now_year=datetime.now().year,
        canonical_shorts_url=f"{site_base}/shorts",
        page_lang=page_lang,
        locale_meta=locale_meta,
        detected_country=detected_country,
        shorts_asset_ver=shorts_asset_ver,
    )


@app.route("/api/v1/shorts/locale", methods=["GET"])
def shorts_locale_api():
    import shorts_locale as sl

    country = sl._country_from_request(request)
    accept = sl._lang_from_accept_language(request)
    return jsonify(
        {
            "locale": sl.detect_locale(request),
            "accept_language": accept,
            "country": country,
            "ip": sl._client_ip(request),
            "geo_enabled": sl._GEO_ENABLED,
            "supported": sorted(sl.SUPPORTED),
        }
    )


@app.route("/shorts/success")
@app.route("/숏폼공장/success")
def shorts_success():
    import shorts_subscription as ss

    token = request.args.get("token", "")
    session_id = request.args.get("session_id", "")
    if session_id:
        token = ss.fulfill_checkout_session(session_id) or token
    resp = redirect(url_for("shorts_page", _anchor="studio"))
    if token:
        resp.set_cookie(
            ss.COOKIE_NAME,
            token,
            max_age=60 * 60 * 24 * 400,
            httponly=True,
            secure=app.config.get("SESSION_COOKIE_SECURE", True),
            samesite="Lax",
        )
    return resp


@app.route("/api/v1/shorts/subscription", methods=["GET"])
def shorts_subscription_status():
    import shorts_subscription as ss

    token = request.cookies.get(ss.COOKIE_NAME, "")
    db = get_db()
    ss.ensure_tables(db)
    row = ss.get_subscriber_by_token(db, token)
    if row:
        row = ss._sync_daily_usage(db, row)
    st = ss.subscriber_status(row)
    return jsonify({"subscription": st})


@app.route("/api/v1/shorts/checkout", methods=["POST"])
def shorts_checkout():
    import shorts_subscription as ss

    data = request.get_json(force=True, silent=True) or {}
    plan_id = (data.get("plan") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    plan = ss.PLANS.get(plan_id)
    if plan and plan.get("free"):
        token = request.cookies.get(ss.COOKIE_NAME, "")
        db = get_db()
        ss.ensure_tables(db)
        row = ss.get_subscriber_by_token(db, token) if token else None
        if row:
            row = ss._sync_daily_usage(db, row)
            st = ss.subscriber_status(row)
            if st and st.get("active"):
                return jsonify(
                    {"checkout_url": url_for("shorts_page", _external=True, _anchor="studio")}
                )
    try:
        url = ss.create_checkout_session(
            plan_id,
            email,
            success_url=url_for("shorts_success", _external=True),
            cancel_url=url_for("shorts_page", _external=True, _anchor="pricing"),
        )
        return jsonify({"checkout_url": url})
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400


@app.route("/api/v1/shorts/webhook/stripe", methods=["POST"])
def shorts_stripe_webhook():
    import shorts_subscription as ss

    try:
        ss.handle_stripe_webhook(request.get_data(), request.headers.get("Stripe-Signature", ""))
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.exception("stripe webhook")
        return jsonify({"detail": str(e)}), 400


@app.route("/api/v1/shorts/generate-pipeline", methods=["POST"])
def shorts_generate_pipeline():
    import shorts_pipeline as sp
    import shorts_subscription as ss

    security_utils.validate_same_origin()
    if request.content_length and request.content_length > security_utils.SHORTS_MAX_BODY_BYTES:
        return jsonify({"detail": "Request body too large."}), 413

    token = request.cookies.get(ss.COOKIE_NAME, "")
    db = get_db()
    ss.ensure_tables(db)
    ok, msg, row = ss.can_generate(db, token)
    if not ok:
        code = 402 if row else 403
        return jsonify({"detail": msg}), code

    data = request.get_json(force=True, silent=True) or {}
    creds = data.get("credentials") or {}
    if not isinstance(creds, dict):
        return jsonify({"detail": "Invalid credentials."}), 400
    api_key = security_utils.clamp_text(creds.get("api_key"), 120)
    if not api_key:
        return jsonify({"detail": "Google AI API key is required.", "code": "api_key_required"}), 400
    if not security_utils.validate_google_api_key_shape(api_key):
        return jsonify({"detail": "Invalid Google AI API key format."}), 400

    if not security_utils.check_shorts_rate_limit():
        return jsonify(
            {"detail": f"Please wait {security_utils.SHORTS_MIN_INTERVAL_SEC}s between generations."}
        ), 429

    try:
        result = sp.run_pipeline(data, api_key=api_key)
        ss.record_usage(db, int(row["id"]))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception:
        app.logger.exception("shorts_generate_pipeline failed")
        return jsonify({"detail": "Pipeline error. Please try again."}), 500


@app.route("/shorts/admin", methods=["GET", "POST"])
def shorts_admin_page():
    import shorts_settings as sset

    if not _shorts_admin_configured():
        return render_template("shorts_admin.html", access_configured=False), 503

    if request.method == "POST" and not _shorts_admin_ok():
        if not security_utils.check_office_login_allowed():
            flash("로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.", "error")
        else:
            pw = request.form.get("password", "")
            if SHORTS_ADMIN_PASSWORD and secrets.compare_digest(pw, SHORTS_ADMIN_PASSWORD):
                security_utils.clear_office_login_failures()
                session["shorts_admin_auth"] = True
                session.permanent = True
                return redirect(url_for("shorts_admin_page"))
            security_utils.record_office_login_failure()
            flash("비밀번호가 올바르지 않습니다.", "error")

    if not _shorts_admin_ok():
        return render_template("shorts_admin.html", access_configured=True, logged_in=False)

    return render_template(
        "shorts_admin.html",
        access_configured=True,
        logged_in=True,
        key_info=sset.key_info(),
    )


@app.route("/shorts/admin/logout", methods=["POST"])
def shorts_admin_logout():
    session.pop("shorts_admin_auth", None)
    return redirect(url_for("shorts_admin_page"))


@app.route("/api/v1/shorts/admin/gemini-key", methods=["GET", "POST"])
def shorts_admin_gemini_key():
    import shorts_settings as sset

    if not _shorts_admin_ok():
        return jsonify({"detail": "Admin login required."}), 403

    if request.method == "GET":
        return jsonify({"key": sset.key_info()})

    security_utils.validate_same_origin()
    data = request.get_json(force=True, silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return jsonify({"detail": "API key is required."}), 400
    if not security_utils.validate_google_api_key_shape(api_key):
        return jsonify({"detail": "Invalid Google AI API key format."}), 400

    sset.save_google_api_key(api_key)
    return jsonify({"ok": True, "key": sset.key_info()})


def _request_wants_json() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _home_ask_error(message: str, status: int = 400):
    if _request_wants_json():
        return jsonify({"ok": False, "error": message}), status
    flash(message, "error")
    return redirect(url_for("index", _anchor="home-ask"))


@app.route("/ask", methods=["POST"])
def home_ask():
    """홈 질문창 → 새 블로그 글 + 젬마24 댓글 답변(대화형)."""
    db = get_db()
    author = request.form.get("author", "").strip()
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "")
    topic = request.form.get("topic", "").strip()

    if topic and topic not in HOME_QA_TOPICS:
        topic = ""

    if not all([author, content, password]):
        return _home_ask_error("닉네임, 질문 내용, 비밀번호를 모두 입력해 주세요.")

    if not security_utils.check_comment_rate_limit():
        return _home_ask_error(
            f"질문 등록은 {security_utils.COMMENT_MIN_INTERVAL_SEC}초 간격으로 가능합니다. 잠시 후 다시 시도해 주세요.",
            429,
        )

    try:
        post_id, post_title, created = _create_question_post(
            db, author, content, password, topic
        )
        user_comment_id = _insert_question_comment(
            db, post_id, author, content, password, topic
        )
        answer = home_qa_reply.attach_reply(
            db, post_id, user_comment_id, author, content, post_title, topic
        )
    except Exception:
        app.logger.exception("home_ask failed")
        return _home_ask_error(
            "질문·답변 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            500,
        )

    question_payload = {
        "post_id": post_id,
        "title": post_title,
        "author": author,
        "content": content,
        "created": created,
        "topic": topic,
        "url": url_for("view", post_id=post_id, _anchor="comments"),
    }

    if _request_wants_json():
        thread = _home_chat_thread_payload(db, post_id)
        return jsonify(
            {
                "ok": True,
                "question": question_payload,
                "answer": answer,
                "thread": thread,
            }
        )

    flash("질문 글이 등록되었고 젬마24 답변이 댓글로 달렸습니다.", "success")
    return redirect(url_for("view", post_id=post_id, _anchor="comments"))


def _extract_topic_from_question_post(post) -> str:
    title = (post.get("title") if isinstance(post, dict) else post["title"]) or ""
    m = re.search(r"\[([^\]]+)\]", str(title))
    if m and m.group(1) in HOME_QA_TOPICS:
        return m.group(1)
    return "기타"


def _home_chat_message_row(comment) -> dict:
    author = comment["author"]
    is_gemma = author == home_qa_reply.GEMMA24_AUTHOR
    return {
        "id": int(comment["id"]),
        "role": "assistant" if is_gemma else "user",
        "author": author,
        "content": comment["content"],
        "created": comment["created"],
    }


def _home_chat_thread_payload(db, post_id: int) -> dict | None:
    post = db.execute(
        "SELECT id, title, author, content, created FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()
    if not post or not _is_home_question_post(post):
        return None
    comments = db.execute(
        "SELECT id, author, content, created FROM comments WHERE post_id = ? ORDER BY id ASC",
        (post_id,),
    ).fetchall()
    return {
        "post_id": int(post["id"]),
        "title": post["title"],
        "author": _post_display_author(dict(post), is_question=True),
        "created": post["created"],
        "url": url_for("view", post_id=post_id, _anchor="comments"),
        "messages": [_home_chat_message_row(c) for c in comments],
    }


@app.route("/api/home-chat/<int:post_id>", methods=["GET"])
def home_chat_thread(post_id: int):
    db = get_db()
    payload = _home_chat_thread_payload(db, post_id)
    if not payload:
        return jsonify({"ok": False, "error": "질문 글을 찾을 수 없습니다."}), 404
    return jsonify({"ok": True, **payload})


@app.route("/api/home-chat/<int:post_id>/pulse", methods=["GET"])
def home_chat_pulse(post_id: int):
    db = get_db()
    post = db.execute(
        "SELECT id, title, content FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    if not post or not _is_home_question_post(post):
        return jsonify({"ok": False, "error": "질문 글을 찾을 수 없습니다."}), 404
    row = db.execute(
        "SELECT COUNT(*) AS c, MAX(id) AS mid FROM comments WHERE post_id = ?",
        (post_id,),
    ).fetchone()
    count = int(row["c"] or 0) if row else 0
    last_id = int(row["mid"] or 0) if row and row["mid"] is not None else 0
    return jsonify({"ok": True, "sig": f"{count}|{last_id}", "message_count": count})


@app.route("/api/home-chat/<int:post_id>/message", methods=["POST"])
def home_chat_message(post_id: int):
    db = get_db()
    post = db.execute(
        "SELECT id, title, content FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    if not post or not _is_home_question_post(post):
        return jsonify({"ok": False, "error": "질문 글을 찾을 수 없습니다."}), 404

    author = request.form.get("author", "").strip()
    content = request.form.get("content", "").strip()
    password = request.form.get("password", "")
    if not all([author, content, password]):
        return jsonify({"ok": False, "error": "닉네임, 내용, 비밀번호를 입력해 주세요."}), 400

    if not security_utils.check_comment_rate_limit():
        return jsonify(
            {
                "ok": False,
                "error": f"메시지는 {security_utils.COMMENT_MIN_INTERVAL_SEC}초 간격으로 보낼 수 있습니다.",
            }
        ), 429

    topic = _extract_topic_from_question_post(post)
    user_comment_id = _insert_question_comment(
        db, post_id, author, content, password, topic
    )
    home_qa_reply.attach_reply(
        db,
        post_id,
        user_comment_id,
        author,
        content,
        post["title"],
        topic,
    )

    payload = _home_chat_thread_payload(db, post_id)
    return jsonify({"ok": True, **payload})


@app.route("/blog")
def blog():
    ctx = _blog_list_context()
    return render_template("blog.html", **ctx)


# ── 글쓰기 ────────────────────────────────────────────────────────────────────
@app.route('/write', methods=['GET', 'POST'])
def write():
    if not _blog_write_allowed():
        flash(
            "글 작성은 운영자만 가능합니다. 에이전트 사무실 입장 후 다시 시도해 주세요.",
            "error",
        )
        return redirect(url_for("agent_office_login", next=url_for("write")))
    if request.method == 'POST':
        title   = request.form['title'].strip()
        author  = request.form['author'].strip()
        content = request.form['content'].strip()
        password = request.form['password']

        if not all([title, content, password]):
            flash('제목, 내용, 비밀번호를 입력해주세요.', 'error')
            return render_template('write.html')

        db = get_db()
        cur = db.execute(
            "INSERT INTO posts (title, author, content, password, created) VALUES (?,?,?,?,?)",
            (
                title,
                author or SITE_NAME,
                content,
                security_utils.hash_password(password),
                datetime.now().strftime('%Y-%m-%d %H:%M'),
            ),
        )
        new_id = cur.lastrowid
        pen = blog_pen_name(new_id)
        db.execute("UPDATE posts SET author=? WHERE id=?", (pen, new_id))
        db.commit()
        flash('게시글이 등록되었습니다.', 'success')
        return redirect(url_for('blog'))

    return render_template('write.html')


# ── 상세보기 ──────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>')
def view(post_id):
    db = get_db()
    db.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
    db.commit()

    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        flash('존재하지 않는 게시글입니다.', 'error')
        return redirect(url_for('blog'))

    post = dict(post)
    post["is_question_thread"] = _is_home_question_post(post)
    post["display_author"] = _post_display_author(
        post, is_question=post["is_question_thread"]
    )
    if post["is_question_thread"]:
        body = (post.get("content") or "").strip()
        if body.startswith(HOME_QUESTION_MARKER):
            post["content"] = body[len(HOME_QUESTION_MARKER) :].lstrip()

    comments = db.execute(
        "SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC", (post_id,)
    ).fetchall()
    related_posts = db.execute(
        f"SELECT id, title, created FROM posts WHERE id != ? AND {_POST_PUBLISHED_SQL} ORDER BY id DESC LIMIT 4",
        (post_id,),
    ).fetchall()
    return render_template(
        'view.html',
        post=post,
        comments=comments,
        related_posts=related_posts,
        gemma24_author=home_qa_reply.GEMMA24_AUTHOR,
    )


# ── 수정 ──────────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return redirect(url_for('blog'))

    if request.method == 'POST':
        password = request.form['password']
        if not _verify_post_password(db, post_id, password, post['password']):
            flash('비밀번호가 틀렸습니다.', 'error')
            return render_template('edit.html', post=post)

        title   = request.form['title'].strip()
        content = request.form['content'].strip()
        if not all([title, content]):
            flash('제목과 내용을 입력해주세요.', 'error')
            return render_template('edit.html', post=post)

        db.execute(
            "UPDATE posts SET title=?, content=? WHERE id=?",
            (title, content, post_id)
        )
        db.commit()
        flash('수정되었습니다.', 'success')
        return redirect(url_for('view', post_id=post_id))

    return render_template('edit.html', post=post)


# ── 삭제 ──────────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return redirect(url_for('blog'))

    password = request.form.get('password', '')
    if not _verify_post_password(db, post_id, password, post['password']):
        flash('비밀번호가 틀렸습니다.', 'error')
        return redirect(url_for('view', post_id=post_id))

    db.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash('게시글이 삭제되었습니다.', 'success')
    return redirect(url_for('blog'))


# ── 댓글 등록 ─────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    db = get_db()
    post = db.execute(
        "SELECT id, title, content FROM posts WHERE id = ?", (post_id,)
    ).fetchone()
    if not post:
        if _request_wants_json():
            return jsonify({"ok": False, "error": "존재하지 않는 게시글입니다."}), 404
        flash('존재하지 않는 게시글입니다.', 'error')
        return redirect(url_for('blog'))

    author = request.form.get('author', '').strip()
    content = request.form.get('content', '').strip()
    password = request.form.get('password', '')

    if not all([author, content, password]):
        msg = '댓글 항목을 모두 입력해주세요.'
        if _request_wants_json():
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, 'error')
        return redirect(url_for('view', post_id=post_id, _anchor='comments'))

    if not security_utils.check_comment_rate_limit():
        msg = (
            f"질문 등록은 {security_utils.COMMENT_MIN_INTERVAL_SEC}초 간격으로 가능합니다. "
            "잠시 후 다시 시도해 주세요."
        )
        if _request_wants_json():
            return jsonify({"ok": False, "error": msg}), 429
        flash(msg, "error")
        return redirect(url_for('view', post_id=post_id, _anchor='comments'))

    is_q = _is_home_question_post(post)
    topic = _extract_topic_from_question_post(dict(post)) if is_q else ""
    user_comment_id = _insert_question_comment(
        db, post_id, author, content, password, topic
    )
    if is_q:
        try:
            home_qa_reply.attach_reply(
                db,
                post_id,
                user_comment_id,
                author,
                content,
                post["title"],
                topic,
            )
        except Exception:
            app.logger.exception("gemma reply failed post_id=%s", post_id)
            if _request_wants_json():
                return jsonify(
                    {
                        "ok": False,
                        "error": "질문은 등록됐지만 답변 생성에 실패했습니다. 잠시 후 새로고침해 주세요.",
                    }
                ), 500
            flash(
                "질문은 등록됐지만 젬마24 답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
                "error",
            )
            return redirect(url_for("view", post_id=post_id, _anchor="comments"))

    if is_q and _request_wants_json():
        payload = _home_chat_thread_payload(db, post_id)
        if payload:
            return jsonify({"ok": True, **payload})
        return jsonify({"ok": False, "error": "대화를 불러오지 못했습니다."}), 500

    flash('댓글이 등록되었습니다.', 'success')
    return redirect(url_for('view', post_id=post_id, _anchor='comments'))


# ── 댓글 삭제 ─────────────────────────────────────────────────────────────────
@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    db = get_db()
    comment = db.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
    if not comment:
        return redirect(url_for('blog'))

    post_id = comment['post_id']
    password = request.form.get('password', '')
    if not _verify_comment_password(db, comment_id, password, comment['password']):
        flash('비밀번호가 틀렸습니다.', 'error')
    else:
        db.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        db.commit()

    return redirect(url_for('view', post_id=post_id))


@app.route('/products/etf-data')
def data_product_etf():
    """ETF 정보 수집·재가공·제공(라이선스) 모델 소개(베타)."""
    blocked = _etf_public_blocked()
    if blocked:
        return blocked
    return render_template('data_product_etf.html')


def _monthly_sheet_csv(sheet: dict) -> str:
    """월배당 시트 전체를 CSV 문자열로."""
    year = sheet.get("year", 2026)
    rows = sheet.get("rows") if isinstance(sheet.get("rows"), list) else []
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf)
    month_headers = [f"{m}월" for m in range(1, 13)]
    writer.writerow(
        [
            "no",
            "brand",
            "name",
            "code",
            "cycle",
            "listed",
            "market_cap",
            "expense_ratio",
            *month_headers,
            "dividend_total",
            "current_price",
            f"{year}_누적배당수익률_pct",
            f"{year}_YTD주가수익률_pct",
            f"{year}_YTD총수익률_pct",
        ]
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        months = row.get("months") if isinstance(row.get("months"), list) else []
        month_vals = []
        for i in range(12):
            if i < len(months) and months[i] is not None:
                month_vals.append(months[i])
            else:
                month_vals.append("")
        writer.writerow(
            [
                row.get("no", ""),
                row.get("brand", ""),
                row.get("name", ""),
                row.get("code", ""),
                row.get("cycle", ""),
                row.get("listed", ""),
                row.get("market_cap", ""),
                row.get("expense_ratio", ""),
                *month_vals,
                row.get("dividend_total", ""),
                row.get("current_price", ""),
                row.get("dividend_yield_pct", ""),
                row.get("price_return_pct", ""),
                row.get("total_return_pct", ""),
            ]
        )
    return buf.getvalue()


@app.route("/etf/monthly-dividends.csv")
def etf_monthly_csv():
    blocked = _etf_public_blocked()
    if blocked:
        return blocked
    sheet = load_monthly_dividend_sheet()
    year = sheet.get("year", 2026)
    body = _monthly_sheet_csv(sheet)
    return Response(
        body,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=monthly_dividend_etfs_{year}.csv"
        },
    )


@app.route("/etf/monthly-sheet")
def etf_monthly_sheet():
    """월배당 ETF 트래킹 시트 전용 페이지(필터·차트·CSV·브랜드 요약)."""
    blocked = _etf_public_blocked()
    if blocked:
        return blocked
    dividend_sheet = load_monthly_dividend_sheet()
    rows = dividend_sheet.get("rows") if isinstance(dividend_sheet.get("rows"), list) else []
    return render_template(
        "etf_monthly_sheet.html",
        dividend_sheet=dividend_sheet,
        brand_summaries=build_brand_summaries(rows),
        row_count=len(rows),
    )


@app.route('/etf')
def etf_hub():
    blocked = _etf_public_blocked()
    if blocked:
        return blocked
    db = get_db()
    etf_posts = fetch_etf_related_posts(db)
    dividend_sheet = load_monthly_dividend_sheet()
    rows = dividend_sheet.get("rows") if isinstance(dividend_sheet.get("rows"), list) else []
    return render_template(
        'etf_hub.html',
        etf_posts=etf_posts,
        themed_posts=group_etf_posts_by_theme(etf_posts),
        monthly_posts=fetch_monthly_dividend_posts(db),
        sheet_row_count=len(rows),
        sheet_year=dividend_sheet.get("year", 2026),
        etf_count=len(etf_posts),
    )


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


CAR_INSPECTION_PRIVATE_DIR = os.path.join(app.root_path, "private_assets", "car-inspection")


@app.route("/private/car-inspection")
@require_office_access
def private_car_inspection():
    """토스 미니앱 자동차검사소 — 검수·내부 참고용 비공개 페이지."""
    return render_template("private_car_inspection.html")


@app.route("/private/car-inspection/logo.png")
@require_office_access
def private_car_inspection_logo():
    return send_from_directory(CAR_INSPECTION_PRIVATE_DIR, "logo.png", mimetype="image/png")


@app.route("/agents/office/login", methods=["GET", "POST"])
def agent_office_login():
    """사무실 입장 — 대표님·젬마24 전용 (비공개)."""
    if not _office_access_configured():
        return render_template(
            "agent_office_login.html",
            access_configured=False,
            next_url=url_for("agent_office"),
        )
    if _office_session_ok():
        return redirect(request.args.get("next") or url_for("agent_office"))

    if request.method == "POST":
        if not security_utils.check_office_login_allowed():
            flash(
                "로그인 시도가 너무 많습니다. 15분 후 다시 시도해 주세요.",
                "error",
            )
            return render_template(
                "agent_office_login.html",
                access_configured=True,
                next_url=request.args.get("next") or url_for("agent_office"),
            )
        pw = request.form.get("password", "")
        if AGENT_OFFICE_ACCESS_PASSWORD and secrets.compare_digest(
            pw, AGENT_OFFICE_ACCESS_PASSWORD
        ):
            security_utils.clear_office_login_failures()
            session["agent_office_auth"] = True
            session.permanent = True
            nxt = request.form.get("next") or request.args.get("next") or url_for("agent_office")
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("agent_office")
            return redirect(nxt)
        security_utils.record_office_login_failure()
        flash("입장 비밀번호가 올바르지 않습니다.", "error")

    return render_template(
        "agent_office_login.html",
        access_configured=True,
        next_url=request.args.get("next") or url_for("agent_office"),
    )


@app.route("/agents/office/logout", methods=["POST"])
def agent_office_logout():
    session.pop("agent_office_auth", None)
    flash("사무실에서 나왔습니다.", "success")
    return redirect(url_for("index"))


@app.route("/agents/office")
@require_office_access
def agent_office():
    """젬마24 에이전트 사무실 — 대표님·젬마24 전용 비공개."""
    ctx = _agent_office_context()
    unit = (request.args.get("unit") or "").strip()
    if unit == "saju-learn":
        ctx["office_tab_active"] = "saju-learn"
    elif unit == "kiwoom-chasu":
        ctx["office_tab_active"] = "kiwoom-chasu"
    elif unit == "stock-watch":
        ctx["office_tab_active"] = "stock-watch"
    elif unit == "homepage-design":
        ctx["office_tab_active"] = "homepage-design"
    elif unit == "workisus-chasu":
        ctx["office_tab_active"] = "workisus-chasu"
    elif unit == "gwansang-learn":
        ctx["office_tab_active"] = "gwansang-learn"
    elif unit == "chief-dev":
        ctx["office_tab_active"] = "chief-dev"
    else:
        ctx["office_tab_active"] = "finance"
    return render_template("agent_office.html", **ctx)


@app.route("/agents/office/kiwoom-chasu")
@require_office_access
def kiwoom_chasu():
    """차수거래 — 메인 사무실 탭으로 통합."""
    return redirect(url_for("agent_office", unit="kiwoom-chasu"))


@app.route("/agents/office/knowledge-network")
@require_office_access
def knowledge_network():
    """젬마24 지식 네트워크 LIVE (force-graph)."""
    return render_template("knowledge_network.html")


@app.route("/api/agents/office/knowledge-graph.json")
@require_office_access
def agent_office_knowledge_graph_json():
    """지식망 nodes/links (force-graph)."""
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parent / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import knowledge_graph_builder

    max_nodes = min(5000, max(100, int(request.args.get("max_nodes", 3000))))
    max_links = min(30000, max(200, int(request.args.get("max_links", 15000))))
    include_swiki = request.args.get("swiki", "1").strip() not in ("0", "false", "no")
    payload = knowledge_graph_builder.build_knowledge_graph(
        max_nodes=max_nodes,
        max_links=max_links,
        include_swiki=include_swiki,
    )
    return jsonify({"ok": True, **payload})


@app.route("/api/agents/office/pulse.json")
@require_office_access
def agent_office_pulse():
    """실시간 폴링용 경량 상태 (변경 여부만 확인)."""
    feed = load_agent_office_feed()
    messages = feed.get("messages") if isinstance(feed.get("messages"), list) else []
    last_msg_id = 0
    for m in messages:
        if isinstance(m, dict) and isinstance(m.get("id"), int):
            last_msg_id = max(last_msg_id, m["id"])

    tasks = load_agent_office_tasks()
    last_task_id = 0
    task_parts: list[str] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if isinstance(t.get("id"), int):
            last_task_id = max(last_task_id, t["id"])
        task_parts.append(
            f"{t.get('id')}:{t.get('status')}:{t.get('finished_at') or ''}:"
            f"{t.get('wiki_id') or ''}:{t.get('blog_draft_id') or ''}"
        )
    task_sig = "|".join(task_parts[-15:])

    import agent_registry

    reg_agents = agent_registry.merge_agents_for_office(
        feed, agent_registry.load_registry()
    )
    saju_msgs = _filter_office_messages(
        messages, reg_agents, agent_registry.DIVISION_SAJU
    )
    last_saju_msg_id = 0
    for m in saju_msgs:
        if isinstance(m, dict) and isinstance(m.get("id"), int):
            last_saju_msg_id = max(last_saju_msg_id, m["id"])

    kiwoom_msgs = _filter_office_messages(
        messages, reg_agents, agent_registry.DIVISION_KIWOM
    )
    last_kiwoom_msg_id = 0
    for m in kiwoom_msgs:
        if isinstance(m, dict) and isinstance(m.get("id"), int):
            last_kiwoom_msg_id = max(last_kiwoom_msg_id, m["id"])

    stock_msgs = _filter_office_messages(
        messages, reg_agents, agent_registry.DIVISION_STOCK
    )
    last_stock_msg_id = 0
    for m in stock_msgs:
        if isinstance(m, dict) and isinstance(m.get("id"), int):
            last_stock_msg_id = max(last_stock_msg_id, m["id"])

    kn = load_gemma_knowledge_summary()
    return Response(
        json.dumps(
            {
                "updated_at": feed.get("updated_at") or "",
                "message_count": len(messages),
                "last_message_id": last_msg_id,
                "saju_message_count": len(saju_msgs),
                "last_saju_message_id": last_saju_msg_id,
                "saju_feed_sig": (
                    f"{feed.get('updated_at')}|{len(saju_msgs)}|{last_saju_msg_id}"
                ),
                "kiwoom_message_count": len(kiwoom_msgs),
                "last_kiwoom_message_id": last_kiwoom_msg_id,
                "kiwoom_feed_sig": (
                    f"{feed.get('updated_at')}|{len(kiwoom_msgs)}|{last_kiwoom_msg_id}"
                ),
                "stock_message_count": len(stock_msgs),
                "last_stock_message_id": last_stock_msg_id,
                "stock_feed_sig": (
                    f"{feed.get('updated_at')}|{len(stock_msgs)}|{last_stock_msg_id}"
                ),
                "feed_sig": f"{feed.get('updated_at')}|{len(messages)}|{last_msg_id}",
                "task_count": len(tasks),
                "last_task_id": last_task_id,
                "tasks_sig": f"{len(tasks)}|{last_task_id}|{task_sig}",
                "wiki_count": kn.get("wiki_count", 0),
                "knowledge_sig": f"{kn.get('updated_at')}|{kn.get('wiki_count')}",
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office.json")
@require_office_access
def agent_office_json():
    """사무실 피드 + 레지스트리 JSON (자동 새로고침용)."""
    ctx = _agent_office_context()
    payload = {
        "office_name": ctx["office"].get("office_name"),
        "updated_at": ctx["office"].get("updated_at"),
        "messages": ctx["finance_messages"],
        "finance_messages": ctx["finance_messages"],
        "saju_messages": ctx["saju_messages"],
        "kiwoom_messages": ctx["kiwoom_messages"],
        "stock_messages": ctx["stock_messages"],
        "design_messages": ctx["design_messages"],
        "workisus_messages": ctx["workisus_messages"],
        "gwansang_messages": ctx["gwansang_messages"],
        "agents": ctx["agents"],
        "office_always_on": ctx["office_always_on"],
        "global_always_on": ctx["global_always_on"],
    }
    return Response(
        json.dumps(payload, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/registry.json")
@require_office_access
def agent_registry_json():
    import agent_registry

    feed = load_agent_office_feed()
    reg = agent_registry.load_registry()
    return Response(
        json.dumps(
            {
                "office_always_on": bool(reg.get("office_always_on") or reg.get("global_always_on")),
                "global_always_on": reg.get("global_always_on"),
                "agents": agent_registry.merge_agents_for_office(feed, reg),
                "control_enabled": bool(AGENT_OFFICE_CONTROL_TOKEN),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/tasks.json")
@require_office_access
def agent_office_tasks_json():
    finance_queue = {"mode": "reserved", "active": 0, "target": 3, "label": "예약"}
    saju_queue = {"mode": "reserved", "active": 0, "target": 3, "label": "명리 예약"}
    kiwoom_queue = {"mode": "reserved", "active": 0, "target": 3, "label": "차수 예약"}
    try:
        import agent_office_council
        import agent_office_kiwoom_reserved_tasks as kiwoom_reserved

        finance_queue = agent_office_council.queue_status(agent_registry.DIVISION_FINANCE)
        saju_queue = agent_office_council.queue_status(agent_registry.DIVISION_SAJU)
        kiwoom_queue = {
            "mode": "reserved",
            "active": kiwoom_reserved.count_reserved_active(),
            "target": max(1, int(os.getenv("AGENT_OFFICE_KIWOM_RESERVED_QUEUE", "3") or "3")),
            "label": "차수 예약",
        }
    except Exception:
        pass
    return Response(
        json.dumps(
            {
                "tasks": load_agent_office_tasks(),
                "finance_reserved_active": finance_queue["active"],
                "finance_reserved_queue_target": finance_queue["target"],
                "finance_reserved_queue_label": finance_queue["label"],
                "finance_reserved_queue_mode": finance_queue["mode"],
                "saju_reserved_active": saju_queue["active"],
                "saju_reserved_queue_target": saju_queue["target"],
                "saju_reserved_queue_label": saju_queue["label"],
                "saju_reserved_queue_mode": saju_queue["mode"],
                "saju_council_verified": saju_queue.get("verified", 0),
                "saju_council_total": saju_queue.get("total", 0),
                "kiwoom_reserved_active": kiwoom_queue["active"],
                "kiwoom_reserved_queue_target": kiwoom_queue["target"],
                "kiwoom_reserved_queue_label": kiwoom_queue["label"],
                "kiwoom_reserved_queue_mode": kiwoom_queue["mode"],
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/cursor-inbox.json")
@require_office_access
def agent_office_cursor_inbox_json():
    """Cursor(젬마24 채팅) 연동용 인박스."""
    import agent_office_cursor_bridge

    data = agent_office_cursor_bridge.load_inbox()
    pending = agent_office_cursor_bridge.list_pending()
    return Response(
        json.dumps(
            {
                "inbox": data,
                "pending_count": len(pending),
                "pending": pending,
                "markdown_path": "CURSOR_OFFICE_INBOX.md",
                "sync_cmd": "python board/scripts/sync_cursor_office_inbox.py pull",
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/saju-learn.json")
@require_office_access
def agent_office_saju_learn_json():
    import agent_office_saju_learn

    stats = agent_office_saju_learn.stats()
    try:
        import agent_office_saju_card_council

        if agent_office_saju_card_council.use_card_council():
            stats["council"] = agent_office_saju_card_council.council_stats()
    except Exception:
        pass
    try:
        import saju_reading_engine

        stats["reading"] = {
            "pass_cards_total": saju_reading_engine.pass_cards_count(),
            "min_pass_match": saju_reading_engine.min_pass_cards(),
            "compose_enabled": os.getenv("SAJU_READING_API_ENABLED", "0").strip()
            in ("1", "true", "yes"),
        }
    except Exception:
        pass
    return Response(
        json.dumps(
            {
                "stats": stats,
                "cards": agent_office_saju_learn.list_cards(limit=100),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/saju-learn/ingest", methods=["POST"])
@require_office_access
def agent_office_saju_learn_ingest():
    import agent_office_saju_learn

    payload = request.get_json(silent=True) or request.form
    body = (payload.get("body") or payload.get("text") or "").strip()
    title = (payload.get("title") or "").strip()
    if not body:
        return Response(
            json.dumps({"ok": False, "error": "풀이 본문을 입력해 주세요."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        card = agent_office_saju_learn.add_card(body=body, title=title, source="office_paste")
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "card": card, "stats": agent_office_saju_learn.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/saju-learn/<int:card_id>/confirm", methods=["POST"])
@require_office_access
def agent_office_saju_learn_confirm(card_id: int):
    import agent_office_saju_learn

    card = agent_office_saju_learn.confirm_card(card_id)
    if not card:
        return Response(
            json.dumps({"ok": False, "error": "카드를 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps(
            {
                "ok": True,
                "card": card,
                "stats": agent_office_saju_learn.stats(),
                "pack": agent_office_saju_learn.export_pack(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/saju-learn/<int:card_id>", methods=["DELETE"])
@require_office_access
def agent_office_saju_learn_delete(card_id: int):
    import agent_office_saju_learn

    ok = agent_office_saju_learn.delete_card(card_id)
    return Response(
        json.dumps({"ok": ok, "stats": agent_office_saju_learn.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        status=200 if ok else 404,
    )


@app.route("/api/saju/reading/compose", methods=["POST"])
def saju_reading_compose():
    """
    심층 풀이 경로: PASS 카드 2장+ 매칭 시 조합(무료), 아니면 LLM.
    saju-v2 연동용. SAJU_READING_API_ENABLED=1 필요.

    reading_kind: full | daily | monthly | summary (채팅 요약)
    응답: text_chat(짧음), text_full(심층), display.body (=text_chat)
    오늘: daily / 다음달: monthly / 나의 운세 요약: summary
    """
    if os.getenv("SAJU_READING_API_ENABLED", "0").strip() not in ("1", "true", "yes"):
        return Response(
            json.dumps({"ok": False, "error": "saju reading API disabled"}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    payload = request.get_json(silent=True) or {}
    try:
        import saju_reading_engine
        from saju_reading_intent import apply_intent_to_context

        ctx = payload.get("context") if isinstance(payload.get("context"), dict) else payload
        if not isinstance(ctx, dict):
            ctx = {}
        for key in ("reading_kind", "reading_mode", "fortune_kind", "mode"):
            if key in payload and payload[key] is not None:
                ctx = {**ctx, key: payload[key]}
        for key in ("user_query", "question", "message", "topic", "surface"):
            if key in payload and payload.get(key) is not None:
                ctx = {**ctx, key: payload[key]}
        surface = str(payload.get("surface") or ctx.get("surface") or "chat")
        ctx = apply_intent_to_context(ctx, surface=surface)
        result = saju_reading_engine.build_reading(ctx)
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)[:200]}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps(result, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/gemma/knowledge-hits")
def gemma_knowledge_hits():
    """RAG 매칭 미리보기 — Connect AI Lab 포함 gemma_knowledge."""
    q = (request.args.get("q") or request.args.get("query") or "").strip()
    topic = (request.args.get("topic") or "").strip()
    if len(q) < 2:
        return Response(
            json.dumps({"ok": False, "error": "q required"}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    import gemma24_local

    domain = gemma24_local.infer_rag_domain(q, topic)
    cards = gemma24_local.search_injected_knowledge(
        q, topic, domain=domain, public_only=True, limit=5
    )
    return Response(
        json.dumps(
            {
                "ok": True,
                "domain": domain,
                "count": len(cards),
                "sources": gemma24_local.format_knowledge_sources(cards, max_titles=5),
                "hits": [
                    {
                        "id": c.get("id"),
                        "title": c.get("title"),
                        "summary": (c.get("summary") or "")[:240],
                        "source": c.get("source"),
                        "tags": (c.get("tags") or [])[:8],
                    }
                    for c in cards
                ],
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/connect-ai-lab-sync", methods=["POST"])
@require_office_access
def agent_office_connect_ai_lab_sync():
    """Connect AI Lab brain + 문서 → Coupax RAG (사무실 수동)."""
    payload = request.get_json(silent=True) or {}
    skip_swiki = str(payload.get("skip_swiki", "")).lower() in ("1", "true", "yes")
    try:
        import sync_connect_ai_lab

        report = sync_connect_ai_lab.cmd_full(skip_swiki=skip_swiki)
        return Response(
            json.dumps({"ok": True, "report": report}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)[:300]}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/saju-learn/export.json")
@require_office_access
def agent_office_saju_learn_export():
    import agent_office_saju_learn

    pack = agent_office_saju_learn.export_pack()
    return Response(
        json.dumps(pack, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "attachment; filename=saju_knowledge_pack.json",
        },
    )


@app.route("/api/agents/office/kiwoom-chasu.json")
@require_office_access
def agent_office_kiwoom_learn_json():
    import agent_office_kiwoom_learn

    rl: dict = {}
    try:
        import kiwoom_card_rl_engine as rle

        rl = rle.status()
    except Exception:
        pass

    return Response(
        json.dumps(
            {
                "stats": agent_office_kiwoom_learn.stats(),
                "cards": agent_office_kiwoom_learn.list_cards(limit=50),
                "rl": rl,
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/kiwoom-chasu/learn-path.json")
@require_office_access
def agent_office_kiwoom_learn_path():
    import wonhero_learn_path

    return Response(
        json.dumps(wonhero_learn_path.build_path_report(), ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/kiwoom-chasu/learn-path/<int:step>/complete", methods=["POST"])
@require_office_access
def agent_office_kiwoom_learn_path_complete(step: int):
    import wonhero_learn_path

    st = wonhero_learn_path.mark_step_done(step)
    return Response(
        json.dumps(
            {
                "ok": True,
                "path": wonhero_learn_path.build_path_report(),
                "state": st,
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/kiwoom-chasu/compose-next", methods=["POST"])
@require_office_access
def agent_office_kiwoom_compose_next():
    """갭 1건 — 제목 자동 생성 + 9젬마 협업 제작."""
    try:
        import kiwoom_card_council as kc
        import kiwoom_card_gap_detector as gap_det
        import kiwoom_card_title_compose as kt
        import agent_office_kiwoom_learn as learn

        gaps = gap_det.detect_gaps()
        missing = [m for m in gaps.get("missing") or [] if isinstance(m.get("spec"), dict)]
        if not missing:
            return Response(
                json.dumps(
                    {"ok": True, "created": 0, "message": "갭 없음", "stats": learn.stats()},
                    ensure_ascii=False,
                ),
                mimetype="application/json; charset=utf-8",
            )
        spec = kt.enrich_spec(dict(missing[0]["spec"]))
        out = kc.create_card_via_council(spec, source="office_compose_next") if kc.council_enabled() else None
        if not out:
            return Response(
                json.dumps({"ok": False, "error": "제작 실패 또는 중복"}, ensure_ascii=False),
                status=400,
                mimetype="application/json; charset=utf-8",
            )
        return Response(
            json.dumps(
                {"ok": True, "card": out, "stats": learn.stats()},
                ensure_ascii=False,
            ),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)[:400]}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/kiwoom-chasu/seed-error-cards", methods=["POST"])
@require_office_access
def agent_office_kiwoom_seed_error_cards():
    """젬마 기억(카드 학습) — 오류 해결 방법 meta 카드 일괄 제작."""
    try:
        import seed_kiwoom_error_method_cards as seed_err

        result = seed_err.run(dry_run=False, use_council=True)
        import agent_office_kiwoom_learn

        return Response(
            json.dumps(
                {
                    "ok": True,
                    "result": result,
                    "stats": agent_office_kiwoom_learn.stats(),
                },
                ensure_ascii=False,
            ),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)[:400]}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/kiwoom-chasu/ingest", methods=["POST"])
@require_office_access
def agent_office_kiwoom_learn_ingest():
    import agent_office_kiwoom_learn

    payload = request.get_json(silent=True) or request.form
    body = (payload.get("body") or payload.get("text") or "").strip()
    title = (payload.get("title") or "").strip()
    catalog_seed = (payload.get("catalog_seed") or "").strip()
    if not body:
        return Response(
            json.dumps({"ok": False, "error": "학습 본문을 입력해 주세요."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        card = agent_office_kiwoom_learn.add_card(
            body=body,
            title=title,
            source="office_paste",
            catalog_seed=catalog_seed,
            revise_if_seed_exists=True,
        )
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "card": card, "stats": agent_office_kiwoom_learn.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/kiwoom-chasu/<int:card_id>/revise", methods=["POST", "PATCH"])
@require_office_access
def agent_office_kiwoom_learn_revise(card_id: int):
    import agent_office_kiwoom_learn

    payload = request.get_json(silent=True) or request.form
    body = (payload.get("body") or payload.get("text") or "").strip()
    title = (payload.get("title") or "").strip() or None
    catalog_seed = (payload.get("catalog_seed") or "").strip() or None
    if not body and title is None and catalog_seed is None:
        return Response(
            json.dumps({"ok": False, "error": "수정할 본문·제목·catalog_seed 중 하나는 필요합니다."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        card = agent_office_kiwoom_learn.revise_card(
            card_id,
            body=body or None,
            title=title,
            catalog_seed=catalog_seed,
        )
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    if not card:
        return Response(
            json.dumps({"ok": False, "error": "카드를 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "card": card, "stats": agent_office_kiwoom_learn.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/kiwoom-chasu/<int:card_id>/confirm", methods=["POST"])
@require_office_access
def agent_office_kiwoom_learn_confirm(card_id: int):
    import agent_office_kiwoom_learn

    card = agent_office_kiwoom_learn.confirm_card(card_id)
    if not card:
        return Response(
            json.dumps({"ok": False, "error": "카드를 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps(
            {
                "ok": True,
                "card": card,
                "stats": agent_office_kiwoom_learn.stats(),
                "pack": agent_office_kiwoom_learn.export_pack(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/kiwoom-chasu/<int:card_id>", methods=["DELETE"])
@require_office_access
def agent_office_kiwoom_learn_delete(card_id: int):
    import agent_office_kiwoom_learn

    ok = agent_office_kiwoom_learn.delete_card(card_id)
    return Response(
        json.dumps({"ok": ok, "stats": agent_office_kiwoom_learn.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        status=200 if ok else 404,
    )


@app.route("/api/agents/office/kiwoom-account.json")
@require_office_access
def agent_office_kiwoom_account_json():
    import agent_office_kiwoom_account

    agent_office_kiwoom_account.import_from_env_file()
    snap = agent_office_kiwoom_account.load_snapshot()
    return Response(
        json.dumps(
            {
                "snapshot": snap,
                "stats": agent_office_kiwoom_account.stats(),
                "summary": agent_office_kiwoom_account.summary_text(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/kiwoom-account", methods=["POST"])
@require_office_access
def agent_office_kiwoom_account_update():
    import agent_office_kiwoom_account

    payload = request.get_json(silent=True) or request.form
    positions_raw = payload.get("positions")
    positions = None
    if isinstance(positions_raw, list):
        positions = positions_raw
    elif isinstance(positions_raw, str) and positions_raw.strip():
        try:
            positions = json.loads(positions_raw)
        except json.JSONDecodeError:
            positions = None

    def _int_field(key: str):
        v = payload.get(key)
        if v is None or v == "":
            return None
        try:
            return int(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None

    snap = agent_office_kiwoom_account.update_snapshot(
        broker=(payload.get("broker") or "키움증권").strip(),
        account_mask=(payload.get("account_mask") or payload.get("mask") or "").strip(),
        deposit=_int_field("deposit"),
        orderable=_int_field("orderable"),
        eval_amount=_int_field("eval_amount"),
        profit_loss=_int_field("profit_loss"),
        profit_rate_pct=payload.get("profit_rate_pct"),
        positions=positions,
        note=(payload.get("note") or "").strip(),
        source="office_form",
    )
    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="kiwoom_account",
            kind="task",
            text="[계좌 현황 갱신]\n" + agent_office_kiwoom_account.summary_text()[:800],
            division="kiwoom-chasu",
        )
    except Exception:
        pass
    return Response(
        json.dumps(
            {
                "ok": True,
                "snapshot": snap,
                "stats": agent_office_kiwoom_account.stats(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/kiwoom-chasu/export.json")
@require_office_access
def agent_office_kiwoom_learn_export():
    import agent_office_kiwoom_learn

    pack = agent_office_kiwoom_learn.export_pack()
    return Response(
        json.dumps(pack, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "attachment; filename=kiwoom_knowledge_pack.json",
        },
    )


@app.route("/api/agents/office/homepage-design.json")
@require_office_access
def agent_office_homepage_design_learn_json():
    import agent_office_homepage_design_learn as dl

    return Response(
        json.dumps(
            {"stats": dl.stats(), "cards": dl.list_cards(limit=50)},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/homepage-design/ingest", methods=["POST"])
@require_office_access
def agent_office_homepage_design_learn_ingest():
    import agent_office_homepage_design_learn as dl

    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    title = (payload.get("title") or "").strip()
    if not body:
        return Response(
            json.dumps({"ok": False, "error": "본문이 필요합니다."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        card = dl.add_card(body=body, title=title, source="office_paste")
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "card": card, "stats": dl.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/homepage-design/confirm/<int:card_id>", methods=["POST"])
@require_office_access
def agent_office_homepage_design_learn_confirm(card_id: int):
    import agent_office_homepage_design_learn as dl

    card = dl.confirm_card(card_id)
    if not card:
        return Response(
            json.dumps({"ok": False, "error": "카드를 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps(
            {
                "ok": True,
                "card": card,
                "stats": dl.stats(),
                "pack": dl.export_pack(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/homepage-design/delete/<int:card_id>", methods=["POST"])
@require_office_access
def agent_office_homepage_design_learn_delete(card_id: int):
    import agent_office_homepage_design_learn as dl

    ok = dl.delete_card(card_id)
    return Response(
        json.dumps({"ok": ok, "stats": dl.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/homepage-design/debate-topics.json")
@require_office_access
def agent_office_homepage_design_debate_topics():
    import homepage_design_debate_generator as gen
    import agent_office_homepage_design_learn as dl

    pending = gen.propose_next_specs(limit=8)
    return Response(
        json.dumps(
            {
                "auto_enabled": gen.auto_enabled(),
                "max_per_run": gen.max_per_run(),
                "recent": gen.list_recent_topics(limit=15),
                "pending": [
                    {"catalog_seed": s.get("catalog_seed"), "title": s.get("title")}
                    for s in pending
                ],
                "stats": dl.stats(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/homepage-design/web-research-debate", methods=["POST"])
@require_office_access
def agent_office_homepage_design_web_research_debate():
    """외부 사이트 웹 검색 → 위원회 토론 → 확정 카드."""
    return _office_web_research_debate_response("homepage-design")


_WEB_RESEARCH_LEARN_MODULES = {
    "finance": "agent_office_finance_learn",
    "saju-learn": "agent_office_saju_learn",
    "gwansang-learn": "agent_office_gwansang_learn",
    "kiwoom-chasu": "agent_office_kiwoom_learn",
    "stock-watch": "agent_office_stock_learn",
    "homepage-design": "agent_office_homepage_design_learn",
    "workisus-chasu": "agent_office_workisus_learn",
}


def _office_web_research_debate_response(unit_slug: str):
    try:
        import importlib
        import office_web_research_debate as owrd

        payload = request.get_json(silent=True) or {}
        max_n = max(1, min(3, int(payload.get("max") or 1)))
        if unit_slug == "homepage-design":
            try:
                import homepage_design_web_research as hdwr

                out = hdwr.run_web_research_debate(max_n=max_n)
            except Exception:
                out = owrd.run_web_research_debate(unit_slug, max_n=max_n)
        else:
            out = owrd.run_web_research_debate(unit_slug, max_n=max_n)
        mod_name = _WEB_RESEARCH_LEARN_MODULES.get(unit_slug)
        stats = {}
        if mod_name:
            stats = importlib.import_module(mod_name).stats()
        return Response(
            json.dumps({"ok": out.get("ok", False), "result": out, "stats": stats}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/<unit_slug>/web-research-debate", methods=["POST"])
@require_office_access
def agent_office_unit_web_research_debate(unit_slug: str):
    """사업부 공통 — 웹 검색 → 위원회 토론 → 확정 카드."""
    if unit_slug not in _WEB_RESEARCH_LEARN_MODULES:
        return Response(
            json.dumps({"ok": False, "error": f"unknown unit: {unit_slug}"}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    if unit_slug == "homepage-design":
        return _office_web_research_debate_response(unit_slug)
    return _office_web_research_debate_response(unit_slug)


@app.route("/api/agents/office/homepage-design/seed-catalog", methods=["POST"])
@require_office_access
def agent_office_homepage_design_seed_catalog():
    try:
        import homepage_design_catalog_maintain as hcm
        import homepage_design_council as hdc

        out = hcm.run(debate=False)
        out["debate"] = hdc.run_debate_cycle()
        import agent_office_homepage_design_learn as dl

        return Response(
            json.dumps({"ok": True, "result": out, "stats": dl.stats()}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/homepage-design/export.json")
@require_office_access
def agent_office_homepage_design_learn_export():
    import agent_office_homepage_design_learn as dl

    pack = dl.export_pack()
    return Response(
        json.dumps(pack, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "attachment; filename=homepage_design_knowledge_pack.json",
        },
    )

@app.route("/api/agents/office/chief-dev.json")
@require_office_access
def agent_office_chief_dev_json():
    import agent_office_chief_dev_learn as cdl
    return Response(
        json.dumps(
            {"cards": cdl.list_cards(limit=50)},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )

@app.route("/api/agents/office/chief-dev/clear", methods=["POST"])
@require_office_access
def agent_office_chief_dev_clear():
    import agent_office_chief_dev_learn as cdl
    cdl.clear_cards()
    return jsonify({"ok": True})

@app.route("/api/agents/office/chief-dev/<int:card_id>", methods=["DELETE"])
@require_office_access
def agent_office_chief_dev_delete(card_id: int):
    import agent_office_chief_dev_learn as cdl
    if cdl.delete_card(card_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Card not found"}), 404

@app.route("/api/agents/office/local-code-sync", methods=["POST"])
def agent_office_local_code_sync():
    # 보안 강화를 위해 인증 키 확인 로직 (옵션)
    secret = request.headers.get("X-Local-Sync-Secret")
    if secret != "super_secret_local_key":  # 예시 키
        pass # 실제 서비스에서는 403 반환 가능

    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
        
    file_path = data.get("file_path", "알 수 없는 파일")
    code_snippet = data.get("code_snippet", "")
    
    # 젬마 LLM을 호출하여 이 코드에 대한 리뷰 카드 생성
    try:
        import chief_dev_council
        import agent_office_chief_dev_learn as cdl
        topic = f"로컬 코드 리뷰: {file_path.split('/')[-1]}"
        context = f"파일 경로: {file_path}\n코드 스니펫:\n{code_snippet[:1000]}"
        
        title, body = chief_dev_council.generate_debate_card(topic, context)
        cdl.add_card("로컬스캔, 코드리뷰", title, body)
        return jsonify({"ok": True, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agents/office/gwansang-learn.json")
@require_office_access
def agent_office_gwansang_learn_json():
    import agent_office_gwansang_learn as gl

    return Response(
        json.dumps(
            {"stats": gl.stats(), "cards": gl.list_cards(limit=50)},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/gwansang-learn/ingest", methods=["POST"])
@require_office_access
def agent_office_gwansang_learn_ingest():
    import agent_office_gwansang_learn as gl

    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    title = (payload.get("title") or "").strip()
    if not body:
        return Response(
            json.dumps({"ok": False, "error": "본문이 필요합니다."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        card = gl.add_card(body=body, title=title, source="office_paste")
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "card": card, "stats": gl.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/gwansang-learn/confirm/<int:card_id>", methods=["POST"])
@require_office_access
def agent_office_gwansang_learn_confirm(card_id: int):
    import agent_office_gwansang_learn as gl

    try:
        card = gl.confirm_card(card_id)
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    if not card:
        return Response(
            json.dumps({"ok": False, "error": "카드를 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps(
            {"ok": True, "card": card, "stats": gl.stats(), "pack": gl.export_pack()},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/gwansang-learn/delete/<int:card_id>", methods=["POST"])
@require_office_access
def agent_office_gwansang_learn_delete(card_id: int):
    import agent_office_gwansang_learn as gl

    ok = gl.delete_card(card_id)
    return Response(
        json.dumps({"ok": ok, "stats": gl.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/gwansang-learn/seed-catalog", methods=["POST"])
@require_office_access
def agent_office_gwansang_seed_catalog():
    try:
        import seed_gwansang_cards as sg

        out = sg.seed_all(sync=True, confirm=True)
        import agent_office_gwansang_learn as gl

        return Response(
            json.dumps({"ok": True, "result": out, "stats": gl.stats()}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/gwansang-learn/compose-gap", methods=["POST"])
@require_office_access
def agent_office_gwansang_compose_gap():
    import gwansang_card_compose as gcc
    import agent_office_gwansang_learn as gl

    payload = request.get_json(silent=True) or {}
    agent_id = (payload.get("agent_id") or "gwansang_compose").strip()
    try:
        out = gcc.compose_next_gap(agent_id=agent_id)
        pack = gl.export_pack()
        return Response(
            json.dumps(
                {"ok": True, "composed": out, "stats": gl.stats(), "pack_count": pack.get("card_count")},
                ensure_ascii=False,
            ),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/gwansang-learn/export.json")
@require_office_access
def agent_office_gwansang_learn_export():
    import agent_office_gwansang_learn as gl

    pack = gl.export_pack()
    return Response(
        json.dumps(pack, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "attachment; filename=gwansang_knowledge_pack.json",
        },
    )


@app.route("/api/agents/office/workisus-chasu.json")
@require_office_access
def agent_office_workisus_learn_json():
    import agent_office_workisus_learn as wl

    return Response(
        json.dumps(
            {"stats": wl.stats(), "cards": wl.list_cards(limit=50)},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/workisus-chasu/ingest", methods=["POST"])
@require_office_access
def agent_office_workisus_learn_ingest():
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    import agent_office_workisus_learn as wl

    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    title = (payload.get("title") or "").strip()
    if not body:
        return Response(
            json.dumps({"ok": False, "error": "본문이 필요합니다."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        card = wl.add_card(body=body, title=title, source="office_paste")
    except ValueError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "card": card, "stats": wl.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/workisus-chasu/confirm/<int:card_id>", methods=["POST"])
@require_office_access
def agent_office_workisus_learn_confirm(card_id: int):
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    import agent_office_workisus_learn as wl

    card = wl.confirm_card(card_id)
    if not card:
        return Response(
            json.dumps({"ok": False, "error": "카드를 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps(
            {"ok": True, "card": card, "stats": wl.stats(), "pack": wl.export_pack()},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/workisus-chasu/delete/<int:card_id>", methods=["POST"])
@require_office_access
def agent_office_workisus_learn_delete(card_id: int):
    import agent_office_workisus_learn as wl

    ok = wl.delete_card(card_id)
    return Response(
        json.dumps({"ok": ok, "stats": wl.stats()}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/workisus-chasu/seed-catalog", methods=["POST"])
@require_office_access
def agent_office_workisus_seed_catalog():
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    try:
        import seed_workisus_cards as sw
        import seed_workisus_error_cards as serr

        out = sw.seed_all(sync=True, confirm=True)
        err_out = serr.seed_errors(sync=True)
        import agent_office_workisus_learn as wl

        return Response(
            json.dumps(
                {"ok": True, "result": out, "errors": err_out, "stats": wl.stats()},
                ensure_ascii=False,
            ),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/workisus-chasu/export.json")
@require_office_access
def agent_office_workisus_learn_export():
    import agent_office_workisus_learn as wl

    pack = wl.export_pack()
    return Response(
        json.dumps(pack, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": "attachment; filename=workisus_knowledge_pack.json",
        },
    )


@app.route("/api/agents/office/workisus-chasu/trading-context.json")
@require_office_access
def agent_office_workisus_trading_context():
    """확정 학습 카드 → HTS·Cursor 매매 플레이북 텍스트."""
    import agent_office_workisus_learn as wl
    import workisus_agent_card_compose as wac

    text = wac.export_trading_context()
    return Response(
        json.dumps(
            {
                "ok": True,
                "stats": wl.stats(),
                "pack_path": "board/data/workisus_learning/workisus_knowledge_pack.json",
                "context": text,
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/workisus-chasu/atr-rl-autofill", methods=["POST"])
@require_office_access
def agent_office_workisus_atr_rl_autofill():
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    try:
        import workisus_atr_card_rl_autofill as arlf
        import agent_office_workisus_learn as wl

        payload = request.get_json(silent=True) or {}
        max_add = max(1, min(8, int(payload.get("max_add") or 2)))
        out = arlf.run(max_add=max_add, dry_run=bool(payload.get("dry_run")))
        return Response(
            json.dumps({"ok": True, "result": out, "stats": wl.stats()}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/workisus-chasu/seed-atr", methods=["POST"])
@require_office_access
def agent_office_workisus_seed_atr():
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    try:
        import seed_workisus_atr_cards as satr
        import agent_office_workisus_learn as wl

        out = satr.seed_atr(sync=True)
        wl.export_pack()
        return Response(
            json.dumps({"ok": True, "result": out, "stats": wl.stats()}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/workisus-chasu/seed-errors", methods=["POST"])
@require_office_access
def agent_office_workisus_seed_errors():
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    try:
        import seed_workisus_error_cards as serr
        import agent_office_workisus_learn as wl

        out = serr.seed_errors(sync=True)
        wl.export_pack()
        return Response(
            json.dumps({"ok": True, "result": out, "stats": wl.stats()}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/workisus-chasu/compose-gap", methods=["POST"])
@require_office_access
def agent_office_workisus_compose_gap():
    """갭 카드 1건 제작·확정 (에이전트 수동 트리거)."""
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return _workisus_card_production_blocked_response()
    import workisus_agent_card_compose as wac
    import agent_office_workisus_learn as wl

    payload = request.get_json(silent=True) or {}
    agent_id = (payload.get("agent_id") or "workisus_curator").strip()
    try:
        out = wac.compose_next_gap(agent_id=agent_id)
        pack = wl.export_pack()
        return Response(
            json.dumps(
                {"ok": True, "composed": out, "stats": wl.stats(), "pack_count": pack.get("card_count")},
                ensure_ascii=False,
            ),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/stock-watch.json")
@require_office_access
def agent_office_stock_watch_json():
    import agent_office_stock_watch as sw

    snap = sw.load_snapshot()
    return Response(
        json.dumps(
            {
                "ok": True,
                "stats": sw.stats(),
                "snapshot": snap,
                "insights": sw.load_insights(),
                "summary": sw.summary_text(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/stock-watch/official-research", methods=["POST"])
@require_office_access
def agent_office_stock_official_research():
    import agent_office_log
    import agent_office_stock_official as off
    import agent_office_stock_watch as sw

    result = off.run_all_official()
    summaries = []
    for key in (
        "disclosure",
        "government",
        "press",
        "rates_dollar",
        "bonds",
        "commodities",
        "oil_war",
        "ceo_remarks",
        "youtube",
        "analyst_reports",
    ):
        block = result.get(key) or {}
        if block.get("summary"):
            summaries.append(block["summary"])
    text = "\n\n".join(summaries)[:1500]
    try:
        agent_office_log.append_message(
            from_id="stock_macro",
            kind="task",
            text=text or "공시·매크로·리포트·CEO 조사 완료",
            division=sw.DIVISION,
        )
    except Exception:
        pass
    return Response(
        json.dumps(
            {"ok": True, "result": result, "insights": sw.load_insights()},
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/stock-watch/verify-comments", methods=["POST"])
@require_office_access
def agent_office_stock_verify_comments():
    import agent_office_log
    import agent_office_stock_comments as sc
    import agent_office_stock_watch as sw

    r = sc.run_comment_verify()
    try:
        agent_office_log.append_message(
            from_id="stock_listener",
            kind="task",
            text=(r.get("summary") or sc.summary_text())[:1500],
            division=sw.DIVISION,
        )
    except Exception:
        pass

    return Response(
        json.dumps(
            {
                "ok": True,
                "result": r,
                "insights": sw.load_insights(),
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/stock-watch/sync", methods=["POST"])
@require_office_access
def agent_office_stock_watch_sync():
    import agent_office_log
    import agent_office_stock_watch as sw

    r = sw.sync_market_data(force=True)
    comment_verify = None
    if r.get("ok"):
        try:
            agent_office_log.append_message(
                from_id="stock_radar",
                kind="task",
                text=sw.summary_text()[:1500],
                division=sw.DIVISION,
            )
        except Exception:
            pass
        if os.getenv("STOCK_COMMENT_VERIFY_ON_SYNC", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            try:
                import agent_office_stock_comments as sc

                comment_verify = sc.run_comment_verify()
            except Exception:
                pass
        if os.getenv("STOCK_OFFICIAL_ON_SYNC", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            try:
                import agent_office_stock_official as off

                off.run_all_official()
            except Exception:
                pass
    return Response(
        json.dumps(
            {
                "ok": bool(r.get("ok")),
                "result": r,
                "stats": sw.stats(),
                "snapshot": sw.load_snapshot(),
                "insights": sw.load_insights(),
                "summary": sw.summary_text(),
                "comment_verify": comment_verify,
            },
            ensure_ascii=False,
        ),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/cursor-inbox/<item_id>", methods=["POST"])
@require_office_access
def agent_office_cursor_inbox_update(item_id: str):
    """Cursor 처리 상태 갱신 (pending | in_progress | done | skipped)."""
    import agent_office_cursor_bridge

    payload = request.get_json(silent=True) or {}
    status = (payload.get("status") or request.form.get("status") or "").strip()
    note = (payload.get("note") or request.form.get("note") or "").strip()
    if not status:
        return Response(
            json.dumps({"ok": False, "error": "status required"}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    ok = agent_office_cursor_bridge.set_cursor_status(item_id, status, note=note)
    if not ok:
        return Response(
            json.dumps({"ok": False, "error": "item not found"}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "id": item_id, "status": status}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route("/api/agents/office/blog-publish/status.json")
@require_office_access
def agent_office_blog_publish_status():
    try:
        import blog_publish_scheduler

        payload = blog_publish_scheduler.status()
    except Exception as e:
        payload = {"enabled": False, "error": str(e)[:200]}
    return Response(
        json.dumps(payload, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/agents/office/draft/<int:post_id>/queue", methods=["POST"])
@require_office_access
def agent_office_queue_draft(post_id: int):
    """순차 발행 우선 선발."""
    db = get_db()
    row = db.execute(
        "SELECT id, COALESCE(is_draft, 0) AS is_draft FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()
    if not row:
        return Response(
            json.dumps({"ok": False, "error": "글을 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    if not row["is_draft"]:
        return Response(
            json.dumps({"ok": False, "error": "이미 공개된 글입니다."}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        import blog_publish_scheduler

        out = blog_publish_scheduler.queue_priority(post_id)
        blog_publish_scheduler.plan()
        st = blog_publish_scheduler.status()
        out["scheduled"] = st.get("scheduled")
        return Response(
            json.dumps(out, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    except Exception as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)[:200]}, ensure_ascii=False),
            status=500,
            mimetype="application/json; charset=utf-8",
        )


@app.route("/api/agents/office/draft/<int:post_id>/publish", methods=["POST"])
@require_office_access
def agent_office_publish_draft(post_id: int):
    """초안 글 공개 — 순차 발행 ON 이면 즉시 발행 대신 예약·선발."""
    payload = request.get_json(silent=True) if request.is_json else {}
    force = request.args.get("force") == "1" or (payload or {}).get("force") is True
    db = get_db()
    row = db.execute(
        "SELECT id, COALESCE(is_draft, 0) AS is_draft FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()
    if not row:
        return Response(
            json.dumps({"ok": False, "error": "글을 찾을 수 없습니다."}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    if not row["is_draft"]:
        return Response(
            json.dumps({"ok": True, "post_id": post_id, "already_published": True}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    try:
        import blog_publish_scheduler

        if blog_publish_scheduler.block_immediate_publish() and not force:
            blog_publish_scheduler.queue_priority(post_id)
            blog_publish_scheduler.plan()
            st = blog_publish_scheduler.status()
            sched = st.get("scheduled") or {}
            return Response(
                json.dumps(
                    {
                        "ok": True,
                        "queued": True,
                        "post_id": post_id,
                        "message": (
                            "순차 발행 모드입니다. 오늘 랜덤 시각에 1건만 공개됩니다. "
                            f"예약: {sched.get('publish_at') or '대기 중'}"
                        ),
                        "scheduled": sched,
                    },
                    ensure_ascii=False,
                ),
                mimetype="application/json; charset=utf-8",
            )
    except ImportError:
        pass

    db.execute("UPDATE posts SET is_draft = 0 WHERE id = ?", (post_id,))
    db.commit()
    return Response(
        json.dumps({"ok": True, "post_id": post_id, "view_url": url_for("view", post_id=post_id)}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


def _load_saju_knowledge_summary() -> dict:
    try:
        import agent_office_wiki_store

        return agent_office_wiki_store.knowledge_stats(agent_office_wiki_store.DOMAIN_SAJU)
    except Exception:
        return {
            "updated_at": "",
            "wiki_count": 0,
            "meta_count": 0,
            "recent_wiki": [],
        }


def load_gemma_knowledge_summary() -> dict:
    try:
        import agent_office_wiki_store

        out = agent_office_wiki_store.knowledge_stats()
    except Exception:
        out = {
            "updated_at": "",
            "wiki_count": 0,
            "meta_count": 0,
            "recent_wiki": [],
            "by_domain": {},
        }
    try:
        import agent_office_swiki_sync

        st = agent_office_swiki_sync.load_state()
        out["swiki"] = {
            "last_push": st.get("last_push") or "",
            "last_pull": st.get("last_pull") or "",
            "synced_count": len(st.get("synced_wiki_ids") or []),
            "last_error": (st.get("last_error") or "")[:120],
            "repo": str(agent_office_swiki_sync._repo_path()),
        }
    except Exception:
        out["swiki"] = {}
    return out


@app.route("/api/agents/office/knowledge.json")
@require_office_access
def agent_office_knowledge_json():
    import agent_office_wiki_store

    domain = (request.args.get("domain") or "").strip()
    if domain == agent_office_wiki_store.DOMAIN_SAJU:
        payload = _load_saju_knowledge_summary()
    elif domain == agent_office_wiki_store.DOMAIN_KIWOM:
        payload = _load_kiwoom_knowledge_summary()
    elif domain == agent_office_wiki_store.DOMAIN_DESIGN:
        payload = _load_design_knowledge_summary()
    elif domain == agent_office_wiki_store.DOMAIN_WORKISUS:
        payload = _load_workisus_knowledge_summary()
    elif domain == agent_office_wiki_store.DOMAIN_GWANSANG:
        payload = _load_gwansang_knowledge_summary()
    elif domain == agent_office_wiki_store.DOMAIN_FINANCE:
        payload = agent_office_wiki_store.knowledge_stats(agent_office_wiki_store.DOMAIN_FINANCE)
    else:
        payload = load_gemma_knowledge_summary()
    return Response(
        json.dumps(payload, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


def _submit_office_instruction(*, want_json: bool):
    payload = request.get_json(silent=True) if request.is_json else request.form
    if not payload:
        payload = request.form
    text = (payload.get("body") or "").strip()
    unit = (payload.get("division") or "finance").strip() or "finance"
    if not text:
        err = "지시 내용을 입력해 주세요."
        if want_json:
            return Response(
                json.dumps({"ok": False, "error": err}, ensure_ascii=False),
                status=400,
                mimetype="application/json; charset=utf-8",
            )
        flash(err, "error")
        return redirect(url_for("agent_office", unit=unit))

    try:
        row = _agent_office_tasks.add_task(
            body=text,
            assign_to=(payload.get("assign_to") or "all").strip() or "all",
            priority=(payload.get("priority") or "normal").strip(),
            title=(payload.get("title") or "").strip(),
            created_by="대표님",
            division=unit,
        )
        try:
            import agent_office_task_runner

            agent_office_task_runner.process_queued_tasks(max_tasks=1)
            row = _agent_office_tasks.find_task(row["id"]) or row
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("office instruct process: %s", exc)
    except ValueError as e:
        if want_json:
            return Response(
                json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
                status=400,
                mimetype="application/json; charset=utf-8",
            )
        flash(str(e), "error")
        return redirect(url_for("agent_office", unit=unit))

    if want_json:
        return Response(
            json.dumps({"ok": True, "task": row}, ensure_ascii=False),
            mimetype="application/json; charset=utf-8",
        )
    status = row.get("status") or "queued"
    if status == "done":
        flash(f"작업 지시 #{row['id']}를 전달했고 에이전트가 처리했습니다.", "success")
    elif status == "in_progress":
        flash(f"작업 지시 #{row['id']}를 전달했습니다. 에이전트가 처리 중입니다.", "success")
    else:
        flash(f"작업 지시 #{row['id']}를 전달했습니다. (대기 — cron worker가 곧 처리합니다)", "success")
    return redirect(url_for("agent_office", unit=unit))


@app.route("/agents/office/instruct", methods=["POST"])
@require_office_access
def agent_office_instruct_form():
    """작업지시 폼 POST (JS 없이도 동작)."""
    return _submit_office_instruction(want_json=False)


@app.route("/api/agents/office/instruct", methods=["POST"])
@require_office_access
def agent_office_instruct():
    """작업지시 JSON API."""
    return _submit_office_instruction(want_json=True)


@app.route("/api/agents/office/mode", methods=["POST"])
@require_office_access
def agent_office_set_mode():
    """에이전트 mode_on / 전체 상시 ON 설정. 사무실 로그인 세션 필요."""
    if not _office_mode_control_allowed():
        return Response(
            json.dumps(
                {"ok": False, "error": "login_required"},
                ensure_ascii=False,
            ),
            status=401,
            mimetype="application/json; charset=utf-8",
        )

    import agent_registry

    body = request.get_json(silent=True) or {}
    office_flag = body.get("office_always_on")
    if office_flag is None:
        office_flag = body.get("global_always_on")
    if office_flag is not None:
        reg = agent_registry.set_office_always_on(bool(office_flag))
        return Response(
            json.dumps(
                {
                    "ok": True,
                    "office_always_on": reg.get("office_always_on"),
                    "global_always_on": reg.get("global_always_on"),
                },
                ensure_ascii=False,
            ),
            mimetype="application/json; charset=utf-8",
        )

    agent_id = (body.get("agent_id") or "").strip()
    if not agent_id:
        return Response(
            json.dumps({"ok": False, "error": "agent_id required"}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    mode_on = body.get("mode_on")
    if mode_on is None:
        return Response(
            json.dumps({"ok": False, "error": "mode_on required"}, ensure_ascii=False),
            status=400,
            mimetype="application/json; charset=utf-8",
        )
    try:
        row = agent_registry.set_agent_mode(agent_id, bool(mode_on))
    except KeyError as e:
        return Response(
            json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            status=404,
            mimetype="application/json; charset=utf-8",
        )
    return Response(
        json.dumps({"ok": True, "agent": row}, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )


@app.route('/robots.txt')
def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /agents/\n"
        "Disallow: /private/\n"
        f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap():
    db = get_db()
    posts = db.execute(
        f"SELECT id, created FROM posts p WHERE {_POST_PUBLISHED_WHERE} ORDER BY id DESC LIMIT 500"
    ).fetchall()
    pages = [
        url_for('index', _external=True),
        url_for('blog', _external=True),
        url_for('about', _external=True),
        url_for('contact', _external=True),
        url_for('privacy', _external=True),
        url_for('terms', _external=True),
    ]
    if etf_ops_enabled():
        pages.extend(
            [
                url_for('etf_hub', _external=True),
                url_for('etf_monthly_sheet', _external=True),
                url_for('data_product_etf', _external=True),
            ]
        )
    if ADSENSE_CLIENT.startswith("ca-pub-"):
        pages.append(url_for("ads_txt", _external=True))
    post_urls = [url_for('view', post_id=row['id'], _external=True) for row in posts]
    urls = pages + post_urls

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for loc in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{loc}</loc>")
        xml_lines.append("  </url>")
    xml_lines.append('</urlset>')
    return Response("\n".join(xml_lines), mimetype='application/xml')


@app.route("/ads.txt")
def ads_txt():
    if ADSENSE_CLIENT.startswith("ca-pub-"):
        pub_id = ADSENSE_CLIENT.replace("ca-pub-", "", 1)
        line = f"google.com, pub-{pub_id}, DIRECT, f08c47fec0942fa0\n"
        return Response(
            line,
            mimetype="text/plain",
            headers={"Cache-Control": "public, max-age=600"},
        )
    return Response(
        "# AdSense not configured: set ADSENSE_CLIENT=ca-pub-... in board/.env\n",
        mimetype="text/plain",
        status=404,
    )


if __name__ == '__main__':
    init_db()
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5001")),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
