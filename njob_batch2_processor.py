import json
import os
import re
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

def parse_capacity(name):
    """
    상품명에서 총 용량을 파싱합니다.
    예: 829g x 2개 -> {'total': 1658, 'unit': 'g', 'base': 100}
    """
    # 1. 기본 패턴 추출 (숫자 + 단위)
    # g, kg, ml, l, mg 등 지원
    unit_pattern = r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|mg)'
    count_pattern = r'x\s*(\d+)|(\d+)\s*(?:개|봉|캔|팩|입|병|세트)'
    
    units = re.findall(unit_pattern, name, re.I)
    if not units:
        return None
    
    val, unit = units[0]
    val = float(val)
    unit = unit.lower()
    
    # 2. 개수(Count) 확인
    counts = re.findall(count_pattern, name)
    total_count = 1
    for c in counts:
        c_val = next((v for v in c if v), None)
        if c_val:
            total_count = int(c_val)
            break
            
    # 3. 단위 변환 (kg -> g, l -> ml)
    base_unit = unit
    multiplier = 1
    if unit == 'kg':
        val *= 1000
        base_unit = 'g'
    elif unit == 'l':
        val *= 1000
        base_unit = 'ml'
        
    total_capacity = val * total_count
    
    # 네이버 단위가격 기준: 보통 100g 또는 100ml
    return {
        "total_cap": round(total_capacity, 2),
        "base_unit": base_unit,
        "base_val": 100 if total_capacity >= 100 else 10
    }

def predict_category(product_name, memory):
    name = product_name
    
    # 1단계: 직접 규칙 (Hard Rules)
    RULES = [
        (["커피", "음료", "음료수", "캔커피"], "식품 > 음료 > 커피 > 캔커피", "1001080315"),
        (["초콜릿", "초코", "사탕", "캔디", "젤리"], "식품 > 과자 > 초콜릿", "1001080112"),
        (["쿠키", "비스킷", "와플", "스낵"], "식품 > 과자 > 스낵", "1001080104"),
        (["호떡", "간편식", "즉석"], "식품 > 냉동식품 > 냉동간식", "1001080402"),
        (["가방", "세트", "꾸미"], "패션잡화 > 가방 > 아동용가방", "0121080000"),
        (["압축팩", "정리"], "생활/건강 > 수납/정리용품 > 압축팩", "1214060000"),
        (["국수", "소면", "세트"], "식품 > 농산물 > 잡곡 > 기타잡곡", "1001080509"),
        (["견과", "아몬드"], "식품 > 농산물 > 견과류 > 기타견과류", "1001080514"),
    ]

    for keywords, path, seId in RULES:
        if any(k in name for k in keywords):
            return path, seId, "Food/General Rules"

    # 기타 트리 검색 로직 생략(간소화)
    return "기타", "", "Unknown"

