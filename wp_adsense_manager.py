import argparse
import os
from dataclasses import dataclass

import requests


@dataclass
class Config:
    wp_url: str
    wp_username: str
    wp_app_password: str
    contact_email: str


def load_config() -> Config:
    load_local_env_file()
    wp_url = os.environ.get("WP_URL", "").strip()
    wp_username = os.environ.get("WP_USERNAME", "").strip()
    wp_app_password = os.environ.get("WP_APP_PASSWORD", "").strip()
    contact_email = os.environ.get("SITE_CONTACT_EMAIL", "admin@coupax.co.kr").strip()

    missing = [
        key
        for key, value in (
            ("WP_URL", wp_url),
            ("WP_USERNAME", wp_username),
            ("WP_APP_PASSWORD", wp_app_password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. "
            "Set them before running this script."
        )
    return Config(wp_url, wp_username, wp_app_password, contact_email)


def load_local_env_file() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


def upsert_page(session: requests.Session, pages_api_url: str, title: str, content: str) -> None:
    items = []
    query = session.get(
        pages_api_url,
        params={"search": title, "per_page": 20, "context": "edit"},
        timeout=20,
    )
    if query.status_code == 200:
        items = query.json()
    else:
        print(f"[WARN] page lookup failed ({query.status_code}), creating page: {title}")
    target = next((item for item in items if item.get("title", {}).get("rendered", "").strip() == title), None)
    payload = {"title": title, "content": content, "status": "publish"}

    if target:
        page_id = target["id"]
        res = session.post(f"{pages_api_url}/{page_id}", json=payload, timeout=20)
        res.raise_for_status()
        print(f"[UPDATED] {title} (id={page_id})")
    else:
        res = session.post(pages_api_url, json=payload, timeout=20)
        res.raise_for_status()
        page_id = res.json()["id"]
        print(f"[CREATED] {title} (id={page_id})")


def ensure_essential_pages(cfg: Config) -> None:
    pages_api_url = f"{cfg.wp_url}/pages"
    session = requests.Session()
    session.auth = (cfg.wp_username, cfg.wp_app_password)

    pages = {
        "사이트 소개 (About)": f"""
        <h2>머니인사이트 소개</h2>
        <p>머니인사이트는 ETF, 연금, 청약, 절세 정보를 실무 관점으로 정리하는 금융 정보 블로그입니다.</p>
        <p>모든 글은 독자가 실제 의사결정에 활용할 수 있도록 근거 출처와 계산 기준을 함께 제공합니다.</p>
        <p>문의: {cfg.contact_email}</p>
        """,
        "문의하기 (Contact)": f"""
        <h2>문의하기</h2>
        <p>콘텐츠 오류, 정정 요청, 협업 문의는 아래 이메일로 보내주세요.</p>
        <p>Email: {cfg.contact_email}</p>
        <p>원칙적으로 2영업일 내 답변합니다.</p>
        """,
        "개인정보처리방침 (Privacy Policy)": """
        <h2>개인정보처리방침</h2>
        <p>본 사이트는 서비스 운영 및 광고 게재를 위해 쿠키를 사용할 수 있습니다.</p>
        <p>Google 등 제3자 공급업체는 쿠키를 사용해 맞춤형 광고를 제공할 수 있습니다.</p>
        <p>사용자는 브라우저 설정을 통해 쿠키를 차단하거나 삭제할 수 있습니다.</p>
        <p>수집된 정보는 관련 법령에 따라 안전하게 관리합니다.</p>
        """,
        "이용약관 (Terms)": """
        <h2>이용약관</h2>
        <p>본 사이트의 정보는 투자 권유가 아닌 일반 정보 제공 목적입니다.</p>
        <p>콘텐츠를 근거로 한 투자 결과에 대한 최종 책임은 사용자에게 있습니다.</p>
        <p>무단 전재 및 재배포는 금지되며, 인용 시 출처를 명시해야 합니다.</p>
        """,
    }

    for title, content in pages.items():
        upsert_page(session, pages_api_url, title, content)


def publish_sample_post(cfg: Config) -> None:
    posts_api_url = f"{cfg.wp_url}/posts"
    session = requests.Session()
    session.auth = (cfg.wp_username, cfg.wp_app_password)

    title = "2026년 종합소득세 신고 전 반드시 확인할 7가지 체크리스트"
    content = """
    <h2>핵심 요약</h2>
    <p>종합소득세 신고에서 가장 많이 누락되는 항목은 필요경비, 공제 요건, 증빙 정리입니다.</p>
    <h2>1) 신고 대상 소득 확인</h2>
    <p>근로소득 외 사업/기타/금융소득이 있는지 먼저 구분합니다.</p>
    <h2>2) 경비 증빙 정리</h2>
    <p>카드내역, 세금계산서, 현금영수증을 용도별로 분류합니다.</p>
    <h2>3) 공제 누락 점검</h2>
    <p>연금계좌, 보험료, 기부금, 의료비 등 공제 항목을 다시 확인합니다.</p>
    <h2>4) 가산세 리스크 점검</h2>
    <p>무신고/과소신고 가능성이 있는 항목은 선제 정정합니다.</p>
    <h2>5) 납부 계획 수립</h2>
    <p>납부기한과 분할납부 가능 여부를 확인해 현금흐름을 관리합니다.</p>
    <h2>6) 신고 후 보관</h2>
    <p>주요 증빙자료는 최소 5년 보관을 권장합니다.</p>
    <h2>7) 업데이트 추적</h2>
    <p>세법 개정사항을 반영해 기존 글도 주기적으로 업데이트합니다.</p>
    <hr/>
    <p><strong>면책:</strong> 본 글은 일반 정보 제공이며 개인별 세무 자문이 아닙니다.</p>
    """
    payload = {"title": title, "content": content, "status": "publish"}
    res = session.post(posts_api_url, json=payload, timeout=20)
    res.raise_for_status()
    post_id = res.json()["id"]
    print(f"[CREATED] sample post id={post_id}")


def print_adsense_checklist() -> None:
    print("\n=== Adsense Submission Checklist ===")
    checklist = [
        "필수 페이지 4개(소개/문의/개인정보/약관) 공개 상태",
        "최근 30일 내 발행/수정된 원본 글 20개 이상",
        "모바일/PC에서 메뉴 및 내부링크 정상 동작",
        "도메인 HTTPS 정상 + robots/sitemap 점검",
        "애드센스 스크립트가 <head>에 1회만 삽입됨",
        "Google Search Console 소유권 확인 완료",
    ]
    for idx, item in enumerate(checklist, 1):
        print(f"{idx}. {item}")
    print("====================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare WordPress site for Adsense review.")
    parser.add_argument(
        "--create-sample-post",
        action="store_true",
        help="Create one sample long-form post.",
    )
    args = parser.parse_args()

    cfg = load_config()
    ensure_essential_pages(cfg)
    if args.create_sample_post:
        publish_sample_post(cfg)
    print_adsense_checklist()
    print("[DONE] Essential Adsense setup tasks completed.")


if __name__ == "__main__":
    main()
