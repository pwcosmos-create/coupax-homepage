import json
import os
import pandas as pd
from datetime import datetime

# 1. 강화학습 메모리 로드 (RL Memory)
MEMORY_FILE = 'njob_rl_memory.json'
CATEGORY_TREE_FILE = 'njob_category_tree.json'

# 카테고리 트리 로드 (세부 경로 검색용)
_cat_tree = None
def load_category_tree():
    global _cat_tree
    if _cat_tree is None and os.path.exists(CATEGORY_TREE_FILE):
        with open(CATEGORY_TREE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _cat_tree = data.get('flat_list', [])
    return _cat_tree or []

def search_category_tree(keywords, path_hint=None):
    """
    카테고리 트리에서 키워드로 검색, (path, seId) 반환.
    path_hint: 상위 경로 힌트 (예: "화장품") - 오매핑 방지용 컨텍스트 필터
    """
    tree = load_category_tree()

    # 키워드 정규화: "색연필/파스텔" -> ["색연필", "파스텔"] 로 분리
    normalized = []
    for kw in keywords:
        for part in kw.replace('/', ' ').replace('·', ' ').split():
            if len(part) >= 2:
                normalized.append(part)

    # 1차: path_hint + 키워드 동시 매칭 (정확도 우선)
    if path_hint:
        for kw in normalized:
            for node in tree:
                node_name = node.get('name', '')
                node_path = node.get('path', '')
                if kw in node_name and path_hint in node_path and node.get('seId'):
                    return node_path, node['seId']

    # 2차: 정확한 이름 일치 (kw == node_name)
    for kw in normalized:
        for node in tree:
            if kw == node.get('name', '') and node.get('seId'):
                return node['path'], node['seId']

    # 3차: 키워드가 노드명 시작 부분에 있는 것 우선
    for kw in normalized:
        for node in tree:
            node_name = node.get('name', '')
            if node_name.startswith(kw) and node.get('seId'):
                return node['path'], node['seId']

    # 4차: 부분 포함 (기존 방식)
    for kw in normalized:
        for node in tree:
            node_name = node.get('name', '')
            if kw in node_name and node.get('seId'):
                return node['path'], node['seId']

    return None, None
EXTRACTED_DATA = [
    {"id": "64260446", "name": "12컬러 부드러운 그림 그리기 색연필 미술용품"},
    {"id": "64260017", "name": "페트병 화분 자동급수기"},
    {"id": "64259486", "name": "메이크업 브러쉬 14종 원통케이스 세트"},
    {"id": "64259442", "name": "반지 팔찌 키링 시드 미니 비즈 diy 만들기 세트"},
    {"id": "64252483", "name": "36000 공단판 데코리본 세트 - 중 (36개입)"}
    # 실제로는 더 많은 데이터가 JSON 파일로 관리됩니다.
]

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"keywords": {}}