if __name__ == "__main__":
    memory = load_memory()
    
    # Batch #2: 26 Food Items from Subagent
    DATA_BATCH_2 = [
      {"id": "64182678", "name": "조지아 오리지날 240ml 캔커피 30캔 세트 사무실 간식 음료"},
      {"id": "64161247", "name": "넓적 당면 간식 향라맛 20개 세트 마라훠 즉석 간편식 중국 식품"},
      {"id": "64139138", "name": "조지아 오리지날 240ml 캔커피 30캔 세트 사무실 간식 음료"},
      {"id": "64146485", "name": "롯데 ABC초콜릿 ABC 초코 829g x 2개"},
      {"id": "64146478", "name": "롯데 ABC초콜릿 ABC 초코 829g"},
      {"id": "64139121", "name": "앤드 메이플 쿠키 320g 단풍 시럽 함유 부드러운 쿠키"},
      {"id": "64010376", "name": "[삼립] 삼립호떡(꿀호떡) 200g x 10봉"},
      {"id": "64004805", "name": "국내산 봄 도다리 도다리탕 세트 도다리800g 쑥 40g"},
      {"id": "63726538", "name": "롤리팝 막대 사탕 소 10개입 화이트데이 발렌타인 선물 어린이집 간식"},
      {"id": "63686231", "name": "[삼립] 삼립호떡(꿀호떡) 200g x 10봉"},
      {"id": "63686230", "name": "머거본 아몬드 4종 믹스 민들 10g 20개입 1팩 견과류 세트 맥주 안주 어른 간식"},
      {"id": "63686246", "name": "머거본 믹스파티 프렌즈 250g 믹스 견과 종합 안주 세트 맥주 안주 어른 간식"},
      {"id": "63686202", "name": "오발틴 코코아 마시멜로우 25g 20개입 1통 초코 마시멜로 대용량 아이들 초등학"},
      {"id": "63686264", "name": "미성 해씨 초콜릿 30g 영양 만점 해바라기씨 초코 아이들 초등학생 간식 어른 간"},
      {"id": "63675328", "name": "선물 구포 추석 명절 소면 설날 국수 세트"},
      {"id": "63655156", "name": "공간활용 옷장 정리 압축 이불 정리 압축팩 침구류 여행용"},
      {"id": "63626067", "name": "쥬얼리 캔디(45g) 발렌타인 화이트 데이 사탕 선물"},
      {"id": "63622162", "name": "청우 오리지날 찰떡 쿠키 (215g)"},
      {"id": "63622201", "name": "청우 오리지날 그린티 찰떡쿠키 (215g)"},
      {"id": "63686197", "name": "델피 차차 야구 캡모자 미니 초코볼 30g 12개입 1통 장난감 초코볼 아이들 초등"},
      {"id": "63686203", "name": "미니 땅콩버터 와플 초콜릿 콘 300g 4개 대용량 세트 피넛버터 과자 아이들 초등"},
      {"id": "63686201", "name": "오발틴 코코아 마시멜로우 25g 초코 마시멜로 달콤한 초콜릿 디저트 아이들 초등"},
      {"id": "63686204", "name": "미니 땅콩버터 와플 초콜릿 콘 300g 대용량 피넛버터 과자 아이들 초등학생"},
      {"id": "63686233", "name": "스노우 생 초코레드 오리지널 32g 입안에서 사르르 녹는 초콜릿 아이들 초등학생"},
      {"id": "63686263", "name": "미성 해씨 초콜릿 30g 12개입 1통 고소한 해바라기씨 초콜릿 아이들 초등학생"},
      {"id": "63686213", "name": "엘리스 초코 샌드 비스킷 150g 진한 초콜릿 크림 샌드 과자 아이들 초등학생 간식"}
    ]
    
    optimized_list = []
    for item in DATA_BATCH_2:
        # 이미 처리된 ID라도 이번에는 단위가격 설정을 위해 다시 처리 (선택사항)
        # if item['id'] in memory["processed_ids"]: continue
        
        path, seId, status = predict_category(item['name'], memory)
        cap_info = parse_capacity(item['name'])
        
        row = {
            "상품코드": item['id'],
            "상품명": item['name'],
            "제안 카테고리": path,
            "seId": seId,
            "상태": status
        }
        
        # 단위가격 정보 추가
        if cap_info:
            row["총용량"] = cap_info["total_cap"]
            row["단위"] = cap_info["base_unit"]
            row["기준단위용량"] = cap_info["base_val"]
        else:
            row["총용량"] = ""
            row["단위"] = ""
            row["기준단위용량"] = ""
            
        optimized_list.append(row)
        if item['id'] not in memory["processed_ids"]:
            memory["processed_ids"].append(item['id'])

    if optimized_list:
        df = pd.DataFrame(optimized_list)
        df['seId'] = df['seId'].astype(str).replace('nan', '')
        
        timestamp = datetime.now().strftime('%m%d_%H%M')
        # 엑셀 파일명에 'unit_price' 명시
        output_file = f"njob_unit_price_update_{timestamp}.xlsx"
        
        writer = pd.ExcelWriter(output_file, engine='openpyxl')
        df.to_excel(writer, index=False)
        writer.close()
        
        save_memory(memory)
        print(f"✅ 식품군 26건 업데이트 완료: {output_file}")
        print(f"   (총용량/단위 파싱 성공 건수: {df[df['총용량'] != ''].shape[0]}건)")
    else:
        print("새로 처리할 상품이 없습니다.")
