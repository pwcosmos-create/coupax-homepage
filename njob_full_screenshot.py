import asyncio
import os
from playwright.async_api import async_playwright

async def full_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json", viewport={"width": 1280, "height": 3000})
        page = await context.new_page()
        
        food_item_id = "64146485"
        await page.goto(f"https://www.njobapp.com/mybox/getEditView?itemNo={food_item_id}")
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path="food_edit_full.png", full_page=True)
        
        # '단위가격' 키워드가 HTML에 있는지 확인
        content = await page.content()
        if "단위가격" in content:
            print("Found '단위가격' in HTML!")
            # 해당 텍스트 근처의 input들 찾기
            # (생략: 그냥 스크린샷으로 확인)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(full_screenshot())
