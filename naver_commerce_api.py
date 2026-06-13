import time
import bcrypt
import pybase64
import requests
import os
from dotenv import load_dotenv

class NaverCommerceAPI:
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")
        self.base_url = "https://api.commerce.naver.com/external"
        self.access_token = None
        self.token_expiry = 0

    def _generate_signature(self, timestamp):
        """
        bcrypt를 이용한 전자서명 생성
        """
        password = f"{self.client_id}_{timestamp}"
        hashed = bcrypt.hashpw(password.encode('utf-8'), self.client_secret.encode('utf-8'))
        return pybase64.standard_b64encode(hashed).decode('utf-8')

    def get_access_token(self):
        """
        OAuth2 토큰 발급 - 발급받은 토큰은 유효시간 동안 재사용
        """
        current_time = time.time()
        if self.access_token and current_time < self.token_expiry - 60:
            return self.access_token

        timestamp = str(int(current_time * 1000))
        signature = self._generate_signature(timestamp)

        url = f"{self.base_url}/v1/oauth2/token"
        data = {
            "client_id": self.client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": "SELF"
        }

        response = requests.post(url, data=data)
        if response.status_code == 200:
            res_json = response.json()
            self.access_token = res_json.get("access_token")
            # expires_in은 초 단위 (보통 3600초)
            self.token_expiry = current_time + res_json.get("expires_in", 3600)
            return self.access_token
        else:
            raise Exception(f"인증 실패: {response.text}")

    def _get_headers(self):
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get_product_list(self, page=1, size=50):
        """
        상품 목록 조회를 위한 검색 API 호출 (POST 방식)
        """
        url = f"{self.base_url}/v1/products/search"
        data = {
            "page": page,
            "size": size
        }
        response = requests.post(url, headers=self._get_headers(), json=data)
        return response.json()

    def get_product_detail(self, origin_product_no):
        """
        원상품 상세 조회 (v2 권장)
        """
        url = f"{self.base_url}/v2/products/origin-products/{origin_product_no}"
        response = requests.get(url, headers=self._get_headers())
        return response.json()

    def put_product(self, origin_product_no, data):
        """
        원상품 전체 수정 (v2)
        카테고리 변경 등을 위해 사용 (전체 필드 포함 필요)
        """
        url = f"{self.base_url}/v2/products/origin-products/{origin_product_no}"
        response = requests.put(url, headers=self._get_headers(), json=data)
        return response.json()

    def update_product_stock(self, origin_product_no, stock_quantity):
        """
        상품 재고 수량 업데이트 (간편 수정 v1)
        """
        url = f"{self.base_url}/v1/products/origin-products/{origin_product_no}/stock"
        data = {
            "stockQuantity": stock_quantity
        }
        response = requests.put(url, headers=self._get_headers(), json=data)
        return response.json()

    def update_product_price(self, origin_product_no, sale_price):
        """
        상품 판매가 업데이트 (간편 수정 v1)
        """
        url = f"{self.base_url}/v1/products/origin-products/{origin_product_no}/sale-price"
        data = {
            "salePrice": sale_price
        }
        response = requests.put(url, headers=self._get_headers(), json=data)
        return response.json()

    def get_root_categories(self):
        """
        최상위 카테고리 목록 조회
        """
        url = f"{self.base_url}/v1/categories"
        response = requests.get(url, headers=self._get_headers())
        res_json = response.json()
        if isinstance(res_json, list):
            return res_json
        return [] # 오류 발생 시 빈 목록 반환

    def get_sub_categories(self, category_id):
        """
        특정 카테고리의 하위 카테고리 목록 조회
        """
        url = f"{self.base_url}/v1/categories/{category_id}/sub-categories"
        response = requests.get(url, headers=self._get_headers())
        res_json = response.json()
        if isinstance(res_json, list):
            return res_json
        return [] # 오류 발생 시 빈 목록 반환

    def delete_product(self, origin_product_no):
        """상품 삭제 (V2)"""
        url = f"{self.base_url}/v2/products/origin-products/{origin_product_no}"
        headers = self._get_headers()
        res = requests.delete(url, headers=headers)
        return res.json() if res.status_code != 204 else {"status": "success"}

if __name__ == "__main__":
    # 테스트 코드
    api = NaverCommerceAPI()
    try:
        token = api.get_access_token()
        print(f"✅ 토큰 발급 성공: {token[:10]}...")
        
        # 상품 목록 첫 페이지 조회 시도
        # products = api.get_product_list()
        # print(f"상품 목록: {products}")
    except Exception as e:
        print(f"❌ 오류: {e}")
        print("\n💡 주의: .env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 입력했는지 확인해 주세요.")
