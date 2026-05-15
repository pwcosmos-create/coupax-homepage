## Oracle Cloud(OCI) 배포 가이드

이 문서는 `board` Flask 앱을 Oracle Linux 서버에 배포하는 최소 절차입니다.

### 1) 서버에 코드 업로드

`/home/opc/coupax-homepage/board` 경로에 현재 `board` 폴더를 올립니다.

### 2) 환경 변수 파일 준비

```bash
cd /home/opc/coupax-homepage/board
cp .env.example .env
vi .env
```

필수 확인값:

- `FLASK_SECRET_KEY`: 충분히 긴 랜덤 문자열로 변경
- `BOARD_DB_PATH`: 기본값 유지 가능
- `FLASK_DEBUG=false` 유지

### 3) 자동 설치 실행

```bash
cd /home/opc/coupax-homepage/board
chmod +x deploy/setup_oracle.sh
./deploy/setup_oracle.sh
```

스크립트가 다음을 수행합니다.

- 시스템 패키지 설치 (`python3`, `nginx`, 빌드도구)
- 가상환경 생성 및 `requirements.txt` 설치
- `systemd` 서비스 등록/기동 (`board.service`)
- Nginx 설정 반영 (`deploy/nginx-board.conf`)

### 4) 방화벽 열기 (필요 시)

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

OCI 보안 목록(Security List) 또는 NSG에서도 80/443 포트를 허용해야 합니다.

### 5) 상태 확인

```bash
sudo systemctl status board
sudo systemctl status nginx
curl -I http://127.0.0.1:5001
curl -I http://<SERVER_PUBLIC_IP>
```

### 6) HTTPS 적용(권장)

도메인을 서버 IP로 연결한 뒤 certbot으로 인증서를 발급하세요.

```bash
sudo dnf -y install certbot python3-certbot-nginx
sudo certbot --nginx -d coupax.co.kr -d www.coupax.co.kr
```

---

문제 발생 시 로그 확인:

```bash
journalctl -u board -f
sudo tail -f /var/log/nginx/error.log
```

---

### Windows 로컬에서 코드만 갱신 배포

이 PC에 Git 원격이 없거나, 바로 `scp`로 올릴 때:

1. **배포 zip 만들기** (`.env`, `board.db`, `.venv` 제외)

```powershell
cd board\deploy
.\publish_windows.ps1
```

`board\coupax-board-deploy.zip` 이 생성됩니다.

2. **서버로 복사 후 압축 해제·재기동** (경로는 `board.service`의 `WorkingDirectory`와 동일하게)

```bash
scp coupax-board-deploy.zip opc@<SERVER_PUBLIC_IP>:/home/opc/
ssh opc@<SERVER_PUBLIC_IP>
cd /home/opc/coupax-homepage/board
unzip -o ~/coupax-board-deploy.zip
sudo systemctl restart board
sudo systemctl status board --no-pager
```

`requirements.txt`가 바뀌었다면 서버에서 한 번 더:

```bash
cd /home/opc/coupax-homepage/board
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart board
```
