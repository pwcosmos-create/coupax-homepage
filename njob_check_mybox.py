import asyncio
import os
from playwright.async_api import async_playwright

async def check_mybox():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        print(">>> 마이박스로 이동 중...")
        await page.goto("https://www.njobapp.com/mybox")
        await page.wait_for_timeout(10000)
        
        await page.screenshot(path="mybox_debug.png")
        
        rows = await page.query_selector_all("table tbody tr")
        print(f"마이박스 행 수: {len(rows)}")
        
        if len(rows) > 0:
            p_id = await rows[0].evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
            print(f"첫 번째 상품 ID: {p_id}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_mybox())
