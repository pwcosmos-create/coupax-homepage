## Security Playbook

This project contains operational scripts and integrations. Use this checklist to avoid leaking credentials.

### 1) Where secrets should live

- Keep credentials only in `.env` files on trusted machines.
- Commit only templates like `.env.example`.
- Never hardcode credentials in Python/HTML/JSON.

### 2) High-risk files to avoid committing

- `.env`
- `njob_session.json`
- `mybox_html.txt`
- `njob_send_search.html`
- Any debug exports containing cookies, CSRF tokens, or auth headers

### 3) Before commit checklist

1. Run:
   - `python scripts/check_secrets.py`
2. Ensure no real keys are in:
   - `*.py`, `*.html`, `*.json`, `*.md`
3. Confirm `.gitignore` still excludes local secret files.

### 4) If a secret was exposed

1. Rotate/reissue the key immediately.
2. Update `.env` with the new key.
3. Remove old leaked files from future tracking.
4. Re-run `python scripts/check_secrets.py`.

### 5) Current known sensitive categories

- Naver commerce credentials
- Dome API key
- WordPress app password
- Any session cookies or CSRF tokens

Keep this file updated whenever new integrations are added.
