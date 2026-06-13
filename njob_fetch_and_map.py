import asyncio
import os
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# 카테고리 매퍼 임포트
from njob_category_mapper import predict_category, load_memory, save_memory, _rl_learn

MEMORY_FILE = 'njob_rl_memory.json'

async def get_all_item_nos(context):
    """전송 성공 목록에서 itemNo 전체 수집"""
    page = await context.new_page()
    item_nos = []

    print("[1] 전송 성공 목록에서 상품번호 수집...")
    await page.goto("https://www.njobapp.com/send?status=SUCCESS")
    await page.wait_for_load_state("networkidle")

    # 페이지당 100개 설정
    try:
        await page.wait_for_selector("select.form-control.input-sm", timeout=5000)
        await page.select_option("select.form-control.input-sm", "100")
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    page_num = 1
    while True:
        await page.wait_for_load_state("networkidle")

        nos = await page.evaluate("""
            () => {
                const nos = [];
                document.querySelectorAll('[onclick]').forEach(el => {
                    const oc = el.getAttribute('onclick') || '';
                    if (!oc.includes('editView')) return;
                    const m = oc.match(/editView\\(['"]?(\\d+)['"]?\\)/);
                    if (m) nos.push(m[1]);
                });
                return [...new Set(nos)];
            }
        """)

        if not nos:
            break

        item_nos.extend(nos)
        print(f"  [페이지 {page_num}] {len(nos)}개 (누적: {len(item_nos)}개)")

        next_btn = await page.query_selector('li.next:not(.disabled) a, .pagination li:not(.disabled) a[aria-label="Next"]')
        if not next_btn:
            break
        await next_btn.click()
        await page.wait_for_timeout(1500)
        page_num += 1

    await page.close()
    print(f"  총 {len(item_nos)}개 상품번호 수집 완료")
    return list(dict.fromkeys(item_nos))  # 중복 제거

async def get_product_detail(context, item_no):
    """getEditView에서 상품명 + 현재 카테고리 파싱"""
    page = await context.new_page()
    try:
        await page.goto(f"https://www.njobapp.com/mybox/getEditView?itemNo={item_no}")
        await page.wait_for_load_state("networkidle")

        fields = await page.evaluate("""
            () => {
                const get = name => {
                    const el = document.querySelector(`[name="${name}"]`);
                    return el?.value || '';
                };
                return {
                    itemName: get('itemName'),
                    categoryVal: get('categoryVal'),
                };
            }
        """)
        return {
            "itemNo": item_no,
            "productName": fields.get("itemName", "").strip(),
            "currentCategory": fields.get("categoryVal", "").strip(),
        }
    except Exception as e:
        return {"itemNo": item_no, "productName": "", "currentCategory": ""}
    finally:
        await page.close()

async def fetch_products():
    """njobapp 전송 성공 목록에서 전체 상품 수집"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")

        # 1. 상품번호 수집
        item_nos = await get_all_item_nos(context)
        if not item_nos:
            await browser.close()
            return []

        # 2. 각 상품번호로 상품명 수집 (병렬 5개씩)
        print(f"\n[2] {len(item_nos)}개 상품 상세정보 수집 중...")
        products = []
        batch_size = 5

        for i in range(0, len(item_nos), batch_size):
            batch = item_nos[i:i+batch_size]
            tasks = [get_product_detail(context, no) for no in batch]
            results = await asyncio.gather(*tasks)
            products.extend([r for r in results if r["productName"]])
            print(f"  {min(i+batch_size, len(item_nos))}/{len(item_nos)} 완료...")
            await asyncio.sleep(0.3)

        await browser.close()

    print(f"\n[완료] 총 {len(products)}개 상품 수집")
    return products

def map_categories(products):
    """수집된 상품에 카테고리 매핑 + RL 학습"""
    memory = load_memory()
    results = []
    unknown_count = 0

    print(f"\n[2] {len(products)}개 상품 카테고리 매핑 중...")

    for i, item in enumerate(products, 1):
        name = item.get('productName', '')
        if not name:
            continue

        category, seId, status = predict_category(name, memory)

        results.append({
            "상품번호": item.get('itemNo', ''),
            "상품명": name,
            "카테고리경로": category,
            "seId": str(seId),
            "매핑상태": status
        })

        # RL 학습 (New Learned인 경우)
        if status == "New Learned" and seId:
            _rl_learn(name, category, seId, memory)

        if status == "Unknown (Check Required)":
            unknown_count += 1

        if i % 100 == 0:
            print(f"  {i}/{len(products)} 처리 완료...")

    # RL 통계 업데이트
    reward = len([r for r in results if r['매핑상태'] != 'Unknown (Check Required)'])
    memory.setdefault('feedback', {})
    memory['feedback']['reward_count'] = memory['feedback'].get('reward_count', 0) + reward
    memory['feedback']['penalty_count'] = memory['feedback'].get('penalty_count', 0) + unknown_count
    memory['feedback']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    save_memory(memory)

    print(f"  매핑 완료: {reward}건 성공 / {unknown_count}건 Unknown")
    print(f"  RL 메모리 키워드: {len(memory['keywords'])}개")
    return results

def save_excel(results):
    """결과 엑셀 저장"""
    df = pd.DataFrame(results)
    df['seId'] = df['seId'].astype(str).replace('nan', '')

    output_file = f"njob_category_result_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='openpyxl')
    df.to_excel(writer, index=False)

    ws = writer.sheets['Sheet1']
    # seId 열 텍스트 형식 유지
    seId_col = df.columns.get_loc('seId') + 1
    for row in ws.iter_rows(min_row=2, min_col=seId_col, max_col=seId_col):
        for cell in row:
            cell.number_format = '@'
    writer.close()

    print(f"\n[저장] {output_file} ({len(results)}행)")

    # Unknown 목록 별도 저장
    unknown_df = df[df['매핑상태'] == 'Unknown (Check Required)']
    if len(unknown_df) > 0:
        unk_file = f"njob_unknown_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
        unknown_df.to_excel(unk_file, index=False)
        print(f"[Unknown] {unk_file} ({len(unknown_df)}건) - 수동 확인 필요")

    return output_file

async def main():
    # 세션 확인
    if not os.path.exists("njob_session.json"):
        print("[오류] njob_session.json 없음. njob_login.py 먼저 실행하세요.")
        return

    # 1. 상품 수집
    products = await fetch_products()
    if not products:
        print("[오류] 수집된 상품 없음")
        return

    # 2. 카테고리 매핑
    results = map_categories(products)

    # 3. 엑셀 저장
    save_excel(results)

if __name__ == "__main__":
    asyncio.run(main())
