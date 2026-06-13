import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

NJOB_ID = os.getenv("NJOB_ID")
NJOB_PW = os.getenv("NJOB_PW")
MEMORY_FILE = "njob_rl_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "processed_ids" not in data:
                data["processed_ids"] = []
            return data
    return {"processed_ids": []}

def save_memory(memory):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

async def optimize_njob_products(limit=100):
    memory = load_memory()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context(
            storage_state="njob_session.json", 
            viewport={'width': 1600, 'height': 1200}
        )
        page = await context.new_page()

        print(">>> [N잡AI] 고정밀 좌표 최적화 엔진 가동 중...")
        await page.goto("https://www.njobapp.com/send?status=SUCCESS")
        await page.wait_for_load_state("networkidle")

        # 페이지 노출 단위 100개로 변경 (이미 되어있을 수 있음)
        try:
            await page.wait_for_selector("select.form-control.input-sm", timeout=5000)
            await page.select_option("select.form-control.input-sm", "100")
            await page.wait_for_timeout(3000)
        except:
            pass

        success_count = 0
        processed_count = 0
        
        while processed_count < limit:
            # 1. 행 목록 확보
            rows = await page.query_selector_all("table tbody tr")
            found_this_loop = False

            for row in rows:
                if processed_count >= limit: break
                
                # 상품코드 추출
                try:
                    product_id = await row.evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
                except:
                    continue
                
                # 이미 처리된 상품 스킵 (RL 지능)
                if product_id in memory["processed_ids"]:
                    continue
                
                found_this_loop = True
                print(f"[{processed_count+1}/{limit}] ID:{product_id} 정밀 작업 시작...")
                
                # '상품편집' 버튼 클릭 (Force Click 사용)
                edit_btn = await row.query_selector('button:has-text("상품편집")')
                if not edit_btn:
                    continue
                
                await edit_btn.scroll_into_view_if_needed()
                # 좌표 기반 강제 클릭 (Force=True) - 레이어 간섭 무시
                await edit_btn.click(force=True, timeout=10000)
                
                # 2. 모달 제어
                try:
                    # 아주 넉넉하게 대기 (N잡 시스템 로딩 고려)
                    await page.wait_for_selector(".modal-content", timeout=25000)
                    await page.wait_for_timeout(5000) # 완전 로딩 대기
                    
                    # 카테고리 변경 스위치 강제 ON
                    # ID(#myonoffswitch_1) 대신 좌표나 라벨 클릭 시도
                    switch_label = await page.query_selector("label[for='myonoffswitch_1']")
                    if switch_label:
                        await switch_label.click(force=True)
                        print("  - 카테고리 스위치 ON")

                    # AI 버튼 강제 클릭
                    ai_btn = await page.query_selector('button:contains("AINain"), .layer_btn4, a:has-text("AI상품정보최적화")')
                    if ai_btn:
                        await ai_btn.click(force=True)
                        print("  - AI 분석 시작 (25초 대기)...")
                        await page.wait_for_timeout(25000)
                        
                        # 저장 버튼 클릭
                        save_btn = await page.query_selector('.modal-footer button.btn-primary:has-text("저장")')
                        if save_btn:
                            await save_btn.click(force=True)
                            print(f"  - ✅ {product_id} 저장 성공!")
                            success_count += 1
                            memory["processed_ids"].append(product_id)
                            save_memory(memory)
                        else:
                            print("  - ⚠️ 저장 버튼 찾지 못함")
                    else:
                        print("  - ⚠️ AI 버튼 찾지 못함")
                        
                except Exception as e:
                    print(f"  - ❌ 오류 발생: {e}")
                
                # 모달 닫기
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(2000)
                
                processed_count += 1
                break # 다음 순회를 위해 break
            
            if not found_this_loop:
                # 더 이상 페이지에 없으면 다음 페이지로
                next_btn = await page.query_selector("li.next:not(.disabled) a")
                if next_btn:
                    await next_btn.click(force=True)
                    await page.wait_for_timeout(5000)
                else:
                    break

        print(f"\n>>> [결과] 총 {success_count}건 성공 / 누적 {len(memory['processed_ids'])}건 처리 완료")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(optimize_njob_products(100))
