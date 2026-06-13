import asyncio
import os
import json
import pandas as pd
from playwright.async_api import async_playwright
from datetime import datetime

# .env 로드
from dotenv import load_dotenv
load_dotenv()

NJOB_ID = os.getenv("NJOB_ID")
NJOB_PW = os.getenv("NJOB_PW")
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

def predict_category(product_name, memory):
    name = product_name
    for kw, entry in memory['keywords'].items():
        if kw in name:
            return entry.get('path', ''), entry.get('seId', ''), "Verified (RL Memory)"

    RULES = [
        (["색연필"], "문구 > 화방용품 > 스케치/드로잉용품 > 색연필", "0903050300"),
        (["화분", "식물"], "취미/도서 > 원예/식물 > 화분용품 > 화분", "1312080000"),
        (["브러쉬"], "화장품 > 뷰티소품 > 메이크업브러쉬", "0706020000"),
        (["반지", "팔찌", "목걸이", "귀걸이"], "패션잡화 > 주얼리 > 반지", "0120030000"),
        (["리본", "포장"], "생활용품 > 공구 > 포장용품 > 리본", "12161905"),
        (["바둑"], "취미/도서 > 완구/피규어 > 보드게임", "1307020300"),
        (["배드민턴", "라켓", "셔틀콕"], "스포츠/레저 > 배드민턴 > 배드민턴라켓", "1408040000"),
        (["돗자리", "매트"], "스포츠/레저 > 캠핑 > 캠핑매트", "1421040000"),
        (["숟가락", "젓가락"], "생활용품 > 주방용품 > 식기/커틀러리 > 수저세트", "1213030100"),
        (["컴퍼스", "학용품"], "문구 > 사무용품 > 제도용품", "1001090000"),
        (["물풍선", "선물"], "취미/도서 > 완구/피규어 > 파티용품", "1307130000"),
        (["리듬악기", "악기"], "취미/도서 > 악기 > 타악기", "1313040000"),
        (["양말", "덧신"], "패션잡화 > 양말 > 양말세트", "0123010500"),
        (["복스알", "드라이버", "공구"], "생활용품 > 공구 > 수공구 > 드라이버", "1216020100"),
        (["농구"], "스포츠/레저 > 구기스포츠 > 농구 > 농구용품", "1405030000"),
    ]

    for keywords, path, seId in RULES:
        if any(k in name for k in keywords):
            return path, seId, "New Learned"
    return "기타", "", "Unknown"

async def run_relay_relay():
    memory = load_memory()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")
        page = await context.new_page()

        page_num = 1
        while True:
            print(f">>> [N잡AI] {page_num}페이지에서 미처리 상품 추출 중...")
            await page.goto(f"https://www.njobapp.com/send?status=SUCCESS&sz=100&pg={page_num}")
            await page.wait_for_load_state("networkidle")
            
            rows = await page.query_selector_all("table tbody tr")
            if not rows: break

            batch_20 = []
            for row in rows:
                p_id = await row.evaluate('r => r.querySelector("td:nth-child(2)").innerText.trim()')
                p_name = await row.evaluate('r => r.querySelector("td:nth-child(4)").innerText.trim()')
                
                if p_id not in memory["processed_ids"]:
                    batch_20.append({"id": p_id, "name": p_name})
                    if len(batch_20) == 20: break
            
            if not batch_20:
                print(f"  - {page_num}페이지에는 미처리 상품이 없습니다. 다음 페이지로...")
                page_num += 1
                if page_num > 10: break # 최대 10개 페이지만 검색
                continue

            # 20개 분석 및 엑셀 생성
            print(f"  - [{len(batch_20)}건] 분석 및 엑셀 생성 중...")
            optimized = []
            for item in batch_20:
                path, seId, status = predict_category(item['name'], memory)
                optimized.append({"상품코드": item['id'], "상품명": item['name'], "제안 카테고리": path, "seId": seId, "상태": status})
                memory["processed_ids"].append(item['id'])

            timestamp = datetime.now().strftime('%H%M%S')
            file_name = f"relay_20_pack_{timestamp}.xlsx"
            df = pd.DataFrame(optimized)
            df['seId'] = df['seId'].astype(str).replace('nan', '')
            writer = pd.ExcelWriter(file_name, engine='openpyxl')
            df.to_excel(writer, index=False)
            writer.close()

            # 엑셀 다운로드/업로드 버튼 클릭 (414 에러 방지를 위해 20건만)
            # 여기서는 엑셀 보정 버튼 클릭 시 URL에 ID들이 포함되므로 숫자를 줄이는 게 관건
            id_list_str = ",".join([item['id'] for item in batch_20])
            print(f"  - [{file_name}] 업로드 준비 중...")
            
            # 실제 업로드 페이지로 이동하여 파일 제출 시뮬레이션 가능
            # N잡 앱 내부 URL 구조상 엑셀 다운로드 버튼 URL을 조작하여 20건만 받게 할 수 있음
            
            save_memory(memory)
            print(f"  - ✅ {file_name} 완료 (누적 {len(memory['processed_ids'])}건)")
            
            # 사용자에게 20개 완료 보고 후 다음 요청 대기하거나 루프 지속
            # 일단 1세트 완료 보고
            break

        await browser.close()
    return f"relay_20_pack_{timestamp}.xlsx"

if __name__ == "__main__":
    asyncio.run(run_relay_relay())
