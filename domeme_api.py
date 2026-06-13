import requests
import os
from dotenv import load_dotenv

load_dotenv()

class DomemeAPI:
    def __init__(self):
        self.aid = os.getenv("DOME_API_KEY")
        self.base_url = "https://domeggook.com/ssl/api/"
        if not self.aid:
            raise ValueError("DOME_API_KEY not found in .env")

    def search_product(self, keyword, size=1):
        """
        키워드로 상품 검색 (최초 1건 추천용)
        """
        params = {
            "ver": "4.1",
            "mode": "getItemList",
            "aid": self.aid,
            "market": "dome",
            "om": "json",
            "kw": keyword,
            "sz": size
        }
        try:
            response = requests.get(self.base_url, params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_item_detail(self, item_no):
        """
        상품 번호로 상세 정보 조회 (카테고리 확인용)
        """
        params = {
            "ver": "4.5",
            "mode": "getItemView",
            "aid": self.aid,
            "no": item_no,
            "om": "json"
        }
        try:
            response = requests.get(self.base_url, params=params)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    # 간단한 테스트
    api = DomemeAPI()
    result = api.search_product("마스크")
    if 'domeggook' in result:
        print("[+] API Connection Success!")
        print(f"    Sample Item: {result['domeggook']['list']['item'][0]['title']}")
    else:
        print(f"[-] API Error: {result}")
