from naver_commerce_api import NaverCommerceAPI
import json

def get_product_count():
    api = NaverCommerceAPI()
    try:
        response = api.get_product_list()
        # Full response for debugging
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        total = response.get('total', 0)
        print(f"\n>>> Total Products: {total}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_product_count()
