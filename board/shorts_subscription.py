"""숏폼공장 글로벌 구독 — Stripe + 사용량 쿼터."""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

FREE_DAILY_LIMIT = max(1, int(os.getenv("SHORTS_FREE_DAILY_LIMIT", "1") or "1"))
QUOTA_TZ = ZoneInfo(os.getenv("SHORTS_QUOTA_TZ", "Asia/Seoul"))

PLANS: dict[str, dict[str, Any]] = {
    "starter": {
        "name": "Starter",
        "name_ko": "스타터",
        "name_ja": "スターター",
        "name_zh": "入门版",
        "name_es": "Inicial",
        "price_usd": 0,
        "free": True,
        "unlimited": True,
        "quota": 0,
        "stripe_price_env": "STRIPE_PRICE_STARTER",
    },
    "pro": {
        "name": "Pro",
        "name_ko": "프로",
        "name_ja": "プロ",
        "name_zh": "专业版",
        "name_es": "Pro",
        "price_usd": 29,
        "free": False,
        "quota": 40,
        "stripe_price_env": "STRIPE_PRICE_PRO",
    },
    "business": {
        "name": "Business",
        "name_ko": "비즈니스",
        "name_ja": "ビジネス",
        "name_zh": "商业版",
        "name_es": "Empresa",
        "price_usd": 79,
        "free": False,
        "quota": 150,
        "stripe_price_env": "STRIPE_PRICE_BUSINESS",
    },
}

COOKIE_NAME = "sf_access"
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
SHORTS_GOOGLE_API_KEY = ""  # legacy import; use get_google_api_key()


def get_google_api_key() -> str:
    import shorts_settings as _st

    return _st.get_google_api_key()
