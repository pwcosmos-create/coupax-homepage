"""로컬 PC 코드 스캐닝 및 서버 동기화 데몬 스크립트.
대표님의 PC에서 이 스크립트를 백그라운드로 실행해 두면,
가계부 앱 폴더의 변경 사항을 감지하여 서버의 젬마에게 리뷰를 요청합니다.
"""
from __future__ import annotations

import os
import time
import json
import urllib.request
from pathlib import Path

# 대표님의 로컬 작업 폴더 경로 (토스 앱 전체 감시)
WATCH_DIR = Path(r"c:\커셔\토스 앱")
# 실제 Oracle 클라우드 서버의 주소
SERVER_API_URL = "https://168.107.31.153/api/agents/office/local-code-sync"
SECRET_KEY = "super_secret_local_key"

def scan_and_upload():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 폴더 스캔 시작: {WATCH_DIR}")
    
    target_files = []
    if WATCH_DIR.exists():
        for ext in ["*.jsx", "*.js", "*.py"]:
            for path in WATCH_DIR.rglob(ext):
                # node_modules나 가상환경, 페이팔(paypal) 관련 파일은 스캔 제외
                if any(x in path.parts for x in ["node_modules", ".git", "venv", ".venv", "__pycache__"]) or "paypal" in path.name.lower():
                    continue
                target_files.append(path)
            
    if not target_files:
        print("대상 파일을 찾을 수 없습니다.")
        return
        
    # 가장 최근에 수정된 파일 1개만 샘플로 전송
    target_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_file = target_files[0]
    
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"파일 읽기 실패: {e!s}")
        return
        
    # 코드 스니펫 추출 (너무 길면 자름)
    snippet = content[:1500]
    
    payload = {
        "file_path": str(latest_file),
        "code_snippet": snippet
    }
    
    print(f"-> 전송 대상: {latest_file.name} (크기: {len(snippet)} bytes)")
    
    try:
        import ssl
        context = ssl._create_unverified_context()
        req = urllib.request.Request(
            SERVER_API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Local-Sync-Secret": SECRET_KEY,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30, context=context) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                print(f"[성공] 서버 젬마의 코드 리뷰 카드가 생성되었습니다: {data.get('title')}")
            else:
                print(f"[실패] 서버 응답 오류: {data}")
    except Exception as e:
        print(f"[전송 실패] 서버와 연결할 수 없습니다: {e!s}")

if __name__ == "__main__":
    print("========================================")
    print("▶ 로컬 코드 감시 데몬 실행 중...")
    print("========================================")
    
    # 무한 루프: 10분마다 1번씩 최근 수정된 코드를 전송
    while True:
        scan_and_upload()
        time.sleep(600)  # 600초(10분) 대기
