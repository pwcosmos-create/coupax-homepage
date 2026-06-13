import asyncio
import os
import json
from playwright.async_api import async_playwright

async def debug_pages():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()
        
        for pg in range(1, 5):
            url = f"https://www.njobapp.com/send?status=SUCCESS&sz=100&pg={pg}"
            await page.goto(url)
            await page.wait_for_timeout(5000)
            rows = await page.query_selector_all("table tbody tr")
            print(f"Page {pg}: {len(rows)} rows, URL: {url}")
            if len(rows) > 0:
                p_id = await rows[0].evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
                print(f"  First ID: {p_id}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_pages())
