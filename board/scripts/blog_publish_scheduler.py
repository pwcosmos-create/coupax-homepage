"""
블로그 순차 발행 — 하루 1건, 랜덤 시각, AdSense 보강 후 공개.

  python scripts/blog_publish_scheduler.py plan    # 오늘 발행 1건 예약
  python scripts/blog_publish_scheduler.py tick    # 예약 시각 도래 시 발행
  python scripts/blog_publish_scheduler.py status

환경 변수:
  BLOG_SCHEDULED_PUBLISH_ENABLED=1   (기본 1)
  BLOG_PUBLISH_TZ=Asia/Seoul
  BLOG_PUBLISH_HOUR_START=8
  BLOG_PUBLISH_HOUR_END=21
  BLOG_ADSENSE_MIN_CHARS=1500
"""
from __future__ import annotations

import argparse
import os
import random
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
import blog_publish_dedupe as dedupe  # noqa: E402

DB_PATH = board_env.resolve_db_path()
STATE_PATH = BOARD / "data" / "blog_publish_scheduler.json"
def _enabled() -> bool:
    return os.getenv("BLOG_SCHEDULED_PUBLISH_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _tz() -> ZoneInfo:
    name = (os.getenv("BLOG_PUBLISH_TZ") or "Asia/Seoul").strip()
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Seoul")


def _now() -> datetime:
    return datetime.now(_tz())


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def _parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=_tz())
    except ValueError:
        return None


def _default_state() -> dict:
    return {
        "scheduled": None,
        "last_published_date": "",
        "priority_post_id": None,
        "blocked_post_ids": [],
        "history": [],
    }


def _coerce_post_id(value) -> int | None:
    try:
        n = int(value)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _blocked_ids(data: dict) -> set[int]:
    out: set[int] = set()
    for raw in data.get("blocked_post_ids") or []:
        pid = _coerce_post_id(raw)
        if pid:
            out.add(pid)
    return out


def load_state() -> dict:
    try:
        data = json_store.load_json(STATE_PATH, default=_default_state())
    except json_store.JsonStoreError:
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()
    data.setdefault("history", [])
    return data


def save_state(data: dict) -> None:
    json_store.save_json(STATE_PATH, data)


