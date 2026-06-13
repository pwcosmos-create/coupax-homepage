import asyncio
import os
from playwright.async_api import async_playwright

async def debug_send_list():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        print(">>> SUCCESS 리스트로 이동 중...")
        await page.goto("https://www.njobapp.com/send?status=SUCCESS&sz=100")
        await page.wait_for_timeout(10000) # 충분히 대기
        
        # 스크린샷 캡처
        await page.screenshot(path="send_list_debug.png")
        
        # 테이블 내 텍스트 추출 확인
        rows = await page.query_selector_all("table tbody tr")
        print(f"발견된 행 수: {len(rows)}")
        
        if len(rows) > 0:
            html = await rows[0].inner_html()
            print("첫 번째 행 HTML 일부:")
            print(html[:500])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_send_list())
