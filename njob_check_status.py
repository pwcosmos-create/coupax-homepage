import asyncio
import os
import json
from playwright.async_api import async_playwright

async def check_all_statuses():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        statuses = ["READY", "SUCCESS", "FAIL"]
        for st in statuses:
            url = f"https://www.njobapp.com/send?status={st}&sz=100"
            await page.goto(url)
            await page.wait_for_timeout(5000)
            rows = await page.query_selector_all("table tbody tr")
            print(f"Status {st}: {len(rows)} rows")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_all_statuses())