SITE_BASE_URL = os.getenv("SHORTS_SITE_URL", "https://coupax.co.kr").rstrip("/")
DEV_SUBSCRIBE = os.getenv("SHORTS_DEV_SUBSCRIBE", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _period_end(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def _today_local() -> str:
    return datetime.now(QUOTA_TZ).strftime("%Y-%m-%d")


def _is_free_plan(plan_id: str) -> bool:
    p = PLANS.get(plan_id)
    return bool(p and p.get("free"))


def _is_unlimited_plan(plan_id: str) -> bool:
    p = PLANS.get(plan_id)
    return bool(p and p.get("unlimited"))


def _ensure_subscriber_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(shorts_subscribers)")}
    if "daily_used" not in cols:
        conn.execute("ALTER TABLE shorts_subscribers ADD COLUMN daily_used INTEGER NOT NULL DEFAULT 0")
    if "daily_used_on" not in cols:
        conn.execute("ALTER TABLE shorts_subscribers ADD COLUMN daily_used_on TEXT NOT NULL DEFAULT ''")
    conn.commit()


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shorts_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            access_token TEXT NOT NULL UNIQUE,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            shorts_used INTEGER NOT NULL DEFAULT 0,
            quota INTEGER NOT NULL DEFAULT 10,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            created TEXT NOT NULL,
            daily_used INTEGER NOT NULL DEFAULT 0,
            daily_used_on TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.commit()
    _ensure_subscriber_columns(conn)


def stripe_enabled() -> bool:
    return bool(STRIPE_SECRET)


def plan_info(plan_id: str) -> dict[str, Any] | None:
    return PLANS.get(plan_id)


def list_plans_public() -> list[dict[str, Any]]:
    out = []
    for pid, p in PLANS.items():
        item = {
            "id": pid,
            "name": p["name"],
            "name_ko": p["name_ko"],
            "name_ja": p.get("name_ja", p["name"]),
            "name_zh": p.get("name_zh", p["name"]),
            "name_es": p.get("name_es", p["name"]),
            "price_usd": p["price_usd"],
            "quota": p["quota"],
            "free": bool(p.get("free")),
            "unlimited": bool(p.get("unlimited")),
        }
        out.append(item)
    return out


def plan_display_name(plan_id: str, locale: str) -> str:
    p = PLANS.get(plan_id)
    if not p:
        return plan_id
    if locale == "ko":
        return p["name_ko"]
    if locale == "ja":
        return p.get("name_ja", p["name"])
    if locale == "zh":
        return p.get("name_zh", p["name"])
    if locale == "es":
        return p.get("name_es", p["name"])
    return p["name"]


def get_subscriber_by_token(conn: sqlite3.Connection, token: str):
    if not token:
        return None
    return conn.execute(
        "SELECT * FROM shorts_subscribers WHERE access_token = ?",
        (token.strip(),),
    ).fetchone()


def _sync_daily_usage(conn: sqlite3.Connection, row) -> sqlite3.Row | Any:
    """유료 일일 쿼터 플랜: 날짜가 바뀌면 일일 사용량 리셋."""
    if _is_unlimited_plan(row["plan"]) or not _is_free_plan(row["plan"]):
        return row
    today = _today_local()
    if (row["daily_used_on"] or "") != today:
        conn.execute(
            "UPDATE shorts_subscribers SET daily_used = 0, daily_used_on = ? WHERE id = ?",
            (today, row["id"]),
        )
        conn.commit()
        return get_subscriber_by_token(conn, row["access_token"])
    return row


def subscriber_status(row) -> dict[str, Any] | None:
    if not row:
        return None
    plan = plan_info(row["plan"]) or {}
    free = _is_free_plan(row["plan"])
    active = row["status"] == "active" and (free or row["period_end"] >= _now_iso())

    if free:
        if _is_unlimited_plan(row["plan"]):
            return {
                "plan": row["plan"],
                "plan_name": plan.get("name", row["plan"]),
                "status": row["status"] if active else "expired",
                "active": active,
                "limit_type": "unlimited",
                "period_end": row["period_end"],
            }
        daily_quota = int(plan.get("daily_quota", FREE_DAILY_LIMIT))
        daily_used = int(row["daily_used"] or 0)
        if (row["daily_used_on"] or "") != _today_local():
            daily_used = 0
        remaining = max(0, daily_quota - daily_used)
        return {
            "plan": row["plan"],
            "plan_name": plan.get("name", row["plan"]),
            "status": row["status"] if active else "expired",
            "active": active,
            "quota": daily_quota,
            "used": daily_used,
            "remaining": remaining,
            "limit_type": "daily",
            "period_end": row["period_end"],
        }

    remaining = max(0, int(row["quota"]) - int(row["shorts_used"]))
    return {
        "plan": row["plan"],
        "plan_name": plan.get("name", row["plan"]),
        "status": row["status"] if active else "expired",
        "active": active,
        "quota": int(row["quota"]),
        "used": int(row["shorts_used"]),
        "remaining": remaining,
        "limit_type": "monthly",
        "period_end": row["period_end"],
    }


def can_generate(conn: sqlite3.Connection, token: str) -> tuple[bool, str, Any]:
    row = get_subscriber_by_token(conn, token)
    if not row:
        return False, "Active subscription required. Please subscribe first.", None
    row = _sync_daily_usage(conn, row)
    st = subscriber_status(row)
    if not st or not st["active"]:
        return False, "Your subscription is inactive or expired. Renew to continue.", row
    if st.get("limit_type") != "unlimited" and st["remaining"] <= 0:
        if st.get("limit_type") == "daily":
            return False, "Daily short quota reached. Try again tomorrow or upgrade your plan.", row
        return False, "Monthly short quota reached. Upgrade or wait for renewal.", row
    return True, "", row


def record_usage(conn: sqlite3.Connection, subscriber_id: int) -> None:
    row = conn.execute(
        "SELECT plan, daily_used, daily_used_on FROM shorts_subscribers WHERE id = ?",
        (subscriber_id,),
    ).fetchone()
    if not row:
        return
    if _is_unlimited_plan(row["plan"]):
        return
    if _is_free_plan(row["plan"]):
        today = _today_local()
        if (row["daily_used_on"] or "") != today:
            conn.execute(
                "UPDATE shorts_subscribers SET daily_used = 1, daily_used_on = ? WHERE id = ?",
                (today, subscriber_id),
            )
        else:
            conn.execute(
                "UPDATE shorts_subscribers SET daily_used = daily_used + 1 WHERE id = ?",
                (subscriber_id,),
            )
    else:
        conn.execute(
            "UPDATE shorts_subscribers SET shorts_used = shorts_used + 1 WHERE id = ?",
            (subscriber_id,),
        )
    conn.commit()


def _stripe_price_id(plan_id: str) -> str:
    p = PLANS.get(plan_id)
    if not p:
        return ""
    return os.getenv(p["stripe_price_env"], "").strip()


def _anonymous_email() -> str:
    """개인 이메일 없이 구독 행을 식별하기 위한 내부 ID (실제 개인정보 아님)."""
    return f"guest_{secrets.token_urlsafe(12)}@shorts.local"


def create_checkout_session(plan_id: str, email: str, success_url: str, cancel_url: str) -> str:
    if plan_id not in PLANS:
        raise ValueError("Invalid plan")

    if _is_free_plan(plan_id):
        return activate_free_subscriber(plan_id)

    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Valid email is required")

    price_id = _stripe_price_id(plan_id)
    if not stripe_enabled() or not price_id:
        if not DEV_SUBSCRIBE:
            raise ValueError("Payments are not configured yet. Try again later.")
        return _dev_activate(plan_id, email)

    import stripe

    stripe.api_key = STRIPE_SECRET
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"plan_id": plan_id, "email": email},
        allow_promotion_codes=True,
    )
    return session.url


