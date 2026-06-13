import pandas as pd
import time
import os
from naver_commerce_api import NaverCommerceAPI

# 설정
REPORT_FILE = "refined_category_report_v2.csv"
SUCCESS_FILE = "update_success_v2.txt"

def bulk_update_v2(test_id=None, dry_run=False):
    api = NaverCommerceAPI()
    
    if not os.path.exists(REPORT_FILE):
        print(f"[-] Report file not found: {REPORT_FILE}")
        return

    df = pd.read_csv(REPORT_FILE)
    
    # 2단계 보정 성공 상품만 필터링
    targets = df[df['상태'] == 'Fixed (Phase2)']
    
    if test_id:
        targets = targets[targets['상품ID'].astype(str) == str(test_id)]
        if targets.empty:
            print(f"[-] Test ID {test_id} not found in 'Fixed (Phase2)' targets.")
            return
        print(f"[*] Testing with product: {test_id}")
    
    total = len(targets)
    print(f"[*] Total targets for 2nd batch update: {total}")
    if dry_run:
        print("[!] DRY RUN MODE: No actual updates will be performed.")

    success_count = 0
    fail_count = 0
    
    for idx, row in targets.iterrows():
        p_id = str(row['상품ID'])
        # ID 포맷팅 (숫자와 소수점 제거)
        try:
            new_cat_id = str(int(float(row['추천ID'])))
        except:
            new_cat_id = str(row['추천ID'])
            
        p_name = row['상품명']
        
        print(f"\n[{success_count + fail_count + 1}/{total}] Processing: {p_id} ({p_name[:20]}...)")
        print(f"    - New Category ID: {new_cat_id}")
        
        if dry_run:
            success_count += 1
            continue
            
        try:
            # 1. 상세 조회
            detail = api.get_product_detail(p_id)
            if 'originProduct' not in detail:
                print(f"    [-] Failed to get detail: {detail}")
                fail_count += 1
                continue
            
            # 2. 카테고리 업데이트
            origin_product = detail['originProduct']
            origin_product['leafCategoryId'] = new_cat_id
            
            payload = {
                "originProduct": origin_product,
                "smartstoreChannelProduct": detail.get('smartstoreChannelProduct', {})
            }
            
            # 3. PUT 실행
            res = api.put_product(p_id, payload)
            
            if 'originProductNo' in res:
                print(f"    [+] Successfully updated {p_id}")
                success_count += 1
                with open(SUCCESS_FILE, "a") as f:
                    f.write(f"{p_id}\n")
            else:
                print(f"    [-] Update failed: {res}")
                fail_count += 1
                
        except Exception as e:
            print(f"    [!] Error: {e}")
            fail_count += 1
        
        time.sleep(0.5)

    print(f"\n[🏁] Phase 2 Update Finished!")
    print(f"    - Total Success: {success_count}")
    print(f"    - Total Fail: {fail_count}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-id", help="Single product ID to test")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform actual update")
    parser.add_argument("--execute", action="store_true", help="Perform actual bulk update")
    
    args = parser.parse_args()
    
    if args.execute or args.test_id or args.dry_run:
        bulk_update_v2(test_id=args.test_id, dry_run=args.dry_run)
    else:
        print("Usage: python njob_api_bulk_updater_v2.py --execute OR --dry-run")