def _published_today(conn: sqlite3.Connection, today: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM posts
        WHERE COALESCE(is_draft, 0) = 0
          AND substr(created, 1, 10) = ?
        LIMIT 1
        """,
        (today,),
    ).fetchone()
    return bool(row)


def _list_draft_candidates(conn: sqlite3.Connection) -> list[dict]:
    """최근 초안 + 사무실(task) 초안만 후보 (전체 일괄 발행 방지)."""
    limit = int(os.getenv("BLOG_PUBLISH_CANDIDATE_LIMIT", "120") or "120")
    rows = conn.execute(
        f"""
        SELECT id, title, content, created
        FROM posts
        WHERE COALESCE(is_draft, 0) = 1
        ORDER BY id DESC
        LIMIT {max(20, min(limit, 300))}
        """
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        pid, title, content, created = r
        body = content or ""
        score = adsense.adsense_score(body)
        if "coupax-research-draft" in body:
            score += 45
        if "task_id=" in body or "사무실 작업" in body or "coupax-adsense-enriched" in body:
            score += 25
        if re.search(r"\[카테고리\]", body):
            score += 5
        out.append(
            {
                "id": int(pid),
                "title": (title or "")[:120],
                "created": created or "",
                "score": score,
                "text_len": len(adsense._strip_html(body)),
            }
        )
    return out


def _pick_post_id(
    conn: sqlite3.Connection,
    candidates: list[dict],
    priority: int | None,
    *,
    exclude: set[int] | None = None,
) -> tuple[int | None, list[dict]]:
    """중복 없는 초안 1건 선택. (post_id, skipped)."""
    exclude = exclude or set()
    unique, skipped = dedupe.filter_unique_candidates(conn, candidates)
    unique = [c for c in unique if int(c["id"]) not in exclude]
    if not unique:
        return None, skipped
    if priority is not None and priority not in exclude:
        for c in unique:
            if c["id"] == priority:
                return priority, skipped
        for c in candidates:
            if c["id"] == priority:
                skipped.append({**c, "skip_reason": "우선 지정 글이 공개글·대기글과 중복"})
    ready = [c for c in unique if c["score"] >= 40]
    pool = ready or unique
    pool.sort(key=lambda x: (-x["score"], x["id"]))
    return int(pool[0]["id"]), skipped


def _random_publish_at(now: datetime) -> datetime:
    start_h = int(os.getenv("BLOG_PUBLISH_HOUR_START", "8") or "8")
    end_h = int(os.getenv("BLOG_PUBLISH_HOUR_END", "21") or "21")
    start_h = max(0, min(start_h, 23))
    end_h = max(start_h, min(end_h, 23))
    day = now.date()
    start = datetime(day.year, day.month, day.day, start_h, 0, tzinfo=_tz())
    end = datetime(day.year, day.month, day.day, end_h, 59, tzinfo=_tz())
    if now >= end:
        return now + timedelta(minutes=5)
    if now < start:
        window_start = start
    else:
        window_start = now + timedelta(minutes=10)
    span_min = max(5, int((end - window_start).total_seconds() // 60))
    offset = random.randint(0, span_min)
    return window_start + timedelta(minutes=offset)


def plan(*, force: bool = False) -> dict:
    """오늘 발행할 초안 1건 예약."""
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    draft_ensure: dict = {}
    try:
        try:
            import board_env

            board_env.load_board_env()
        except ImportError:
            pass
        import blog_research_draft as rd

        draft_ensure = rd.ensure_daily_research_draft()
    except Exception as e:
        draft_ensure = {"ok": False, "error": str(e)[:120]}

    now = _now()
    today = now.strftime("%Y-%m-%d")
    data = load_state()
    scheduled = data.get("scheduled")
    if (
        isinstance(scheduled, dict)
        and scheduled.get("date") == today
        and not force
    ):
        return {"ok": True, "action": "already_scheduled", "scheduled": scheduled}

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    with sqlite3.connect(DB_PATH) as conn:
        if _published_today(conn, today) and not force:
            data["last_published_date"] = today
            save_state(data)
            return {"ok": True, "action": "already_published_today"}

        candidates = _list_draft_candidates(conn)
        priority = _coerce_post_id(data.get("priority_post_id"))
        blocked = _blocked_ids(data)
        skipped_all: list[dict] = []
        chosen: int | None = None
        enrich: dict = {}
        title = ""
        content = ""

        for attempt in range(int(os.getenv("BLOG_PUBLISH_PICK_MAX_TRIES", "15") or "15")):
            pick_priority = priority if attempt == 0 and priority else None
            post_id, skipped = _pick_post_id(
                conn, candidates, pick_priority, exclude=blocked
            )
            skipped_all.extend(skipped)
            if post_id is None:
                break
            enrich = adsense.enrich_post(post_id, db_path=DB_PATH)
            if not enrich.get("ok"):
                return {"ok": False, "error": enrich.get("error"), "post_id": post_id}

            row = conn.execute(
                "SELECT title, content FROM posts WHERE id=?", (post_id,)
            ).fetchone()
            title = (row[0] if row else "") or f"글 #{post_id}"
            content = (row[1] if row else "") or ""
            published = dedupe.load_published_index(conn)
            dup, reason = dedupe.is_duplicate_of_published(title, content, published)
            if dup:
                blocked.add(post_id)
                skipped_all.append(
                    {"id": post_id, "skip_reason": f"중복 차단: {reason}"}
                )
                continue
            chosen = post_id
            break

        if chosen is None:
            data["blocked_post_ids"] = sorted(blocked)[-120:]
            save_state(data)
            return {
                "ok": True,
                "action": "no_unique_drafts",
                "candidates": len(candidates),
                "skipped_duplicates": len(skipped_all),
                "blocked_count": len(blocked),
                "skipped_sample": [
                    {"id": s.get("id"), "reason": s.get("skip_reason")}
                    for s in skipped_all[:5]
                ],
            }

        publish_at = _random_publish_at(now)
        data["scheduled"] = {
            "date": today,
            "post_id": chosen,
            "publish_at": _fmt(publish_at),
            "title": title[:120],
            "score": enrich.get("score"),
            "dedupe": "ok",
        }
        data["blocked_post_ids"] = sorted(blocked)[-120:]
        if priority == chosen:
            data["priority_post_id"] = None
        save_state(data)
        out = {"ok": True, "action": "scheduled", "scheduled": data["scheduled"]}
        if draft_ensure:
            out["research_draft"] = draft_ensure
        return out


def publish_scheduled() -> dict:
    """예약 시각이 지난 글 1건 공개."""
    if not _enabled():
        return {"ok": True, "action": "disabled"}

    data = load_state()
    scheduled = data.get("scheduled")
    if not isinstance(scheduled, dict):
        return {"ok": True, "action": "nothing_scheduled"}

    publish_at = _parse_ts(str(scheduled.get("publish_at") or ""))
    now = _now()
    if publish_at and now < publish_at:
        return {
            "ok": True,
            "action": "waiting",
            "publish_at": scheduled.get("publish_at"),
        }

    post_id = _coerce_post_id(scheduled.get("post_id"))
    if post_id is None:
        data["scheduled"] = None
        save_state(data)
        return {"ok": False, "error": "invalid_post_id"}

    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    ts = scheduled.get("publish_at") or _fmt(now)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, COALESCE(is_draft, 0) FROM posts WHERE id=?",
            (post_id,),
        ).fetchone()
        if not row:
            data["scheduled"] = None
            save_state(data)
            return {"ok": False, "error": "not_found", "post_id": post_id}
        if not row[1]:
            data["scheduled"] = None
            data["last_published_date"] = now.strftime("%Y-%m-%d")
            save_state(data)
            return {"ok": True, "action": "already_public", "post_id": post_id}

        title_row = conn.execute(
            "SELECT title, content FROM posts WHERE id=?", (post_id,)
        ).fetchone()
        title = (title_row[0] if title_row else "") or ""
        content = (title_row[1] if title_row else "") or ""
        published = dedupe.load_published_index(conn)
        dup, reason = dedupe.is_duplicate_of_published(
            title, content, published, exclude_post_id=post_id
        )
        if dup:
            blocked = _blocked_ids(data)
            blocked.add(post_id)
            data["blocked_post_ids"] = sorted(blocked)[-120:]
            data["scheduled"] = None
            save_state(data)
            replan = plan(force=True)
            return {
                "ok": True,
                "action": "duplicate_skipped",
                "post_id": post_id,
                "reason": reason,
                "replan": replan,
            }

        adsense.enrich_post(post_id, db_path=DB_PATH)
        conn.execute(
            "UPDATE posts SET is_draft=0, created=? WHERE id=?",
            (ts, post_id),
        )
        conn.commit()

    hist = data.get("history") or []
    if not isinstance(hist, list):
        hist = []
    hist.append(
        {
            "post_id": post_id,
            "published_at": ts,
            "title": scheduled.get("title"),
        }
    )
    data["history"] = hist[-60:]
    data["last_published_date"] = now.strftime("%Y-%m-%d")
    data["scheduled"] = None
    save_state(data)

    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="creator",
            kind="conclusion",
            text=f"[블로그 순차 발행] post #{post_id} 공개 ({ts}) — {scheduled.get('title', '')[:80]}",
            division="finance",
        )
    except Exception:
        pass

    return {
        "ok": True,
        "action": "published",
        "post_id": post_id,
        "published_at": ts,
    }


def tick() -> dict:
    plan_r = plan()
    pub_r = publish_scheduled()
    return {"plan": plan_r, "publish": pub_r}


def status() -> dict:
    data = load_state()
    drafts = 0
    unique_ready = 0
    if DB_PATH.is_file():
        with sqlite3.connect(DB_PATH) as conn:
            drafts = conn.execute(
                "SELECT COUNT(*) FROM posts WHERE COALESCE(is_draft, 0)=1"
            ).fetchone()[0]
            cands = _list_draft_candidates(conn)
            unique, _ = dedupe.filter_unique_candidates(conn, cands)
            unique_ready = len(unique)
    return {
        "enabled": _enabled(),
        "tz": str(_tz()),
        "now": _fmt(_now()),
        "draft_count": drafts,
        "unique_candidate_count": unique_ready,
        "scheduled": data.get("scheduled"),
        "last_published_date": data.get("last_published_date"),
        "priority_post_id": data.get("priority_post_id"),
        "recent_history": (data.get("history") or [])[-5:],
    }


def queue_priority(post_id: int) -> dict:
    """사무실에서 '선발' — 다음 plan 시 우선."""
    data = load_state()
    data["priority_post_id"] = int(post_id)
    save_state(data)
    return {"ok": True, "priority_post_id": post_id}


def publish_post_now(post_id: int | None = None, *, refresh_research: bool = False) -> dict:
    """조사 초안 즉시 공개 (선택: refresh로 전체 조사 반영 후 발행)."""
    if not DB_PATH.is_file():
        return {"ok": False, "error": "db_missing"}

    refresh_r: dict = {}
    if refresh_research:
        try:
            import blog_research_draft as rd

            refresh_r = rd.refresh_stock_research_draft()
            if not refresh_r.get("ok"):
                return refresh_r
            post_id = refresh_r.get("post_id") or post_id
        except Exception as e:
            return {"ok": False, "error": f"refresh_failed: {e}"[:120]}

    if post_id is None:
        today = _now().strftime("%Y-%m-%d")
        try:
            import blog_research_draft as rd

            st = rd.load_state()
            post_id = st.get("last_post_id")
        except Exception:
            post_id = None
        if post_id is None:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    """
                    SELECT id FROM posts
                    WHERE COALESCE(is_draft, 0) = 1
                      AND content LIKE '%coupax-research-draft%'
                    ORDER BY id DESC LIMIT 1
                    """
                ).fetchone()
                post_id = int(row[0]) if row else None

    pid = _coerce_post_id(post_id)
    if pid is None:
        return {"ok": False, "error": "no_post_id"}

    now = _now()
    ts = _fmt(now)
    data = load_state()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, COALESCE(is_draft, 0), title, content FROM posts WHERE id=?",
            (pid,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "not_found", "post_id": pid}
        if not row[1]:
            return {"ok": True, "action": "already_public", "post_id": pid}

        title = row[2] or ""
        content = row[3] or ""
        published = dedupe.load_published_index(conn)
        dup, reason = dedupe.is_duplicate_of_published(
            title, content, published, exclude_post_id=pid
        )
        if dup:
            return {
                "ok": False,
                "action": "duplicate_blocked",
                "post_id": pid,
                "reason": reason,
            }

        enrich = adsense.enrich_post(pid, db_path=DB_PATH)
        conn.execute("UPDATE posts SET is_draft=0, created=? WHERE id=?", (ts, pid))
        conn.commit()

    sched = data.get("scheduled")
    if isinstance(sched, dict) and _coerce_post_id(sched.get("post_id")) == pid:
        data["scheduled"] = None
    data["last_published_date"] = now.strftime("%Y-%m-%d")
    hist = data.get("history") or []
    if not isinstance(hist, list):
        hist = []
    hist.append({"post_id": pid, "published_at": ts, "title": title[:80]})
    data["history"] = hist[-60:]
    save_state(data)

    return {
        "ok": True,
        "action": "published_now",
        "post_id": pid,
        "published_at": ts,
        "enrich": enrich,
        "refresh": refresh_r,
    }


def block_immediate_publish() -> bool:
    return _enabled() and os.getenv("BLOG_PUBLISH_MANUAL_BLOCK", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass

    p = argparse.ArgumentParser()
    p.add_argument(
        "cmd",
        choices=["plan", "tick", "status", "queue", "publish", "publish-now"],
        nargs="?",
    )
    p.add_argument("--post-id", type=int)
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--refresh",
        action="store_true",
        help="publish-now: 주식 시황 전체 조사 후 초안 갱신·발행",
    )
    args = p.parse_args()
    cmd = args.cmd or "tick"

    if cmd == "plan":
        out = plan(force=args.force)
    elif cmd == "publish":
        out = publish_scheduled()
    elif cmd == "publish-now":
        out = publish_post_now(
            args.post_id, refresh_research=args.refresh or args.force
        )
    elif cmd == "status":
        out = status()
    elif cmd == "queue":
        if not args.post_id:
            print("queue requires --post-id")
            return 2
        out = queue_priority(args.post_id)
    else:
        out = tick()

    print(out)
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