def activate_free_subscriber(plan_id: str) -> str:
    """무료 스타터: 이메일·개인정보 없이 쿠키 토큰만 발급."""
    if not _is_free_plan(plan_id):
        raise ValueError("Invalid free plan")
    db_path = os.getenv("BOARD_DB_PATH", os.path.join(os.path.dirname(__file__), "board.db"))
    plan = PLANS[plan_id]
    token = secrets.token_urlsafe(32)
    with sqlite3.connect(db_path) as conn:
        ensure_tables(conn)
        _upsert_subscriber(
            conn,
            email=_anonymous_email(),
            plan_id=plan_id,
            quota=0,
            token=token,
            stripe_customer_id=None,
            stripe_subscription_id=None,
        )
    return f"{SITE_BASE_URL}/shorts/success?token={token}"


def _dev_activate(plan_id: str, email: str) -> str:
    """Stripe 미설정 시 개발용 즉시 구독."""
    db_path = os.getenv("BOARD_DB_PATH", os.path.join(os.path.dirname(__file__), "board.db"))
    plan = PLANS[plan_id]
    token = secrets.token_urlsafe(32)
    with sqlite3.connect(db_path) as conn:
        ensure_tables(conn)
        _upsert_subscriber(
            conn,
            email=email,
            plan_id=plan_id,
            quota=plan["quota"],
            token=token,
            stripe_customer_id=None,
            stripe_subscription_id=f"dev_{secrets.token_hex(8)}",
        )
    return f"{SITE_BASE_URL}/shorts/success?dev=1&token={token}"


