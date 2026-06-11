"""
종목 시리즈 블로그 — 하루 1종목 신규 글 + 발행된 글에 매일 시세 댓글.

  python scripts/blog_stock_series.py publish      # 오늘 종목 1건 발행
  python scripts/blog_stock_series.py comments    # 시리즈 글들에 오늘 변동 댓글
  python scripts/blog_stock_series.py tick        # publish + comments (cron용)
  python scripts/blog_stock_series.py status

환경 변수:
  BLOG_STOCK_SERIES_ENABLED=1
  BLOG_STOCK_SERIES_PER_DAY=2        # 하루 신규 종목 글 수
  BLOG_STOCK_SERIES_TRACK_DAYS=30    # 댓글 갱신 대상: 최근 N일 내 발행 글
  BLOG_STOCK_SERIES_AUTHOR=머니인사이트
  BLOG_STOCK_SERIES_COMMENT_AUTHOR=시황일지
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import board_env  # noqa: E402
import json_store  # noqa: E402
import blog_adsense_enrich as adsense  # noqa: E402
import blog_stock_series_report as series_report  # noqa: E402
import blog_stock_series_research as series_research  # noqa: E402

DB_PATH = board_env.resolve_db_path()
STATE_PATH = BOARD / "data" / "blog_stock_series.json"
POST_MARKER = "coupax-stock-series"
COMMENT_PREFIX = "[시황일지]"


def _enabled() -> bool:
    return os.getenv("BLOG_STOCK_SERIES_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(os.getenv("BLOG_PUBLISH_TZ", "Asia/Seoul"))
    except Exception:
        return ZoneInfo("Asia/Seoul")


def _now() -> datetime:
    return datetime.now(_tz())


def _today() -> str:
    return _now().strftime("%Y-%m-%d")


def _now_str() -> str:
    return _now().strftime("%Y-%m-%d %H:%M")


def _track_days() -> int:
    return max(7, min(120, int(os.getenv("BLOG_STOCK_SERIES_TRACK_DAYS", "30") or "30")))


def _per_day() -> int:
    return max(1, min(5, int(os.getenv("BLOG_STOCK_SERIES_PER_DAY", "2") or "2")))


def _post_author() -> str:
    return (os.getenv("BLOG_STOCK_SERIES_AUTHOR") or "머니인사이트").strip() or "머니인사이트"


def _comment_author() -> str:
    return (os.getenv("BLOG_STOCK_SERIES_COMMENT_AUTHOR") or "시황일지").strip() or "시황일지"


def _draft_password() -> str:
    if str(BOARD) not in sys.path:
        sys.path.insert(0, str(BOARD))
    import security_utils  # noqa: E402

    plain = os.getenv("AGENT_OFFICE_BLOG_DRAFT_PASSWORD", "coupax2026").strip()
    return security_utils.hash_password(plain or "coupax2026")


def _default_state() -> dict:
    return {"cursor": 0, "entries": [], "last_publish_date": "", "last_comment_date": ""}


def load_state() -> dict:
    return json_store.load_json(STATE_PATH, default=_default_state())


def save_state(st: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    json_store.save_json(STATE_PATH, st)


def _universe_symbols() -> list[dict]:
    import stock_kr_universe as ku

    ku.ensure_universe_fresh()
    u = ku.load_universe()
    rows: list[dict] = []
    for pool in ("kospi200", "kosdaq150"):
        for row in u.get(pool) or []:
            sym = row.get("yahoo_symbol") or ""
            if sym:
                rows.append(
                    {
                        "symbol": sym,
                        "name": row.get("name") or sym,
                        "pool": pool,
                        "code": row.get("code") or "",
                    }
                )
    return rows


def _pick_next_symbol(st: dict) -> dict | None:
    universe = _universe_symbols()
    if not universe:
        return None
    cur = int(st.get("cursor") or 0) % len(universe)
    return universe[cur]


def _quote_for_symbol(snap: dict, symbol: str) -> dict | None:
    import agent_office_stock_watch as sw

    for q in sw.iter_kr_quotes(snap):
        if (q.get("symbol") or "") == symbol:
            return q
    return None


def _rl_for_symbol(ins: dict, symbol: str) -> dict | None:
    for it in (ins.get("rl_predictions") or {}).get("items") or []:
        if isinstance(it, dict) and it.get("symbol") == symbol:
            return it
    return None


def _post_marker(symbol: str) -> str:
    return f'<!-- {POST_MARKER} symbol="{html.escape(symbol)}" -->'


def _build_post_html(row: dict, snap: dict, ins: dict, today: str) -> tuple[str, str]:
    sym = row["symbol"]
    name = row.get("name") or sym
    q = _quote_for_symbol(snap, sym) or {}
    rl = _rl_for_symbol(ins, sym) or {}
    pct = float(q.get("change_pct") or 0)
    price = q.get("price", "—")
    pool = row.get("pool", "")
    pred = rl.get("predicted_ko") or "—"
    conf = rl.get("confidence")
    conf_s = f"{float(conf) * 100:.0f}%" if conf is not None else "—"

    title = f"{today} 종목 브리핑 — {name}"
    parts = [
        _post_marker(sym),
        f"<p><small>종목 시리즈 · {pool} · coupax-stock-series</small></p>",
        "[카테고리] ETF·주식",
        f"<p><strong>{html.escape(name)}</strong> "
        f"(<code>{html.escape(sym)}</code>) — "
        f"{html.escape(today)} 기준 시황부 스냅샷입니다. 투자 권유가 아닙니다.</p>",
        "<h2>1. 당일 시세</h2>",
        f"<p>가격 <strong>{html.escape(str(price))}</strong> · "
        f"등락 <strong class=\"{'stock-up' if pct > 0 else 'stock-down' if pct < 0 else ''}\">"
        f"{pct:+.2f}%</strong></p>",
        "<h2>2. RL 방향 예측 (참고)</h2>",
        f"<p>다음 구간 참고: <strong>{html.escape(pred)}</strong> "
        f"(신뢰 {html.escape(conf_s)}) — 강화학습 ε-greedy, 확정 전망 아님.</p>",
        "<h2>3. 이 글에서 이어짐</h2>",
        "<p>이 글 <strong>댓글</strong>에 거래일마다 시황일지가 변동 요약을 남깁니다. "
        "중요한 매매·세무·법률 판단은 공식 공시·HTS를 확인하세요.</p>",
        '<p class="post-disclaimer"><strong>면책</strong> '
        "일반 정보이며 투자·세무·법률 자문이 아닙니다.</p>",
    ]
    return title[:120], "\n\n".join(parts)


def _insert_post(title: str, content: str, *, publish: bool = True) -> int | None:
    import agent_office_blog_draft as bd

    if not DB_PATH.is_file():
        return None
    bd.ensure_posts_schema()
    is_draft = 0 if publish else 1
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO posts (title, author, content, password, created, views, is_draft)
            VALUES (?,?,?,?,?,0,?)
            """,
            (title[:120], _post_author(), content, _draft_password(), _now_str(), is_draft),
        )
        conn.commit()
        return int(cur.lastrowid)


