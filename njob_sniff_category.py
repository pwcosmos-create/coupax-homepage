import asyncio
import json
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
NJOB_ID = os.getenv("NJOB_ID")
NJOB_PW = os.getenv("NJOB_PW")

captured = []

async def sniff():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 모든 네트워크 요청 캡처
        async def on_request(request):
            if "category" in request.url.lower() or "Category" in request.url:
                captured.append({"type": "REQUEST", "url": request.url, "method": request.method, "post": request.post_data})
                print(f"[REQ] {request.method} {request.url}")
                if request.post_data:
                    print(f"      POST: {request.post_data}")

        async def on_response(response):
            if "category" in response.url.lower() or "Category" in response.url:
                try:
                    body = await response.text()
                    captured.append({"type": "RESPONSE", "url": response.url, "status": response.status, "body": body[:500]})
                    print(f"[RES] {response.status} {response.url}")
                    print(f"      BODY: {body[:300]}")
                except Exception:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        # 로그인
        await page.goto("https://www.njobapp.com/login")
        await page.fill('input[placeholder="아이디"]', NJOB_ID)
        await page.fill('input[placeholder="비밀번호"]', NJOB_PW)
        await page.click('button:has-text("로그인")')
        await page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
        print("[OK] 로그인 완료\n")

        # 마이박스로 이동 - 카테고리 드롭다운이 있는 페이지
        await page.goto("https://www.njobapp.com/mybox")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # JS에서 카테고리 관련 함수 찾기
        cat_js = await page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script')).map(s => s.innerText);
                return scripts.filter(s => s.includes('Category') || s.includes('category') || s.includes('sort1')).join('\\n---\\n').slice(0, 3000);
            }
        """)
        with open("njob_category_js.txt", "w", encoding="utf-8") as f:
            f.write(cat_js)
        print("[OK] 카테고리 관련 JS -> njob_category_js.txt\n")

        # 상품편집 모달 열기 시도 - 전송 성공 목록
        await page.goto("https://www.njobapp.com/send?status=SUCCESS")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        edit_btn = await page.query_selector('button:has-text("상품편집")')
        if edit_btn:
            print("[OK] 상품편집 버튼 클릭...")
            await edit_btn.click()
            await page.wait_for_timeout(5000)

            # 모달 내 카테고리 선택 시도
            sort1_sel = await page.query_selector('#sort1, select[name="sort1"], .select1')
            if sort1_sel:
                # sort1 옵션 목록
                opts = await page.evaluate("""
                    () => {
                        const sel = document.querySelector('#sort1, select[name="sort1"], .select1');
                        if (!sel) return [];
                        return Array.from(sel.options).map(o => ({v: o.value, t: o.text.trim()}));
                    }
                """)
                print(f"\n[sort1 옵션 {len(opts)}개]")
                for o in opts:
                    print(f"  {o['v']}: {o['t']}")

                # 첫 번째 유효 옵션 선택 -> sort2 로드 트리거
                valid = [o for o in opts if o['v']]
                if valid:
                    print(f"\n[sort1 선택: {valid[0]}]")
                    await page.select_option('#sort1, select[name="sort1"], .select1', valid[0]['v'])
                    await page.wait_for_timeout(2000)  # sort2 로드 대기

                    sort2_opts = await page.evaluate("""
                        () => {
                            const sel = document.querySelector('#sort2, select[name="sort2"], .select2');
                            if (!sel) return [];
                            return Array.from(sel.options).map(o => ({v: o.value, t: o.text.trim()}));
                        }
                    """)
                    print(f"[sort2 옵션 {len(sort2_opts)}개]: {sort2_opts[:5]}")
            else:
                print("[!] sort1 select 없음")

            await page.keyboard.press("Escape")
        else:
            print("[!] 상품편집 버튼 없음")

        # 캡처된 요청 저장
        with open("njob_category_requests.json", "w", encoding="utf-8") as f:
            json.dump(captured, f, ensure_ascii=False, indent=2)
        print(f"\n[완료] 카테고리 요청 {len(captured)}건 -> njob_category_requests.json")

        await page.wait_for_timeout(2000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(sniff())
