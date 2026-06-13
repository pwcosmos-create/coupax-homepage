import json
import os
import re
import pandas as pd
from datetime import datetime

MEMORY_FILE = 'njob_rl_memory.json'

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"keywords": {}, "processed_ids": []}

def save_memory(memory):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def parse_capacity(name):
    # g, kg, ml, l, mg
    unit_pattern = r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|mg)'
    count_pattern = r'x\s*(\d+)|(\d+)\s*(?:개|봉|캔|팩|입|병|세트)'
    
    units = re.findall(unit_pattern, name, re.I)
    if not units: return None
    
    val, unit = units[0]
    val = float(val)
    unit = unit.lower()
    
    counts = re.findall(count_pattern, name)
    total_count = 1
    for c in counts:
        c_val = next((v for v in c if v), None)
        if c_val:
            total_count = int(c_val)
            break
            
    base_unit = unit
    multiplier = 1
    if unit == 'kg':
        val *= 1000
        base_unit = 'g'
    elif unit == 'l':
        val *= 1000
        base_unit = 'ml'
        
    total_capacity = val * total_count
    return {
        "total_cap": round(total_capacity, 2),
        "base_unit": base_unit,
        "base_val": 100 if total_capacity >= 100 else 10
    }

def predict_category(product_name, memory):
    name = product_name
    # memory check
    for kw, entry in memory.get('keywords', {}).items():
        if kw in name:
            return entry.get('path', ''), entry.get('seId', ''), "Verified (RL Memory)"
    
    # Simple hard rules for common categories
    RULES = [
        (["색연필", "필기도구", "필통"], "문구 > 화방용품 > 스케치/드로잉용품 > 색연필", "0903050300"),
        (["커피", "음료", "캔커피"], "식품 > 음료 > 커피 > 캔커피", "1001080315"),
        (["초콜릿", "초코", "사탕", "젤리"], "식품 > 과자 > 초콜릿", "1001080112"),
        (["쿠키", "비스킷", "스낵"], "식품 > 과자 > 스낵", "1001080104"),
        (["화분", "식물"], "취미/도서 > 원예/식물 > 화분용품 > 화분", "1312080000"),
        (["배드민턴", "셔틀콕"], "스포츠/레저 > 배드민턴 > 배드민턴용품/소품", "1408010000"),
        (["돗자리", "피크닉매트"], "스포츠/레저 > 캠핑 > 캠핑매트", "1421040000"),
        (["마스크"], "생활/건강 > 주방용품 > 주방잡화 > 마스크", "0708010000"), # Actually beauty or health but...
    ]
    
    for keywords, path, seId in RULES:
        if any(k in name for k in keywords):
            return path, seId, "Rule Based"
            
    return "기타", "", "Unknown"

if __name__ == "__main__":
    if not os.path.exists("njob_next_batch.json"):
        print("njob_next_batch.json 파일이 없습니다.")
        exit()
        
    with open("njob_next_batch.json", "r", encoding='utf-8') as f:
        items = json.load(f)
        
    memory = load_memory()
    results = []
    
    for item in items:
        path, seId, status = predict_category(item['name'], memory)
        cap_info = parse_capacity(item['name'])
        
        row = {
            "상품코드": item['id'],
            "상품명": item['name'],
            "제안 카테고리": path,
            "seId": seId,
            "상태": status,
            "총용량": "",
            "단위": "",
            "기준단위용량": ""
        }
        
        if cap_info:
            row["총용량"] = cap_info["total_cap"]
            row["단위"] = cap_info["base_unit"]
            row["기준단위용량"] = cap_info["base_val"]
            
        results.append(row)
        if item['id'] not in memory["processed_ids"]:
            memory["processed_ids"].append(item['id'])
            
    if results:
        df = pd.DataFrame(results)
        df['seId'] = df['seId'].astype(str).replace('nan', '')
        timestamp = datetime.now().strftime('%m%d_%H%M')
        output_file = f"njob_unit_price_relay_{timestamp}.xlsx"
        df.to_excel(output_file, index=False)
        save_memory(memory)
        print(f"✅ {len(results)}건 처리 완료: {output_file}")
    else:
        print("처리할 상품이 없습니다.")
