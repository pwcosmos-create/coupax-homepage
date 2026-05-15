## Adsense Execution Guide (Coupax)

### 1) Set environment variables

Open `C:/dev/coupax홈페이지/.env` and add:

- `WP_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`
- `SITE_CONTACT_EMAIL`

Use `.env.example` as reference.

### 2) Run essential page setup

```bash
python wp_adsense_manager.py
```

This script will create or update:

- 사이트 소개 (About)
- 문의하기 (Contact)
- 개인정보처리방침 (Privacy Policy)
- 이용약관 (Terms)

### 3) (Optional) Publish one long-form sample post

```bash
python wp_adsense_manager.py --create-sample-post
```

### 4) Add Adsense script to WordPress head

In WordPress admin:

1. Install "WPCode" or "Insert Headers and Footers"
2. Paste Adsense script in Header
3. Save and clear cache

### 5) Submit for Adsense review

In Adsense:

1. Add site: `https://coupax.co.kr`
2. Verify ownership
3. Click "Request review"

### 6) After submission (first 14 days)

- Publish 1 original post/day
- Update 1 old post/day with fresh data
- Keep policy pages visible in footer/header

---

## Important

Google approval is manual and cannot be guaranteed by script.
This automation prepares the site for approval, but final approval depends on policy review.