def _comment_exists_today(conn: sqlite3.Connection, post_id: int) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM comments
        WHERE post_id=? AND substr(created, 1, 10)=?
          AND content LIKE ?
        LIMIT 1
        """,
        (post_id, _today(), f"{COMMENT_PREFIX}%"),
    ).fetchone()
    return bool(row)


def _min_comment_chars() -> int:
    return max(400, int(os.getenv("BLOG_STOCK_SERIES_MIN_COMMENT_CHARS", "500") or "500"))


def _build_comment_body(
    entry: dict,
    q: dict,
    today: str,
    snap: dict,
    ins: dict,
    dossier: dict | None = None,
) -> str:
    if dossier is None:
        dossier = series_research.get_dossier(entry.get("symbol") or "")
    return series_report.build_analyst_comment(
        entry,
        q,
        snap,
        ins,
        today,
        min_chars=_min_comment_chars(),
        dossier=dossier,
    )


def _entries_today(st: dict, today: str) -> list[dict]:
    return [
        e
        for e in (st.get("entries") or [])
        if isinstance(e, dict) and (e.get("published") or "") == today
    ]


def _publish_one(
    st: dict,
    row: dict,
    snap: dict,
    ins: dict,
    today: str,
    *,
    dossier: dict | None = None,
) -> dict | None:
    title, content = _build_post_html(row, snap, ins, today)
    post_id = _insert_post(title, content, publish=True)
    if not post_id:
        return None
    adsense.enrich_post(post_id, db_path=DB_PATH)
    q = _quote_for_symbol(snap, row["symbol"]) or {}
    entry = {
        "symbol": row["symbol"],
        "name": row.get("name"),
        "pool": row.get("pool"),
        "post_id": post_id,
        "published": today,
        "last_price": q.get("price"),
        "last_change_pct": q.get("change_pct"),
        "last_comment_date": today if q else "",
    }
    if q and DB_PATH.is_file():
        body = _build_comment_body(entry, q, today, snap, ins, dossier=dossier)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
                (post_id, _comment_author(), body, "", _now_str()),
            )
            conn.commit()
    entries = list(st.get("entries") or [])
    entries.append(entry)
    st["entries"] = entries[-400:]
    universe_len = max(len(_universe_symbols()), 1)
    st["cursor"] = (int(st.get("cursor") or 0) + 1) % universe_len
    return {
        "post_id": post_id,
        "symbol": row["symbol"],
        "name": row.get("name"),
        "title": title,
    }


def publish_daily_stock(*, force: bool = False) -> dict:
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    st = load_state()
    today = _today()
    per_day = _per_day()
    already = _entries_today(st, today)
    need = per_day - len(already)
    if need <= 0 and not force:
        return {
            "ok": True,
            "action": "already_today",
            "count": len(already),
            "posts": [
                {"post_id": e.get("post_id"), "symbol": e.get("symbol"), "name": e.get("name")}
                for e in already
            ],
        }

    import agent_office_stock_watch as sw

    snap = sw.load_snapshot()
    ins = sw.load_insights()
    published: list[dict] = []
    errors: list[str] = []
    pending_rows: list[dict] = []

    for _ in range(max(need, 0)):
        row = _pick_next_symbol(st)
        if not row:
            errors.append("empty_universe")
            break
        pending_rows.append(row)

    dossiers: dict = {}
    if pending_rows:
        dossiers = series_research.prepare_upload_research(pending_rows)
        snap = sw.load_snapshot()
        ins = sw.load_insights()

    for row in pending_rows:
        sym = row.get("symbol") or ""
        one = _publish_one(
            st, row, snap, ins, today, dossier=dossiers.get(sym)
        )
        if one:
            published.append(one)
        else:
            errors.append(row.get("symbol") or "?")

    st["last_publish_date"] = today
    save_state(st)

    if not published and errors:
        return {"ok": False, "error": "; ".join(errors[:3])}

    return {
        "ok": True,
        "action": "published" if published else "noop",
        "per_day": per_day,
        "count": len(published),
        "posts": published,
        "errors": errors,
    }


def update_series_comments(*, force: bool = False) -> dict:
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    import agent_office_stock_watch as sw

    today = _today()
    cutoff = (_now() - timedelta(days=_track_days())).strftime("%Y-%m-%d")

    st = load_state()
    entries = [e for e in (st.get("entries") or []) if isinstance(e, dict)]
    active = [e for e in entries if (e.get("published") or "") >= cutoff]
    added = 0
    skipped = 0
    missing = 0
    pending: list[dict] = []

    with sqlite3.connect(DB_PATH) as conn:
        for entry in active:
            sym = entry.get("symbol") or ""
            post_id = int(entry.get("post_id") or 0)
            if not post_id:
                continue
            row = conn.execute(
                "SELECT 1 FROM posts WHERE id=? AND COALESCE(is_draft,0)=0",
                (post_id,),
            ).fetchone()
            if not row:
                missing += 1
                continue
            if _comment_exists_today(conn, post_id):
                if force:
                    conn.execute(
                        """
                        DELETE FROM comments
                        WHERE post_id=? AND substr(created, 1, 10)=?
                          AND content LIKE ?
                        """,
                        (post_id, today, f"{COMMENT_PREFIX}%"),
                    )
                else:
                    skipped += 1
                    continue
            pending.append(entry)

    research_targets = [
        {"symbol": e.get("symbol"), "name": e.get("name")}
        for e in pending
        if e.get("symbol")
    ]
    dossiers = (
        series_research.prepare_upload_research(research_targets)
        if research_targets
        else {}
    )
    snap = sw.load_snapshot()
    ins = sw.load_insights()

    with sqlite3.connect(DB_PATH) as conn:
        for entry in pending:
            sym = entry.get("symbol") or ""
            post_id = int(entry.get("post_id") or 0)
            q = _quote_for_symbol(snap, sym)
            if not q:
                missing += 1
                continue
            sym = entry.get("symbol") or ""
            body = _build_comment_body(
                entry,
                q,
                today,
                snap,
                ins,
                dossier=dossiers.get(sym),
            )
            conn.execute(
                "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
                (post_id, _comment_author(), body, "", _now_str()),
            )
            entry["last_price"] = q.get("price")
            entry["last_change_pct"] = q.get("change_pct")
            entry["last_comment_date"] = today
            added += 1
        conn.commit()

    st["last_comment_date"] = today
    save_state(st)

    return {
        "ok": True,
        "action": "comments_updated",
        "added": added,
        "skipped": skipped,
        "missing_quote": missing,
        "tracked": len(active),
        "agents_researched": len(series_research._AGENT_JOBS),
        "dossiers": len(dossiers),
    }


def tick() -> dict:
    pub = publish_daily_stock()
    com = update_series_comments()
    return {"publish": pub, "comments": com}


def status() -> dict:
    st = load_state()
    universe = len(_universe_symbols())
    today = _today()
    return {
        "enabled": _enabled(),
        "per_day": _per_day(),
        "universe_size": universe,
        "cursor": st.get("cursor"),
        "entries": len(st.get("entries") or []),
        "today_published": len(_entries_today(st, today)),
        "last_publish_date": st.get("last_publish_date"),
        "last_comment_date": st.get("last_comment_date"),
        "track_days": _track_days(),
        "recent": (st.get("entries") or [])[-5:],
    }


def main() -> int:
    board_env.load_board_env()
    p = argparse.ArgumentParser(description="종목 시리즈 블로그")
    p.add_argument(
        "cmd",
        choices=["publish", "comments", "tick", "status"],
        nargs="?",
        default="status",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="publish: 오늘 이미 발행해도 다시 / comments: 오늘 시황일지 재작성",
    )
    args = p.parse_args()

    if args.cmd == "publish":
        out = publish_daily_stock(force=args.force)
    elif args.cmd == "comments":
        out = update_series_comments(force=args.force)
    elif args.cmd == "tick":
        out = tick()
    else:
        out = status()

    print(out)
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