def save_memory(memory):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def predict_category(product_name, memory):
    """
    상품명을 분석하여 njobapp 카테고리 경로와 seId를 반환합니다.
    반환: (카테고리경로, seId, 상태)
    """
    name = product_name

    # 1단계: RL 메모리 키워드 매칭 (Exploitation - 가장 높은 우선순위)
    for kw, entry in memory['keywords'].items():
        if kw in name:
            if isinstance(entry, dict):
                return entry.get('path', ''), entry.get('seId', ''), "Verified (RL Memory)"
            return entry, '', "Verified (RL Memory)"

    # 2단계: 직접 seId 매핑 테이블 (njobapp 카테고리 트리 기반, 정확한 seId)
    # 형식: (키워드 리스트, 경로, seId)
    RULES = [
        # ── 화장품 ──────────────────────────────────────────────────────────
        (["메이크업브러쉬", "브러쉬", "파우더브러쉬", "아이브러쉬"],
            "화장품 > 뷰티소품 > 메이크업브러쉬", "0706020000"),
        (["아이섀도", "아이쉐도우"],
            "화장품 > 아이메이크업 > 아이섀도", "0707040000"),
        (["아이라이너"],
            "화장품 > 아이메이크업 > 아이라이너", "0707020000"),
        (["마스카라"],
            "화장품 > 아이메이크업 > 마스카라", "0707030000"),
        (["립스틱", "립글로스", "립틴트", "립밤"],
            "화장품 > 립메이크업 > 립스틱", "0707030000"),
        (["파운데이션", "비비크림"],
            "화장품 > 베이스메이크업 > 파운데이션", "0705080000"),
        (["쿠션", "컨실러", "프라이머"],
            "화장품 > 베이스메이크업 > 쿠션", "0705060000"),
        (["토너", "스킨로션", "기초화장"],
            "화장품 > 기초화장품 > 스킨", "0701090000"),
        (["세럼", "에센스", "앰플"],
            "화장품 > 기초화장품 > 에센스", "0701100000"),
        (["선크림", "선스프레이", "자외선차단"],
            "화장품 > 기초화장품 > 선크림", "0701060000"),
        (["클렌징", "폼클렌저", "클렌징오일"],
            "화장품 > 클렌징", "0710000000"),
        (["샴푸", "린스", "트리트먼트", "헤어팩"],
            "화장품 > 헤어케어 > 샴푸", "0713020000"),
        (["향수", "퍼퓸", "오드뚜왈렛"],
            "화장품 > 향수", "0711000000"),

        # ── 패션잡화 / 주얼리 ──────────────────────────────────────────────
        (["팔찌", "뱅글"],
            "패션잡화 > 주얼리 > 팔찌", "0120070000"),
        (["반지"],
            "패션잡화 > 주얼리 > 반지", "0120030000"),
        (["목걸이"],
            "패션잡화 > 주얼리 > 목걸이", "0120020000"),
        (["귀걸이", "이어링"],
            "패션잡화 > 주얼리 > 귀걸이", "0120010000"),
        (["키링", "키홀더"],
            "패션잡화 > 패션소품 > 키홀더", "0122180000"),
        (["가방", "토트백", "숄더백", "크로스백", "백팩"],
            "패션잡화 > 가방", "0121000000"),
        (["지갑", "카드지갑"],
            "패션잡화 > 지갑", "0908010000"),

        # ── 문구 ────────────────────────────────────────────────────────────
        (["색연필"],
            "문구 > 화방용품 > 스케치/드로잉용품 > 색연필", "0903050300"),
        (["파스텔", "크레파스", "크레용"],
            "문구 > 화방용품 > 스케치/드로잉용품 > 파스텔", "1002060700"),
        (["마카", "마커"],
            "문구 > 화방용품 > 스케치/드로잉용품 > 마카", "1002060100"),
        (["물감", "아크릴물감", "수채화"],
            "문구 > 화방용품 > 물감 > 수채화물감", "1002040300"),
        (["볼펜"],
            "문구 > 사무용품 > 필기도구 > 볼펜", "1001200600"),
        (["연필", "샤프"],
            "문구 > 사무용품 > 필기도구 > 연필", "1001201200"),
        (["스티커", "라벨"],
            "문구 > 사무용품 > 스티커/테이프 > 스티커", "1001120300"),
        (["테이프"],
            "문구 > 사무용품 > 스티커/테이프 > 테이프", "1001120400"),

        # ── 포장재 / 리본 ───────────────────────────────────────────────────
        (["리본", "데코리본", "공단리본", "공단판"],
            "생활용품 > 공구 > 포장용품 > 리본", "12161905"),
        (["포장지", "쇼핑백", "선물포장"],
            "생활용품 > 공구 > 포장용품 > 포장지", "12161906"),
        (["포장용품", "포장재"],
            "생활용품 > 공구 > 포장용품", "1216100000"),

        # ── 취미/도서 (DIY/비즈/원예) ──────────────────────────────────────
        (["비즈", "시드비즈", "씨드비즈"],
            "취미/도서 > DIY/공예 > 비즈공예", "1310010400"),
        (["자수", "크로스스티치"],
            "취미/도서 > DIY/공예 > 자수", "1310010700"),
        (["뜨개", "뜨개질"],
            "취미/도서 > DIY/공예 > 뜨개질", "1310010700"),
        (["화분", "플랜터", "다육화분"],
            "취미/도서 > 원예/식물 > 화분용품 > 화분", "1312080000"),
        (["자동급수", "급수기"],
            "취미/도서 > 원예/식물 > 정원/원예용품", "1312000000"),
        (["원예", "비료", "배양토"],
            "취미/도서 > 원예/식물 > 정원/원예용품", "1312000000"),
        (["피규어", "모형", "프라모델"],
            "취미/도서 > 완구/피규어 > 피규어", "1307040700"),
        (["보드게임"],
            "취미/도서 > 완구/피규어 > 보드게임", "1307020300"),
        (["퍼즐"],
            "취미/도서 > 완구/피규어 > 퍼즐", "1307120200"),

        # ── 식품/건강식품 ───────────────────────────────────────────────────
        (["비타민", "비타C"],
            "식품 > 건강식품 > 비타민제", "1602050000"),
        (["유산균", "프로바이오틱"],
            "식품 > 건강식품 > 유산균", "1602050000"),
        (["단백질", "프로틴"],
            "식품 > 건강식품 > 단백질보충제", "1607050100"),

        # ── 스포츠/레저 ────────────────────────────────────────────────────
        (["배드민턴", "셔틀콕"],
            "스포츠/레저 > 배드민턴 > 배드민턴라켓", "1408040000"),
        (["라켓", "테니스"],
            "스포츠/레저 > 테니스 > 테니스라켓", "1423020000"),
        (["자물쇠", "자전거자물쇠"],
            "스포츠/레저 > 자전거 > 자전거자물쇠", "1418031200"),
        (["요가", "필라테스"],
            "스포츠/레저 > 요가/필라테스 > 요가매트", "1416040000"),
        (["캠핑", "텐트", "등산"],
            "스포츠/레저 > 캠핑", "1421000000"),

        # ── 디지털/가전 ────────────────────────────────────────────────────
        (["이어폰", "블루투스이어폰"],
            "스포츠/레저 > 음향기기 > 이어폰", "1715140000"),
        (["케이블", "충전케이블"],
            "스포츠/레저 > PC부품 > PC케이블 > 데이터케이블", "1702010700"),
        (["충전기", "어댑터"],
            "스포츠/레저 > MP3/PMP액세서리 > 충전기", "1715210300"),
        (["폰케이스", "핸드폰케이스", "스마트폰케이스"],
            "스포츠/레저 > 모바일액세서리 > 모바일케이스", "1724160000"),

        # ── 반려동물 ────────────────────────────────────────────────────────
        (["사료", "펫푸드"],
            "취미/도서 > 반려동물 > 강아지사료 > 건식사료", "1304040100"),
        (["간식", "펫간식"],
            "취미/도서 > 반려동물 > 간식/영양제", "1304160000"),
        (["고양이", "캣타워", "캣"],
            "취미/도서 > 반려동물 > 고양이용품", "1304010000"),
        (["강아지", "펫"],
            "취미/도서 > 반려동물 > 강아지용품", "1304070000"),
    ]

    for keywords, path, seId in RULES:
        if any(k in name for k in keywords):
            return path, seId, "New Learned"

    # 3단계: 트리 검색 폴백 (완전 미지 상품)
    tree_path, tree_seId = search_category_tree(name.split())
    if tree_seId:
        return tree_path, tree_seId, "Tree Search"

    return "기타", "", "Unknown (Check Required)"

