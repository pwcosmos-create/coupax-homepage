# ads.txt (애드센스) 점검

대시보드에 **「찾을 수 없음」**이면 크롤러가 유효한 한 줄을 받지 못한 경우가 많습니다.

## 1. 서버 `.env`

```bash
ADSENSE_CLIENT=ca-pub-XXXXXXXXXXXXXXXX
```

(애드센스에 표시되는 **게시자 ID**와 동일해야 합니다.)

설정 후:

```bash
sudo systemctl restart board
```

## 2. 응답 확인

```bash
curl -sS -i https://coupax.co.kr/ads.txt
```

- **HTTP 200** 이고 본문에  
  `google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0`  
  형태가 한 줄 있어야 합니다.
- **404**이면 아직 `ADSENSE_CLIENT`가 비었거나 앱이 재시작되지 않은 경우가 많습니다.

## 3. Nginx

저장소의 `deploy/nginx-coupax-ssl.conf` / `000-coupax.co.kr.nginx` 에 `location = /ads.txt` 프록시 블록이 있습니다.  
서버 설정과 다르면 동일 블록을 반영한 뒤 `sudo nginx -t && sudo systemctl reload nginx` 하세요.
