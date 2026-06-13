import asyncio
import os
from playwright.async_api import async_playwright

async def debug_fail_list():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        print(">>> FAIL 리스트로 이동 중...")
        await page.goto("https://www.njobapp.com/send?status=FAIL&sz=100")
        await page.wait_for_timeout(10000)
        
        await page.screenshot(path="fail_list_debug.png")
        
        rows = await page.query_selector_all("table tbody tr")
        print(f"발견된 FAIL 행 수: {len(rows)}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_fail_list())
