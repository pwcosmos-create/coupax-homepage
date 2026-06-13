import asyncio
import os
from playwright.async_api import async_playwright

async def find_unit_price_fields():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        # 푸드 아이템 (ABC 초콜릿)
        food_item_id = "64146485" 
        print(f">>> {food_item_id} (푸드) 편집 페이지 로드 중...")
        await page.goto(f"https://www.njobapp.com/mybox/getEditView?itemNo={food_item_id}")
        await page.wait_for_timeout(10000)
        
        # 페이지 전체 HTML 중 input name 들 수집
        inputs = await page.query_selector_all("input")
        input_names = []
        for inp in inputs:
            name = await inp.get_attribute("name")
            if name: input_names.append(name)
            
        print("발견된 Input Names:")
        print(input_names)
        
        # 단위가격 관련 키워드 검색
        labels = await page.query_selector_all("label")
        for lbl in labels:
            text = await lbl.inner_text()
            if "용량" in text or "단위" in text:
                html = await lbl.evaluate("el => el.parentElement.innerHTML")
                print(f"Label: {text}, Parent HTML: {html[:200]}")
                
        await page.screenshot(path="food_edit_view.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_unit_price_fields())
