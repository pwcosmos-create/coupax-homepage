import pandas as pd
import json
import os
import time
import re

# 설정 파일 경로
CATEGORY_TREE_FILE = 'njob_category_tree.json'
RL_MEMORY_FILE = 'njob_rl_memory.json'
PRODUCTS_FILE = 'products_list_full.csv'
REPORT_FILE = 'refined_category_report.csv'

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_rules():
    """
    기본적인 매핑 규칙 정의 (njob_category_mapper.py 등에서 추출 및 보정)
    형식: ([키워드 리스트], 카테고리경로, seId)
    """
    return [
        (["절구", "절구통", "절구공이"], "생활/가계용품 > 주방용품 > 조리도구 > 조리기구 > 절구", "50004758"),
        (["브러쉬", "브러시", "메이크업"], "화장품/미용 > 뷰티소품 > 메이크업브러쉬", "50000244"),
        (["색연필"], "생활/건강 > 문구/사무용품 > 화방용품 > 색연필", "50003896"),
        (["캔커피", "조지아", "레쓰비"], "식품 > 음료 > 커피 > 캔커피", "50001859"),
        (["초콜릿", "abc초코"], "식품 > 과자 > 초콜릿", "50001831"),
        (["호떡", "꿀호떡"], "식품 > 냉동식품 > 냉동간식", "50001825"),
        (["디스펜서", "샴푸통"], "생활/건강 > 욕실용품 > 욕실용기/홀더 > 디스펜서", "50008649"),
        (["드라이버", "스크류"], "생활/건강 > 공구 > 수작업공구 > 드라이버", "50003391"),
    ]

class RefinedMatcher:
    def __init__(self):
        print("[*] Loading Category Tree and Memory...")
        self.cat_data = load_json(CATEGORY_TREE_FILE)
        self.flat_tree = self.cat_data.get('flat_list', [])
        self.memory = load_json(RL_MEMORY_FILE)
        self.rules = get_rules()
        
        # 일반적인/모호한 카테고리 명칭 (패널티 대상)
        self.generic_names = {'세트', '박스', '기타', '기타잡화', '기타용품', '기타잡곡', '정리함', '수납함'}
        # 특정 단어가 포함될 때 제외할 카테고리 맵 (단어: [제외할 상위 카테고리명])
        self.exclusion_context = {
            '주먹밥': ['화방용품', '문구/사무용품'],
            '도시락': ['화방용품', '문구/사무용품'],
            '드라이버': ['수납/정리용품'],
            '샴푸': ['수납/정리용품'],
        }

    def get_score(self, product_name, node):
        node_path = node.get('path', '')
        node_name = node.get('name', '')
        
        # 제외 컨텍스트 확인
        for excl_word, excl_cats in self.exclusion_context.items():
            if excl_word in product_name:
                if any(excl_cat in node_path for excl_cat in excl_cats):
                    return -1000 # 무조건 제외
        
        score = 0
        
        # 1. 노드 이름이 제품명에 정확히 포함됨
        if node_name in product_name:
            # 특수 처리: '정리함' 등 일반 명칭은 단독으로 점수를 많이 주지 않음
            if node_name in self.generic_names:
                score += 10
            else:
                score += 35
                if node_name == product_name: # 완전 일치
                    score += 50
        
        # 2. 제품명의 단어들이 경로에 포함됨
        keywords = [kw for kw in product_name.split() if len(kw) >= 2]
        for kw in keywords:
            if kw in node_path:
                score += 5
        
        # 3. 구체성 보너스 (Depth가 깊을수록 상세 카테고리)
        depth = node_path.count('>') + 1
        score += (depth * 3)
        
        # 3.5. Leaf Node 보너스 (매칭된 노드가 Leaf인 경우)
        # (이미 flat_tree에서 filtering 중이지만 명시적 보너스)
        score += 5

        # 4. 일반적 명칭 패널티 (세트, 기타 등등)
        if node_name in self.generic_names:
            score -= 40
            
        return score

    def predict(self, product_name):
        # 1단계: 직접 규칙 (Hard Rules) - 검증된 Leaf ID만 사용
        for keywords, path, seId in self.rules:
            if any(k in product_name for k in keywords):
                # Hard Rule도 Exclusion 적용
                is_excluded = False
                for excl_word, excl_cats in self.exclusion_context.items():
                    if excl_word in product_name:
                        if any(excl_cat in path for excl_cat in excl_cats):
                            is_excluded = True
                if not is_excluded:
                    return path, seId, "Hard Rule Match", 100

        # 2단계: RL 메모리 키워드 매칭
        for kw, entry in self.memory.get('keywords', {}).items():
            if kw in product_name:
                path = entry.get('path', '')
                seId = entry.get('seId', '')
                # Exclusion 적용
                is_excluded = False
                for excl_word, excl_cats in self.exclusion_context.items():
                    if excl_word in product_name:
                        if any(excl_cat in path for excl_cat in excl_cats):
                            is_excluded = True
                if not is_excluded:
                    return path, seId, "RL Memory Match", 90

        # 3단계: 트리 가중치 검색 (무조건 Leaf Node만 선택)
        best_match = None
        max_score = -100
        
        for node in self.flat_tree:
            # leafCategoryId가 없거나 리프 노드가 아니면 제외
            if not node.get('seId') or not node.get('last', True):
                continue
                
            score = self.get_score(product_name, node)
            if score > max_score:
                max_score = score
                best_match = node
        
        if best_match and max_score > 15: # 최소 임계값 상향
            return best_match['path'], best_match['seId'], "Tree Search", max_score
        
        return "None", "None", "No Match", 0

    def analyze(self):
        if not os.path.exists(PRODUCTS_FILE):
            print(f"[-] {PRODUCTS_FILE} not found.")
            return

        df = pd.read_csv(PRODUCTS_FILE)
        print(f"[*] Analyzing {len(df)} products...")
        
        results = []
        for i, row in df.iterrows():
            name = row['상품명']
            current_cat = row['카테고리']
            
            rec_path, rec_id, method, score = self.predict(name)
            
            is_mismatch = False
            # 추천 카테고리가 있고, 현재와 다를 때만 Mismatch
            if rec_path != "None" and current_cat != rec_path:
                # 점수가 너무 낮으면 (예: 10 이하) 신뢰하지 않음
                if score >= 15:
                    is_mismatch = True
            
            results.append({
                '상품번호': row['상품번호'],
                '상품명': name,
                '현재카테고리': current_cat,
                '추천카테고리': rec_path,
                '추천ID': rec_id,
                '매칭방식': method,
                '점수': score,
                '상태': 'Mismatch' if is_mismatch else 'OK'
            })
            
            if (i+1) % 500 == 0:
                print(f"[*] Processed {i+1}/{len(df)} products...")

        report_df = pd.DataFrame(results)
        report_df.to_csv(REPORT_FILE, index=False, encoding='utf-8-sig')
        
        mismatched_df = report_df[report_df['상태'] == 'Mismatch']
        print(f"\n✅ Analysis Finished!")
        print(f"   - Total Products: {len(df)}")
        print(f"   - Mismatches Detected: {len(mismatched_df)}")
        print(f"   - Report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    matcher = RefinedMatcher()
    matcher.analyze()