def _rl_learn(product_name, category, seId, memory):
    """
    New Learned 상품명에서 핵심 키워드를 추출해 RL 메모리에 저장.
    이미 메모리에 있는 키워드는 건너뜀.
    """
    # 불용어 (분류에 도움이 안 되는 단어)
    stopwords = {
        '세트', '구성', '상품', '제품', '용품', '기타', '미용', '잡화', '기본',
        '신상', '인기', '최신', '고품질', '전용', '국내', '무료', '배송',
        '1개', '2개', '3개', '개입', '개월', '사이즈', '컬러', '색상',
        'diy', 'DIY', '만들기', '세트', '종', '중', '대', '소'
    }

    # 상품명에서 2글자 이상 명사 후보 추출 (공백 기준 토크나이징)
    tokens = product_name.replace('-', ' ').replace('(', ' ').replace(')', ' ').split()
    candidates = [t for t in tokens if len(t) >= 2 and t not in stopwords and not t.isdigit()]

    existing_keywords = set(memory['keywords'].keys())
    learned = []

    for token in candidates:
        # 이미 메모리에 있거나, 너무 일반적인 단어 건너뜀
        if token in existing_keywords:
            continue
        # 이 키워드로 실제로 카테고리를 잘 식별하는지 확인 (역검증)
        # - 해당 토큰이 카테고리 경로에 의미있게 연결되는 경우만 저장
        tree_path, tree_seId = search_category_tree([token])
        if tree_seId == seId:
            # 트리에서도 동일한 seId 발견 → 강한 신호, 즉시 저장
            memory['keywords'][token] = {'path': category, 'seId': seId, 'tree_path': tree_path or ''}
            existing_keywords.add(token)
            learned.append(token)
        elif len(token) >= 3:
            # seId 불일치지만 3글자 이상이면 경로 힌트와 함께 저장 (약한 학습)
            memory['keywords'][token] = {'path': category, 'seId': seId, 'tree_path': ''}
            existing_keywords.add(token)
            learned.append(token)

    if learned:
        print(f"  [RL] '{product_name[:20]}' -> 신규 학습: {learned}")

