import pandas as pd
import time
import os
import sys
from naver_commerce_api import NaverCommerceAPI

# 설정
REPORT_FILE = "refined_category_report.csv"
BACKUP_FILE = "products_before_update.csv"
MIN_SCORE = 25 # 25점 미만은 신뢰도가 낮아 업데이트 제외

def bulk_update(test_id=None, dry_run=False):
    api = NaverCommerceAPI()
    
    if not os.path.exists(REPORT_FILE):
        print(f"[-] Report file not found: {REPORT_FILE}")
        return

    df = pd.read_csv(REPORT_FILE)
    
    # 1. 대상 필터링 (상태가 Mismatch이고 점수가 기준 이상인 제품)
    targets = df[(df['상태'] == 'Mismatch') & (df['점수'] >= MIN_SCORE)]
    
    if test_id:
        targets = targets[targets['상품번호'].astype(str) == str(test_id)]
        if targets.empty:
            print(f"[-] Test ID {test_id} not found in mismatch targets with score >= {MIN_SCORE}")
            return
        print(f"[*] Testing with product: {test_id}")
    
    total = len(targets)
    print(f"[*] Total targets for update: {total}")
    if dry_run:
        print("[!] DRY RUN MODE: No actual updates will be performed.")

    success_count = 0
    fail_count = 0
    
    for idx, row in targets.iterrows():
        p_id = str(row['상품번호'])
        # float -> int -> str 변환 (CSV에서 숫자로 읽힐 경우 .0이 붙는 문제 방지)
        try:
            new_cat_id = str(int(float(row['추천ID'])))
        except (ValueError, TypeError):
            new_cat_id = str(row['추천ID'])
            
        p_name = row['상품명']
        
        print(f"\n[{idx+1}/{total}] Processing: {p_id} ({p_name[:20]}...)")
        print(f"    - New Category ID: {new_cat_id}")
        
        if dry_run:
            success_count += 1
            continue
            
        try:
            # 1. 현재 상세 정보 조회 (v2)
            detail = api.get_product_detail(p_id)
            if 'originProduct' not in detail:
                print(f"    [-] Failed to get detail for {p_id}: {detail}")
                fail_count += 1
                continue
            
            # 2. 카테고리 ID 업데이트 및 불필요 필드 제거 (필요 시)
            origin_product = detail['originProduct']
            origin_product['leafCategoryId'] = new_cat_id
            
            # PUT 요청 바디 구성
            payload = {
                "originProduct": origin_product,
                "smartstoreChannelProduct": detail.get('smartstoreChannelProduct', {})
            }
            
            # 3. PUT 업데이트 (v2)
            res = api.put_product(p_id, payload)
            
            if 'originProductNo' in res:
                print(f"    [+] Successfully updated {p_id}")
                success_count += 1
            else:
                print(f"    [-] Update failed for {p_id}: {res}")
                fail_count += 1
                
        except Exception as e:
            print(f"    [!] Error processing {p_id}: {e}")
            fail_count += 1
        
        # API Rate Limit (TPS) 고려
        time.sleep(0.5)

    print(f"\n[🏁] Update Finished!")
    print(f"    - Success: {success_count}")
    print(f"    - Fail: {fail_count}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-id", help="Single product ID to test")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform actual update")
    parser.add_argument("--execute", action="store_true", help="Perform actual bulk update")
    
    args = parser.parse_args()
    
    if args.execute or args.test_id or args.dry_run:
        bulk_update(test_id=args.test_id, dry_run=args.dry_run)
    else:
        print("Usage: python njob_api_bulk_updater.py --test-id [ID] OR --dry-run OR --execute")
