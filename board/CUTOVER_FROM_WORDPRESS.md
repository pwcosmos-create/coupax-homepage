## WordPress -> Flask 컷오버 가이드 (B안)

### 1) 서버 배포

오라클 서버에 `board`를 배포합니다.

```bash
cd /home/opc/coupax-homepage/board
cp .env.example .env
vi .env
chmod +x deploy/setup_oracle.sh
./deploy/setup_oracle.sh
```

`.env`에서 반드시 수정:

- `FLASK_SECRET_KEY`
- `SITE_CONTACT_EMAIL`
- `ADSENSE_CLIENT` (애드센스에서 받은 client 값)

### 2) 앱 동작 확인

```bash
curl -I http://127.0.0.1:5001
curl -I http://127.0.0.1:5001/privacy
curl -I http://127.0.0.1:5001/robots.txt
curl -I http://127.0.0.1:5001/sitemap.xml
```

### 3) 도메인 전환

도메인 DNS A 레코드를 오라클 서버 공인 IP로 변경합니다.

- `coupax.co.kr` -> `<ORACLE_PUBLIC_IP>`
- `www.coupax.co.kr` -> `<ORACLE_PUBLIC_IP>`

### 4) HTTPS 적용

```bash
sudo dnf -y install certbot python3-certbot-nginx
sudo certbot --nginx -d coupax.co.kr -d www.coupax.co.kr
```

### 5) 애드센스 신청

1. 애드센스 사이트에 `https://coupax.co.kr` 추가
2. 심사용 코드가 이미 head에 들어가도록 `ADSENSE_CLIENT` 설정 확인
3. 검토 요청 제출

### 6) 승인률 높이는 운영 규칙

- 정책 페이지 4개 링크를 헤더/푸터 유지
- 최소 20개 이상 원본 글 유지
- 2주간 매일 신규/업데이트 콘텐츠 반영
- Search Console 색인 상태 주기 점검
