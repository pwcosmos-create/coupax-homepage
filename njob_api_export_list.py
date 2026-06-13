from naver_commerce_api import NaverCommerceAPI
import csv
import json

def export_product_list(limit=100):
    api = NaverCommerceAPI()
    products = []
    page = 1
    size = 50
    
    print(f">>> Fetching up to {limit} products...")
    
    while len(products) < limit:
        res = api.get_product_list(page=page, size=size)
        contents = res.get('contents', [])
        if not contents:
            break
            
        for item in contents:
            # 원상품 정보 추출
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
            if len(products) >= limit:
                break
        
        page += 1
        if page > res.get('totalPages', 0):
            break

    # CSV 저장
    filename = 'products_list.csv'
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['상품번호', '상품명', '판매가', '상태', '카테고리', '재고', '등록일'])
        writer.writeheader()
        writer.writerows(products)
    
    print(f"✅ Exported {len(products)} products to {filename}")
    return products

if __name__ == "__main__":
    export_product_list(100)
