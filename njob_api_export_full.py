from naver_commerce_api import NaverCommerceAPI
import csv
import json
import time

def export_full_product_list():
    api = NaverCommerceAPI()
    products = []
    page = 1
    size = 50 # 최대 500까지 가능하지만, 안정성을 위해 50~100 권장
    
    print(f">>> Fetching all products via Naver Commerce API...")
    
    first_res = api.get_product_list(page=1, size=size)
    total_elements = first_res.get('totalElements', 0)
    total_pages = first_res.get('totalPages', 0)
    
    print(f"[*] Total Products to fetch: {total_elements} ({total_pages} pages)")
    
    # 첫 페이지 결과 처리
    contents = first_res.get('contents', [])
    for item in contents:
        origin_no = item.get('originProductNo')
        channel_info = item.get('channelProducts', [{}])[0]
        products.append({
            '상품번호': origin_no,
            '상품명': channel_info.get('name'),
            '판매가': channel_info.get('salePrice'),
            '상태': channel_info.get('statusType'),
            '카테고리': channel_info.get('wholeCategoryName'),
            '재고': channel_info.get('stockQuantity'),
            '등록일': channel_info.get('regDate')
        })

    # 나머지 페이지 처리
    for p in range(2, total_pages + 1):
        print(f"[*] Fetching page {p}/{total_pages}...")
        res = api.get_product_list(page=p, size=size)
        contents = res.get('contents', [])
        if not contents:
            break
            
        for item in contents:
            origin_no = item.get('originProductNo')
            channel_info = item.get('channelProducts', [{}])[0]
            products.append({
                '상품번호': origin_no,
                '상품명': channel_info.get('name'),
                '판매가': channel_info.get('salePrice'),
                '상태': channel_info.get('statusType'),
                '카테고리': channel_info.get('wholeCategoryName'),
                '재고': channel_info.get('stockQuantity'),
                '등록일': channel_info.get('regDate')
            })
        
        # API 레이트 리밋 방지를 위한 미세 대기
        time.sleep(0.1)

    # CSV 저장
    filename = 'products_list_full.csv'
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['상품번호', '상품명', '판매가', '상태', '카테고리', '재고', '등록일'])
        writer.writeheader()
        writer.writerows(products)
    
    print(f"✅ Successfully exported all {len(products)} products to {filename}")
    return products

if __name__ == "__main__":
    export_full_product_list()