def _upsert_subscriber(
    conn: sqlite3.Connection,
    *,
    email: str,
    plan_id: str,
    quota: int,
    token: str | None = None,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
) -> str:
    email = email.strip().lower()
    now = _now_iso()
    free = _is_free_plan(plan_id)
    end = _period_end(36500 if free else 30)
    today = _today_local()
    existing = conn.execute(
        "SELECT id, access_token FROM shorts_subscribers WHERE email = ?",
        (email,),
    ).fetchone()
    access = token or (existing["access_token"] if existing else secrets.token_urlsafe(32))
    if existing:
        if free:
            conn.execute(
                """
                UPDATE shorts_subscribers
                SET plan = ?, status = 'active', quota = ?, shorts_used = 0,
                    daily_used = 0, daily_used_on = ?,
                    period_start = ?, period_end = ?,
                    stripe_customer_id = COALESCE(?, stripe_customer_id),
                    stripe_subscription_id = COALESCE(?, stripe_subscription_id)
                WHERE email = ?
                """,
                (
                    plan_id,
                    quota,
                    today,
                    now,
                    end,
                    stripe_customer_id,
                    stripe_subscription_id,
                    email,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE shorts_subscribers
                SET plan = ?, status = 'active', quota = ?, shorts_used = 0,
                    period_start = ?, period_end = ?,
                    stripe_customer_id = COALESCE(?, stripe_customer_id),
                    stripe_subscription_id = COALESCE(?, stripe_subscription_id)
                WHERE email = ?
                """,
                (
                    plan_id,
                    quota,
                    now,
                    end,
                    stripe_customer_id,
                    stripe_subscription_id,
                    email,
                ),
            )
    else:
        conn.execute(
            """
            INSERT INTO shorts_subscribers
            (email, plan, status, access_token, stripe_customer_id, stripe_subscription_id,
             shorts_used, quota, period_start, period_end, created, daily_used, daily_used_on)
            VALUES (?, ?, 'active', ?, ?, ?, 0, ?, ?, ?, ?, 0, ?)
            """,
            (
                email,
                plan_id,
                access,
                stripe_customer_id,
                stripe_subscription_id,
                quota,
                now,
                end,
                now,
                today if free else "",
            ),
        )
    conn.commit()
    return access


def handle_stripe_webhook(payload: bytes, sig_header: str) -> None:
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("Webhook secret not configured")
    import stripe

    stripe.api_key = STRIPE_SECRET
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        _on_checkout_completed(data)
    elif etype == "customer.subscription.deleted":
        _set_subscription_status(data.get("id"), "canceled")
    elif etype in ("customer.subscription.updated", "invoice.payment_failed"):
        status = data.get("status", "active")
        if etype == "invoice.payment_failed":
            status = "past_due"
        _set_subscription_status(data.get("id"), status)


def _on_checkout_completed(session: dict) -> None:
    meta = session.get("metadata") or {}
    plan_id = meta.get("plan_id", "starter")
    email = (meta.get("email") or session.get("customer_email") or "").strip().lower()
    if not email or plan_id not in PLANS:
        return
    plan = PLANS[plan_id]
    import sqlite3 as _sqlite3

    db_path = os.getenv("BOARD_DB_PATH", os.path.join(os.path.dirname(__file__), "board.db"))
    with _sqlite3.connect(db_path) as conn:
        ensure_tables(conn)
        _upsert_subscriber(
            conn,
            email=email,
            plan_id=plan_id,
            quota=plan["quota"],
            stripe_customer_id=session.get("customer"),
            stripe_subscription_id=session.get("subscription"),
        )


def _set_subscription_status(stripe_sub_id: str | None, status: str) -> None:
    if not stripe_sub_id:
        return
    import sqlite3 as _sqlite3

    db_path = os.getenv("BOARD_DB_PATH", os.path.join(os.path.dirname(__file__), "board.db"))
    with _sqlite3.connect(db_path) as conn:
        ensure_tables(conn)
        conn.execute(
            "UPDATE shorts_subscribers SET status = ? WHERE stripe_subscription_id = ?",
            (status, stripe_sub_id),
        )
        conn.commit()


def fulfill_checkout_session(session_id: str) -> str | None:
    """Success 페이지: Stripe session 확인 후 access_token 반환."""
    if not session_id or not stripe_enabled():
        return None
    import stripe

    stripe.api_key = STRIPE_SECRET
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid" and session.status != "complete":
        return None
    meta = session.metadata or {}
    email = (meta.get("email") or session.customer_email or "").strip().lower()
    plan_id = meta.get("plan_id", "starter")
    if not email:
        return None
    import sqlite3 as _sqlite3

    db_path = os.getenv("BOARD_DB_PATH", os.path.join(os.path.dirname(__file__), "board.db"))
    with _sqlite3.connect(db_path) as conn:
        ensure_tables(conn)
        return _upsert_subscriber(
            conn,
            email=email,
            plan_id=plan_id,
            quota=PLANS.get(plan_id, PLANS["starter"])["quota"],
            stripe_customer_id=session.customer,
            stripe_subscription_id=session.subscription,
        )
