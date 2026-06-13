import asyncio
import os
import json
import pandas as pd
from playwright.async_api import async_playwright
from datetime import datetime

# .env 로드
from dotenv import load_dotenv
load_dotenv()

MEMORY_FILE = 'njob_rl_memory.json'
CATEGORY_TREE_FILE = 'njob_category_tree.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "processed_ids" not in data: data["processed_ids"] = []
            return data
    return {"keywords": {}, "feedback": {"reward_count": 0, "penalty_count": 0}, "processed_ids": []}

def save_memory(memory):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

# 카테고리 트리 로드
_cat_tree = None
def load_category_tree():
    global _cat_tree
    if _cat_tree is None and os.path.exists(CATEGORY_TREE_FILE):
        with open(CATEGORY_TREE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _cat_tree = data.get('flat_list', [])
    return _cat_tree or []

def search_category_tree(keywords):
    tree = load_category_tree()
    normalized = [k for k in keywords if len(k) >= 2]
    for kw in normalized:
        for node in tree:
            if kw == node.get('name', '') and node.get('seId'):
                return node['path'], node['seId']
    for kw in normalized:
        for node in tree:
            if kw in node.get('name', '') and node.get('seId'):
                return node['path'], node['seId']
    return None, None

def predict_category(product_name, memory):
    name = product_name
    for kw, entry in memory['keywords'].items():
        if kw in name:
            return entry.get('path', ''), entry.get('seId', ''), "Verified (RL Memory)"

    RULES = [
        (["색연필", "플러스펜", "수성펜", "샤프", "무한연필", "펜", "수정테이프", "화이트", "노트", "일기", "메모", "컴퍼스", "제도용품"], "문구 > 사무용품 > 필기도구", "1001201100"),
        (["바둑", "장기", "보드게임"], "취미/도서 > 완구/피규어 > 보드게임", "1307020300"),
        (["화분", "식물", "표지", "이름표", "재배", "원예", "가드닝"], "취미/도서 > 원예/식물 > 화분용품 > 화분", "1312080000"),
        (["리본", "포장"], "생활용품 > 공구 > 포장용품 > 리본", "12161905"),
        (["경첩", "못", "피스", "공구"], "생활용품 > 공구 > DIY자재 > 경첩", "1216010000"),
        (["가방", "스쿨백", "필통", "쥬쥬"], "패션잡화 > 가방 > 아동용가방", "0121080000"),
        (["조명", "태양광", "정원등", "LED"], "생활용품 > 조명 > 실외조명", "1212000000"),
        (["캠핑", "앞접시", "플레이팅"], "스포츠/레저 > 캠핑 > 캠핑취사용품", "1421060000"),
        (["셔틀콕", "배드민턴"], "스포츠/레저 > 배드민턴 > 배드민턴라켓", "1408040000"),
        (["양말", "덧신"], "패션잡화 > 양말 > 양말세트", "0123010500"),
        (["드라이버", "복스알"], "생활용품 > 공구 > 수공구 > 드라이버", "1216020100"),
    ]

    for keywords, path, seId in RULES:
        if any(k in name for k in keywords):
            return path, seId, "New Learned"

    tree_path, tree_seId = search_category_tree(name.split())
    if tree_seId: return tree_path, tree_seId, "Tree Search"
    return "기타", "", "Unknown"

async def autonomic_unlimited_relay():
    memory = load_memory()
    total_processed_this_session = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()

        print(f"[{datetime.now()}] 🚀 N-Job 자율주행 최적화 릴레이 가동 (무제한)")
        
        while True:
            # 1. 미처리 상품 20개 추출
            batch_20 = []
            page_num = 1
            max_pages_to_search = 5
            
            while len(batch_20) < 20 and page_num <= max_pages_to_search:
                await page.goto(f"https://www.njobapp.com/send?status=SUCCESS&sz=100&pg={page_num}")
                await page.wait_for_load_state("networkidle")
                
                rows = await page.query_selector_all("table tbody tr")
                if not rows: break

                for row in rows:
                    p_id = await row.evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
                    p_name = await row.evaluate('r => r.querySelector("td:nth-child(4)").innerText.trim()')
                    
                    if p_id not in memory["processed_ids"]:
                        batch_20.append({"id": p_id, "name": p_name})
                        if len(batch_20) == 20: break
                
                if len(batch_20) < 20:
                    page_num += 1
                else: break

            if not batch_20:
                print("🏁 더 이상 처리할 미처리 상품이 없거나 목표 페이지 범위를 벗어났습니다.")
                break

            # 2. 분석 및 엑셀 생성
            optimized = []
            for item in batch_20:
                path, seId, status = predict_category(item['name'], memory)
                optimized.append({"상품코드": item['id'], "상품명": item['name'], "제안 카테고리": path, "seId": seId, "상태": status})
                memory["processed_ids"].append(item['id'])

            timestamp = datetime.now().strftime('%H%M%S')
            file_name = f"relay_batch_{timestamp}.xlsx"
            df = pd.DataFrame(optimized)
            df['seId'] = df['seId'].astype(str).replace('nan', '')
            writer = pd.ExcelWriter(file_name, engine='openpyxl')
            df.to_excel(writer, index=False)
            ws = writer.sheets['Sheet1']
            for row in ws.iter_rows(min_row=2, min_col=df.columns.get_loc('seId')+1, max_col=df.columns.get_loc('seId')+1):
                for cell in row: cell.number_format = '@'
            writer.close()

            total_processed_this_session += len(batch_20)
            save_memory(memory)
            print(f"📦 [완료] {file_name} 생성 (누적 세트 처리량: {total_processed_this_session}건)")
            
            # 다음 반복 전 짧은 지연 (서버 부하 방지 및 안정성)
            await asyncio.sleep(2)

        await browser.close()
    print(f"[{datetime.now()}] ✅ 모든 작업 자율 종료 (총 {total_processed_this_session}건 처리)")

if __name__ == "__main__":
    asyncio.run(autonomic_unlimited_relay())
