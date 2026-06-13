import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

NJOB_ID = os.getenv("NJOB_ID")
NJOB_PW = os.getenv("NJOB_PW")
STORAGE_STATE = "njob_session.json"

async def login_njob(page):
    """N-Job App(njobapp.com) 로그인 처리"""
    print(f"[N잡AI] '{NJOB_ID}' 계정으로 로그인 시도 중...")
    
    # 1. 로그인 페이지 접속
    await page.goto("https://www.njobapp.com/login")
    
    # 2. 아이디 입력
    await page.fill('input[placeholder="아이디"]', NJOB_ID)
    
    # 3. 비밀번호 입력
    await page.fill('input[placeholder="비밀번호"]', NJOB_PW)
    
    # 4. 로그인 버튼 클릭
    await page.click('button:has-text("로그인")')
    
    # 5. 로그인 성공 여부 확인
    try:
        # 로그인 후 나타나는 사용자 이름 또는 특징적인 요소 대기
        await page.wait_for_selector('text=박원기', timeout=15000)
        print("[N잡AI] ✅ 로그인 성공!")
        return True
    except Exception as e:
        print(f"[N잡AI] ❌ 로그인 확인 지연 또는 실패: {e}")
        await page.screenshot(path="login_error.png")
        return False

async def main():
    if not NJOB_ID or not NJOB_PW:
        print("[N잡AI] ⚠️ .env 파일에 NJOB_ID와 NJOB_PW를 설정해주세요.")
        return

    async with async_playwright() as p:
        # 브라우저 실행 (사용자가 볼 수 있도록 headless=False 설정 가능)
        browser = await p.chromium.launch(headless=True)
        
        # 세션 상태가 있으면 로드
        context_args = {}
        if os.path.exists(STORAGE_STATE):
            context_args["storage_state"] = STORAGE_STATE
            print(f"[N잡AI] 기존 세션 정보({STORAGE_STATE})를 로드합니다.")

        context = await browser.new_context(**context_args)
        page = await context.new_page()

        # 로그인 시도
        success = await login_njob(page)
        
        if success:
            # 세션 상태 저장 (로그인 성공 시)
            await context.storage_state(path=STORAGE_STATE)
            print(f"[N잡AI] 세션 정보가 '{STORAGE_STATE}'에 저장되었습니다.")
            
            # 대시보드 데이터 수집 또는 다음 작업 수행
            print("[N잡AI] 대시보드 진입 대기...")
            await asyncio.sleep(2)
            
            # TODO: 여기에 상품 전송 현황 파악이나 주문 수집 로직 추가 예정
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
