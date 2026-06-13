import asyncio
import json
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
NJOB_ID = os.getenv("NJOB_ID")
NJOB_PW = os.getenv("NJOB_PW")

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # ── 1. 자동 로그인 ────────────────────────────────────────────────────
        print("[1] 로그인 중...")
        await page.goto("https://www.njobapp.com/login")
        await page.fill('input[placeholder="아이디"]', NJOB_ID)
        await page.fill('input[placeholder="비밀번호"]', NJOB_PW)
        await page.click('button:has-text("로그인")')
        await page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
        await context.storage_state(path="njob_session.json")
        print("[1] 로그인 완료")

        # ── 2. 카테고리 API 직접 호출 ─────────────────────────────────────────
        print("[2] 카테고리 API 호출 중...")
        cat_result = {}

        # sort1 목록 가져오기
        resp = await page.request.get("https://www.njobapp.com/getCategoryNjobPc?upper=")
        if resp.ok:
            cat_result["sort1"] = await resp.json()
            print(f"    sort1 응답: {str(cat_result['sort1'])[:200]}")
        else:
            print(f"    sort1 API 실패: {resp.status}")

        # ── 3. 마이박스에서 상품편집 모달 열기 ──────────────────────────────
        print("[3] 마이박스 이동...")
        await page.goto("https://www.njobapp.com/mybox")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # 첫 번째 상품 편집 버튼 클릭
        edit_btn = await page.query_selector('button:has-text("상품편집"), a:has-text("편집"), .btn-edit')
        if not edit_btn:
            print("[3] 마이박스에 상품 없음, 전송 성공 목록 시도...")
            await page.goto("https://www.njobapp.com/send?status=SUCCESS")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)
            edit_btn = await page.query_selector('button:has-text("상품편집")')

        modal_structure = {}
        if edit_btn:
            await edit_btn.click()
            print("[3] 편집 모달 로딩 대기...")
            try:
                await page.wait_for_selector(".modal.in, .modal.show, [role='dialog']", timeout=15000)
                await page.wait_for_timeout(3000)
            except Exception:
                await page.wait_for_timeout(5000)

            # 모달 HTML 전체 구조 덤프
            modal_html = await page.evaluate("""
                () => {
                    const modal = document.querySelector('.modal.in, .modal.show, [role="dialog"], .modal-dialog');
                    return modal ? modal.innerHTML.substring(0, 8000) : 'MODAL NOT FOUND';
                }
            """)
            with open("njob_modal_html.txt", "w", encoding="utf-8") as f:
                f.write(modal_html)
            print("[3] 모달 HTML -> njob_modal_html.txt 저장")

            # 모달 내 필드 수집
            modal_structure = await page.evaluate("""
                () => {
                    const modal = document.querySelector('.modal.in, .modal.show, [role="dialog"]');
                    if (!modal) return { error: 'no modal' };
                    const result = { inputs: [], selects: [], buttons: [] };

                    modal.querySelectorAll('input').forEach(el => {
                        result.inputs.push({ name: el.name, id: el.id, placeholder: el.placeholder, type: el.type, value: el.value.slice(0,50) });
                    });
                    modal.querySelectorAll('select').forEach(el => {
                        const opts = Array.from(el.options).map(o => ({ v: o.value, t: o.text.trim() }));
                        result.selects.push({ name: el.name, id: el.id, options: opts.slice(0,10) });
                    });
                    modal.querySelectorAll('button').forEach(el => {
                        result.buttons.push({ text: el.innerText.trim().slice(0,30), class: el.className });
                    });
                    return result;
                }
            """)
            print(f"[3] 모달 inputs: {len(modal_structure.get('inputs',[]))}개, selects: {len(modal_structure.get('selects',[]))}개, buttons: {len(modal_structure.get('buttons',[]))}개")

            # sort1~sort4 확인
            for sel in modal_structure.get('selects', []):
                if 'sort' in sel.get('name','') or 'sort' in sel.get('id','') or 'category' in sel.get('id','').lower():
                    print(f"    카테고리 select: {sel['name'] or sel['id']} -> {sel['options'][:5]}")

            await page.keyboard.press("Escape")
        else:
            print("[3] 편집 버튼 없음")

        # ── 4. getCategoryNjobPc 전체 탐색 ───────────────────────────────────
        print("[4] 카테고리 전체 구조 수집 중...")
        full_tree = {}

        resp1 = await page.request.get("https://www.njobapp.com/getCategoryNjobPc")
        if resp1.ok:
            raw = await resp1.json()
            # 응답 형식: {'data': {'code': 'name', ...}} 또는 [{'code':..,'name':..}]
            if isinstance(raw, dict) and "data" in raw:
                sort1_dict = raw["data"]
            elif isinstance(raw, dict):
                sort1_dict = raw
            else:
                sort1_dict = {item.get("code", i): item.get("name", str(item)) for i, item in enumerate(raw)}

            full_tree["sort1"] = sort1_dict
            print(f"    sort1 {len(sort1_dict)}개:")
            for code, name in sort1_dict.items():
                print(f"      {code}: {name}")

            # 각 sort1에 대해 sort2 조회
            for code, name in sort1_dict.items():
                if not code:
                    continue
                resp2 = await page.request.get(f"https://www.njobapp.com/getCategoryNjobPc?upper={code}")
                if resp2.ok:
                    try:
                        raw2 = await resp2.json()
                        if isinstance(raw2, dict) and "data" in raw2:
                            sort2_dict = raw2["data"]
                        elif isinstance(raw2, dict):
                            sort2_dict = raw2
                        else:
                            sort2_dict = {item.get("code", i): item.get("name", str(item)) for i, item in enumerate(raw2)}
                        full_tree[f"{code}_sort2"] = sort2_dict
                        print(f"    [{name}] sort2 {len(sort2_dict)}개: {list(sort2_dict.items())[:3]}")

                        # sort3 샘플 (첫 번째 항목만)
                        for code2, name2 in list(sort2_dict.items())[:1]:
                            resp3 = await page.request.get(f"https://www.njobapp.com/getCategoryNjobPc?upper={code2}")
                            if resp3.ok:
                                raw3 = await resp3.json()
                                if isinstance(raw3, dict) and "data" in raw3:
                                    sort3_dict = raw3["data"]
                                else:
                                    sort3_dict = raw3
                                full_tree[f"{code2}_sort3"] = sort3_dict
                                print(f"      [{name2}] sort3: {list(sort3_dict.items())[:3] if isinstance(sort3_dict, dict) else sort3_dict[:3]}")
                            await page.wait_for_timeout(100)
                    except Exception as e:
                        print(f"    [{name}] sort2 파싱 오류: {e}")
                await page.wait_for_timeout(200)
        else:
            print(f"    getCategoryNjobPc 실패 ({resp1.status})")

        # ── 5. 결과 저장 ──────────────────────────────────────────────────────
        result = {
            "modal_structure": modal_structure,
            "category_tree": full_tree,
        }
        with open("njob_structure.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("\n[완료] njob_structure.json 저장 완료")

        await page.wait_for_timeout(3000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(explore())
