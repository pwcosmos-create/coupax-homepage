import pandas as pd
import json
import os
import time

def load_category_tree(filename='njob_category_tree.json'):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found. Please wait for the update script to finish.")
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('flat_list', [])

def match_category(product_name, cat_tree):
    # 단순 키워드 매칭 로직 (개선 가능)
    # 제품명의 단어들이 카테고리 경로(path)에 얼마나 포함되는지 점수 계산
    keywords = [kw for kw in product_name.split() if len(kw) >= 2]
    
    best_match = None
    max_score = 0
    
    # 성능을 위해 leaf 노드(last=True) 위주로 검색하거나 전체 검색
    for node in cat_tree:
        node_path = node.get('path', '')
        node_name = node.get('name', '')
        
        score = 0
        # 1. 카테고리 이름이 제품명에 포함된 경우 (가중치)
        if node_name in product_name:
            score += 10
            
        # 2. 제품명 키워드가 카테고리 경로에 포함된 경우
        for kw in keywords:
            if kw in node_path:
                score += 2
        
        if score > max_score:
            max_score = score
            best_match = node
            
    return best_match, max_score

def analyze_products():
    print(">>> Loading data...")
    products_file = 'products_list_full.csv'
    if not os.path.exists(products_file):
        print(f"Error: {products_file} not found.")
        return
        
    df = pd.read_csv(products_file)
    cat_tree = load_category_tree()
    if not cat_tree:
        return

    results = []
    print(f"[*] Analyzing {len(df)} products...")
    
    start_time = time.time()
    for i, row in df.iterrows():
        name = row['상품명']
        current_cat = row['카테고리']
        
        match, score = match_category(name, cat_tree)
        
        recommended_cat = match['path'] if match else "None"
        recommended_id = match['id'] if match else "None"
        
        is_mismatch = False
        if recommended_cat != "None" and current_cat != recommended_cat:
            # 대분류/중분류 정도만 달라도 미스매치로 간주 (필요시 상세 조정)
            is_mismatch = True
            
        results.append({
            '상품번호': row['상품번호'],
            '상품명': name,
            '현재카테고리': current_cat,
            '추천카테고리': recommended_cat,
            '추천ID': recommended_id,
            '점수': score,
            '상태': 'Mismatch' if is_mismatch else 'OK'
        })
        
        if (i+1) % 100 == 0:
            print(f"[*] Processed {i+1}/{len(df)} products...")

    report_df = pd.DataFrame(results)
    report_filename = 'category_comparison_report.csv'
    report_df.to_csv(report_filename, index=False, encoding='utf-8-sig')
    
    mismatches = report_df[report_df['상태'] == 'Mismatch']
    print(f"\n✅ Analysis Complete! Total Mismatches found: {len(mismatches)}")
    print(f"Detailed report saved to: {report_filename}")

if __name__ == "__main__":
    analyze_products()
