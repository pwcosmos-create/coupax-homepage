"""CSRF, rate limit, client IP helpers."""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict

from flask import abort, request, session
import bleach
from markupsafe import Markup, escape

_POST_ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "strong",
        "em",
        "b",
        "i",
        "h2",
        "h3",
        "h4",
        "ul",
        "ol",
        "li",
        "blockquote",
        "a",
        "figure",
        "figcaption",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "hr",
        "div",
        "span",
    }
)
_POST_ALLOWED_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "loading", "width", "height"],
}

COMMENT_MIN_INTERVAL_SEC = max(
    5, int(os.getenv("COMMENT_MIN_INTERVAL_SEC", "30") or "30")
)
_comment_last_by_ip: dict[str, float] = defaultdict(float)


def client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "unknown")


def ensure_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validate_csrf_request() -> None:
    ensure_csrf_token()
    expected = session.get("csrf_token") or ""
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if request.is_json:
        body = request.get_json(silent=True) or {}
        if isinstance(body, dict):
            token = token or body.get("csrf_token")
    if not token or not secrets.compare_digest(str(token), str(expected)):
        abort(403)


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def nl2br(value) -> Markup:
    if value is None:
        return Markup("")
    return Markup(escape(str(value)).replace("\n", Markup("<br>")))


def safe_post_html(value) -> Markup:
    """게시글 본문: 허용 태그만 렌더, 그 외는 nl2br."""
    if value is None:
        return Markup("")
    text = str(value)
    if "<" not in text or ">" not in text:
        return nl2br(text)
    cleaned = bleach.clean(
        text,
        tags=list(_POST_ALLOWED_TAGS),
        attributes=_POST_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return Markup(cleaned)


def check_comment_rate_limit() -> bool:
    ip = client_ip()
    now = time.time()
    last = _comment_last_by_ip.get(ip, 0.0)
    if last and (now - last) < COMMENT_MIN_INTERVAL_SEC:
        return False
    _comment_last_by_ip[ip] = now
    if len(_comment_last_by_ip) > 5000:
        cutoff = now - 3600
        stale = [k for k, v in _comment_last_by_ip.items() if v < cutoff]
        for k in stale:
            del _comment_last_by_ip[k]
    return True


def blog_write_open() -> bool:
    return os.getenv("BLOG_WRITE_OPEN", "0").strip().lower() in ("1", "true", "yes")


# ── 비밀번호 해시 (글·댓글) ─────────────────────────────────────────────────────

from werkzeug.security import check_password_hash, generate_password_hash

_OFFICE_LOGIN_MAX_ATTEMPTS = max(
    3, int(os.getenv("OFFICE_LOGIN_MAX_ATTEMPTS", "8") or "8")
)
_OFFICE_LOGIN_WINDOW_SEC = max(
    60, int(os.getenv("OFFICE_LOGIN_WINDOW_SEC", "900") or "900")
)
_office_login_attempts: dict[str, list[float]] = defaultdict(list)


def is_password_hash(stored: str | None) -> bool:
    if not stored:
        return False
    return stored.startswith("pbkdf2:") or stored.startswith("scrypt:")


def hash_password(plain: str) -> str:
    return generate_password_hash(plain.strip())


def verify_password(plain: str, stored: str | None) -> bool:
    if not plain or stored is None:
        return False
    stored = str(stored)
    if is_password_hash(stored):
        return check_password_hash(stored, plain)
    return secrets.compare_digest(plain, stored)


def upgrade_password_if_legacy(
    db, table: str, row_id: int, plain: str, stored: str | None
) -> None:
    """기존 평문 비밀번호 로그인 성공 시 해시로 교체."""
    if not plain or stored is None or is_password_hash(stored):
        return
    if not secrets.compare_digest(plain, str(stored)):
        return
    db.execute(
        f"UPDATE {table} SET password=? WHERE id=?",
        (hash_password(plain), row_id),
    )


def check_office_login_allowed() -> bool:
    ip = client_ip()
    now = time.time()
    window_start = now - _OFFICE_LOGIN_WINDOW_SEC
    attempts = [t for t in _office_login_attempts[ip] if t >= window_start]
    _office_login_attempts[ip] = attempts
    return len(attempts) < _OFFICE_LOGIN_MAX_ATTEMPTS


def record_office_login_failure() -> None:
    _office_login_attempts[client_ip()].append(time.time())


def clear_office_login_failures() -> None:
    _office_login_attempts.pop(client_ip(), None)
