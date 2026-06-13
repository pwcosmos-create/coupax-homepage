import asyncio
import json
import os
import pandas as pd
from playwright.async_api import async_playwright
from datetime import datetime

MEMORY_FILE = 'njob_rl_memory.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_ids": []}

async def fetch_next_batch(max_pages=10):
    memory = load_memory()
    new_items = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        for pg in range(1, max_pages + 1):
            print(f">>> {pg}페이지에서 새로운 상품 추출 중...")
            await page.goto(f"https://www.njobapp.com/send?status=SUCCESS&sz=100&pg={pg}")
            await page.wait_for_timeout(3000) # 로딩 대기
            
            rows = await page.query_selector_all("table tbody tr")
            if not rows: break
            
            for row in rows:
                try:
                    p_id = await row.evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
                    p_name = await row.evaluate('r => r.querySelector("td:nth-child(4)").innerText.trim()')
                except:
                    continue
                
                if p_id not in memory["processed_ids"]:
                    new_items.append({"id": p_id, "name": p_name})
                    if len(new_items) >= 50: break
            
            if len(new_items) >= 50: break
        
        await browser.close()
        return new_items

if __name__ == "__main__":
    items = asyncio.run(fetch_next_batch())
    with open("njob_next_batch.json", "w", encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"✅ {len(items)}건의 새로운 상품 데이터를 njob_next_batch.json에 저장했습니다.")