def run_optimization():
    memory = load_memory()
    optimized_list = []
    
    print(f"[{datetime.now()}] 엔잡 AI 최적화 매칭 엔진 가동 중...")
    
    for item in EXTRACTED_DATA:
        category, seId, status = predict_category(item['name'], memory)
        optimized_list.append({
            "상품코드": item['id'],
            "상품명": item['name'],
            "제안 카테고리": category,
            "seId": seId,
            "상태": status
        })
        
        # ── RL 학습: New Learned → 키워드 메모리 저장 (Exploration → Exploitation)
        if status == "New Learned" and seId:
            _rl_learn(item['name'], category, seId, memory)

    # ── RL 통계 업데이트 ──────────────────────────────────────────────────────
    reward = len([x for x in optimized_list if x['상태'] != 'Unknown (Check Required)'])
    penalty = len([x for x in optimized_list if x['상태'] == 'Unknown (Check Required)'])
    memory['feedback']['reward_count'] += reward
    memory['feedback']['penalty_count'] += penalty
    memory['feedback']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    save_memory(memory)

    # 3. 엑셀 업로드용 파일 생성 (seId 앞 0 보존을 위해 문자열 처리)
    df = pd.DataFrame(optimized_list)
    df['seId'] = df['seId'].astype(str).replace('nan', '')
    output_file = f"njob_bulk_update_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='openpyxl')
    df.to_excel(writer, index=False)
    ws = writer.sheets['Sheet1']
    for row in ws.iter_rows(min_row=2, min_col=df.columns.get_loc('seId')+1,
                            max_col=df.columns.get_loc('seId')+1):
        for cell in row:
            cell.number_format = '@'  # 텍스트 형식
    writer.close()

    print(f"[완료] 총 {len(optimized_list)}건에 대한 카테고리 보정 완료!")
    print(f"[완료] 결과 파일: {output_file}")

    # 보고서 작성용 통계
    reward = len([x for x in optimized_list if x['상태'] != 'Unknown (Check Required)'])
    print(f"[RL] 강화학습 성공(Reward): {reward}건 / 미확인: {len(optimized_list) - reward}건")

if __name__ == "__main__":
    run_optimization()
