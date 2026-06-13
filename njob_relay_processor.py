import json
import os
import pandas as pd
from datetime import datetime

# 1. 강화학습 메모리 로드 (RL Memory)
MEMORY_FILE = 'njob_rl_memory.json'
CATEGORY_TREE_FILE = 'njob_category_tree.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "processed_ids" not in data:
                data["processed_ids"] = []
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
    normalized = []
    for kw in keywords:
        for part in kw.replace('/', ' ').replace('·', ' ').split():
            if len(part) >= 2:
                normalized.append(part)

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

    tree_path, tree_seId = search_category_tree(name.split())
    if tree_seId:
        return tree_path, tree_seId, "Tree Search"

    return "기타", "", "Unknown"

def process_batch(items):
    memory = load_memory()
    optimized_list = []
    
    # 중복 제외 필터링
    to_process = [item for item in items if item['id'] not in memory["processed_ids"]]
    
    if not to_process:
        print("이미 모두 처리된 상품들입니다.")
        return None

    for item in to_process:
        category, seId, status = predict_category(item['name'], memory)
        optimized_list.append({
            "상품코드": item['id'],
            "상품명": item['name'],
            "제안 카테고리": category,
            "seId": seId,
            "상태": status
        })
        # 처리 완료 ID 등록
        memory["processed_ids"].append(item['id'])

    # 결과 저장
    df = pd.DataFrame(optimized_list)
    df['seId'] = df['seId'].astype(str).replace('nan', '')
    timestamp = datetime.now().strftime('%m%d_%H%M')
    output_file = f"njob_bulk_update_relay_{timestamp}.xlsx"
    
    writer = pd.ExcelWriter(output_file, engine='openpyxl')
    df.to_excel(writer, index=False)
    ws = writer.sheets['Sheet1']
    for row in ws.iter_rows(min_row=2, min_col=df.columns.get_loc('seId')+1, max_col=df.columns.get_loc('seId')+1):
        for cell in row:
            cell.number_format = '@'
    writer.close()
    
    save_memory(memory)
    return output_file

if __name__ == "__main__":
    # 브라우저에서 가져온 20건 데이터
    DATA_20 = [
        {"id": "64260446", "name": "12컬러 부드러운 그림 그리기 색연필 미술용품"},
        {"id": "64260017", "name": "페트병 화분 자동급수기"},
        {"id": "64259486", "name": "메이크업 브러쉬 14종 원통케이스 세트"},
        {"id": "64259442", "name": "반지 팔찌 키링 시드 미니 비즈 diy 만들기 세트"},
        {"id": "64252483", "name": "36000 공단판 데코리본 세트 - 중 (36개입)"},
        {"id": "64252076", "name": "인효 교재용 바둑알 세트 - 소 P"},
        {"id": "64251950", "name": "스타 배드민턴 라켓 세트 FOCUS X200"},
        {"id": "64251619", "name": "신생사 소내용 끈딱 피크닉 방수 매트 유아용 십이식 돗자리"},
        {"id": "64251526", "name": "데일리 옻칠 나무 숟가락 젓가락 세트"},
        {"id": "64251522", "name": "핑크풋 피규어 컴퍼스 콤파스 세트"},
        {"id": "64251466", "name": "대용량 해피파티 물풍선 교회 성경학교 어린이날 행사 선물 세트 1판 (30set)"},
        {"id": "64251382", "name": "삼익악기 음악 학습용 리듬악기 세트 NSR-28"},
        {"id": "64251306", "name": "E09] (6개세트) 화분[혼합] 파스텔"},
        {"id": "64250846", "name": "여성 여름 망사 시스루 플라워 덧신 양말 10개 세트"},
        {"id": "64250835", "name": "주름리본속 원터치 패킹 세트 25A"},
        {"id": "64250635", "name": "드라이버 복스알 27종 세트 십자 일자 드라이버 소켓"},
        {"id": "64250540", "name": "사각 플라스틱 화분 6.5 x 6.5cm"},
        {"id": "64250380", "name": "네트 농구대 3색 농구림망 세트 일반형 골망 2개"},
        {"id": "64250376", "name": "발광셔틀콕 깃털 셔틀콕 거위깃털 야광 4p 세트 배드민턴공"},
        {"id": "64250361", "name": "인테리어소품 식물 수경 행잉 화분 화병"}
    ]
    res = process_batch(DATA_20)
    if res:
        print(f"성공: {res}")
