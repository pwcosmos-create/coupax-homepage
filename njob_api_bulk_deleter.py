import pandas as pd
import json
import time
import os
from naver_commerce_api import NaverCommerceAPI

# 설정
REPORT_FILE = "refined_category_report_v2.csv"
SUCCESS_FILE = "update_success_v2.txt"
BACKUP_FILE = "njob_deleted_products_backup.json"
DELETE_LOG = "deletion_log.txt"

def run_cleanup(execute=False):
    api = NaverCommerceAPI()
    
    # 1. 대상 53개 ID 추출
    if not os.path.exists(REPORT_FILE) or not os.path.exists(SUCCESS_FILE):
        print("[-] Mapping or success files missing.")
        return

    df = pd.read_csv(REPORT_FILE)
    targets = set(df[df['상태'] == 'Fixed (Phase2)']['상품ID'].astype(str))
    
    with open(SUCCESS_FILE, "r") as f:
        successes = set(f.read().splitlines())
    
    failures = sorted(list(targets - successes))
    total = len(failures)
    
    print(f"[*] Total products to backup and delete: {total}")
    if not execute:
        print("[!] DRY RUN: Only backup will be performed. Use --execute to delete.")

    # 2. 백업 및 삭제 루프
    backup_data = []
    if os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            try:
                backup_data = json.load(f)
            except:
                backup_data = []

    success_del = 0
    fail_del = 0

    for idx, p_id in enumerate(failures):
        print(f"\n[{idx+1}/{total}] Processing: {p_id}")
        
        try:
            # A. 백업 (조회)
            detail = api.get_product_detail(p_id)
            if 'originProduct' in detail:
                backup_data.append(detail)
                # 즉시 저장 (안전)
                with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                print(f"    [+] Backup saved to {BACKUP_FILE}")
            else:
                print(f"    [!] Failed to get detail for backup: {detail}")
            
            # B. 삭제 (실제 실행 시에만)
            if execute:
                res = api.delete_product(p_id)
                if res.get('status') == 'success' or 'originProductNo' in str(res):
                    print(f"    [✔] Successfully deleted from SmartStore")
                    success_del += 1
                    with open(DELETE_LOG, "a") as f:
                        f.write(f"{p_id} - DELETED\n")
                else:
                    print(f"    [✘] Deletion failed: {res}")
                    fail_del += 1
            else:
                print("    [*] Skip deletion (Dry Run)")
                
        except Exception as e:
            print(f"    [!] Error: {e}")
            fail_del += 1
            
        time.sleep(0.5)

    print(f"\n[🏁] Cleanup Finished!")
    print(f"    - Backed up: {len(backup_data)} items (Total in file)")
    if execute:
        print(f"    - Deleted: {success_del}")
        print(f"    - Failed: {fail_del}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Perform actual deletion")
    args = parser.parse_args()
    
    run_cleanup(execute=args.execute)
