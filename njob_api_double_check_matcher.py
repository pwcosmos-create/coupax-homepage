import pandas as pd
import json
import time
import re
from domeme_api import DomemeAPI
from tqdm import tqdm

# 데이터 로드
try:
    report = pd.read_csv('refined_category_report.csv')
    with open('njob_leaf_categories.json', 'r', encoding='utf-8') as f:
        naver_leafs = json.load(f)
except FileNotFoundError:
    print("[-] 필수 데이터 파일(CSV, JSON)을 찾을 수 없습니다.")
    exit()

api = DomemeAPI()

def clean_title(title):
    """제목에서 특수문자 제거 및 검색용 키워드 추출"""
    title = re.sub(r'\[.*?\]', '', title) # 대괄호 태그 제거
    words = re.findall(r'\w+', title)
    return " ".join(words[:5]) # 앞쪽 5단어 위주로 검색

def find_naver_leaf(domeme_cat_leaf):
    """도매매 카테고리명을 기반으로 네이버 리프 노드 매칭"""
    best_match = None
    max_score = 0
    
    # 1. 완전 일치 검색
    for leaf in naver_leafs:
        if domeme_cat_leaf in leaf['name']:
            return leaf['id'], leaf['name']
            
    # 2. 부분 일치 검색 (Fuzzy-ish)
    # 생략 (필요 시 점수 기반 로직 추가 가능)
    return None, None

def process_double_check():
    # 1차 매칭에서 Mismatch였던 상품만 추출
    mismatch_items = report[report['상태'] == 'Mismatch'].copy()
    print(f"[*] 분석 대상 상품 수: {len(mismatch_items)}")

    results = []
    
    for idx, row in tqdm(mismatch_items.iterrows(), total=len(mismatch_items)):
        product_id = str(row['상품번호'])
        title = str(row['상품명'])
        
        # 도매매 검색
        search_kw = clean_title(title)
        search_res = api.search_product(search_kw, size=1)
        
        suggested_id = row['추천ID']
        suggested_name = row['추천카테고리']
        status = "Mismatch"
        
        try:
            if 'domeggook' in search_res and search_res['domeggook']['list']['item']:
                item_no = search_res['domeggook']['list']['item'][0]['no']
                detail = api.get_item_detail(item_no)
                
                if 'domeggook' in detail and 'category' in detail['domeggook']:
                    cat_data = detail['domeggook']['category']
                    domeme_leaf_name = ""
                    if 'current' in cat_data:
                        domeme_leaf_name = cat_data['current']['name']
                    elif 'parents' in cat_data and cat_data['parents']['elem']:
                        domeme_leaf_name = cat_data['parents']['elem'][-1]['name']
                    
                    if domeme_leaf_name:
                        # 네이버 리프 노드 매칭
                        leaf_id, leaf_name = find_naver_leaf(domeme_leaf_name)
                        if leaf_id:
                            suggested_id = leaf_id
                            suggested_name = leaf_name
                            status = "Fixed (Phase2)"
                    else:
                        # 리프 노드 직접 매칭 실패 시, 제목 키워드로 다시 한 번 시도
                        pass
                        
            time.sleep(0.5) # API Rate Limit 보호
        except Exception as e:
            # print(f"\n[-] Error processing {product_id}: {e}")
            pass
            
        results.append({
            '상품ID': product_id,
            '상품명': title,
            '기존ID': row.get('기존ID', ''),
            '기존카테고리': row['현재카테고리'],
            '추천ID': suggested_id,
            '추천카테고리': suggested_name,
            '상태': status
        })

    # 최종 리포트 저장
    new_report = pd.DataFrame(results)
    new_report.to_csv('refined_category_report_v2.csv', index=False, encoding='utf-8-sig')
    print(f"\n[+] 분석 완료. 'refined_category_report_v2.csv' 저장됨.")
    print(f"[+] 보정된 상품 수: {len(new_report[new_report['상태'] == 'Fixed (Phase2)'])}")

if __name__ == "__main__":
    process_double_check()
