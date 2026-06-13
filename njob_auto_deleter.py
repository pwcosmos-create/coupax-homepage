import asyncio
import os
from playwright.async_api import async_playwright

TARGET_IDS = [
    "13153005855", "13153010555", "13153012183", "13161479197", "13166544241",
    "13171550082", "13176704244", "13181931995", "13181936226", "13181936458",
    "13187510031", "13187510467", "13187515901", "13196531321", "13196531664",
    "13201742622", "13207116863", "13207117686", "13207118214", "13212404267"
]

async def delete_targets():
    print("[N잡AI] 20개 실패 상품 삭제 자동화를 시작합니다...")
    deleted_count = 0
    
    async with async_playwright() as p:
        # headless=False 로 해서 사용자님이 삭제 과정을 직접 볼 수 있도록 함
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="njob_session.json" if os.path.exists("njob_session.json") else None)
        page = await context.new_page()

        # 알럿(Alert) 및 모달 자동 승인 처리
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        # Njobapp 전송 목록 페이지로 이동
        page_num = 1
        
        while page_num <= 10: # 최대 10페이지 검사
            print(f">>> [N잡AI] {page_num}페이지 검색 중...")
            await page.goto(f"https://www.njobapp.com/send?status=SUCCESS&sz=100&pg={page_num}")
            await page.wait_for_load_state("networkidle")
            
            # 테이블 행 추출
            rows = await page.query_selector_all("table tbody tr")
            if not rows:
                print("더 이상 상품이 없거나 로그인 세션이 만료되었습니다.")
                break

            found_in_page = []
            
            for row in rows:
                try:
                    product_id = await row.evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
                    if product_id in TARGET_IDS:
                        found_in_page.append(row)
                        # 해당 행의 체크박스 클릭
                        checkbox = await row.query_selector('td:nth-child(1) input[type="checkbox"]')
                        if checkbox:
                            await checkbox.check()
                except Exception as e:
                    pass
            
            if found_in_page:
                print(f"[{page_num}페이지] {len(found_in_page)}개의 삭제 대상 상품을 찾아 선택했습니다.")
                
                # 삭제 버튼 클릭 (버튼 텍스트가 '삭제' 또는 '선택삭제' 등일 수 있음)
                try:
                    delete_btn = await page.query_selector('button:has-text("삭제")')
                    if delete_btn:
                        await delete_btn.click()
                        print("삭제 버튼을 클릭했습니다.")
                        await page.wait_for_timeout(3000) # 삭제 처리 대기
                        deleted_count += len(found_in_page)
                    else:
                        print("⚠️ '삭제' 버튼을 찾을 수 없습니다.")
                        await page.screenshot(path="njob_delete_debug.png", full_page=True)
                except Exception as e:
                    print(f"삭제 과정에 에러 발생: {e}")
                    
                # 삭제 후 페이지가 갱신되므로 같은 페이지 번호를 다시 검사해야 할 수도 있지만, 
                # 안전하게 다음 페이지로 넘어갑니다.
            else:
                print(f"[{page_num}페이지] 대상 상품 없음.")
            
            page_num += 1

        print(f"[N잡AI] 자동화 완료! 총 탐색된 대상 개수 추정치: {deleted_count}개")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(delete_targets())
