import sqlite3
from datetime import datetime

DB = "/home/ubuntu/coupax-homepage/board/board.db"

SEO_TITLES = [
    "ETF 적립식 투자 방법: 2026년 월 50만원 분할매수 전략",
    "연금저축 IRP 차이: 세액공제 최대화하는 배분 비율",
    "종합소득세 신고 방법: 프리랜서 필요경비 정리 가이드",
    "청약통장 점수 올리는 법: 무주택자 실전 준비 체크리스트",
    "적금 만기 자금 운용법: 금리 하락기 목돈 굴리기 전략",
    "ISA 절세 방법: 계좌 운용으로 세금 줄이는 포트폴리오",
    "국민연금 수령시기 계산: 조기수령 vs 연기수령 비교",
    "달러 투자 방법: 환율 변동기 리스크 관리 기준",
    "퇴직연금 DC형 운용법: 수익률 높이는 리밸런싱 규칙",
    "전세 월세 비교 계산: 현금흐름 기준 주거비 의사결정",
    "고배당 ETF 투자 주의점: 분배율 착시 피하는 방법",
    "연말정산 카드공제 계산: 신용카드 체크카드 사용 비율",
    "주택청약 특별공급 조건: 자격요건과 서류 준비 방법",
    "비상금 통장 만들기: 생활비 계좌 분리와 자동이체 전략",
    "해외 ETF 세금 정리: 환전비용 포함 실수익 계산법",
    "근로소득자 종합소득세 신고: 추가신고 필요한 경우 정리",
    "노후자금 계산법: 연금과 개인투자 통합 설계 방법",
    "청년형 소득공제 장기펀드: 가입조건과 절세 포인트",
    "주식 하락장 대응법: 멘탈 관리와 매매원칙 세우기",
    "월급 재테크 자동화: 자동이체 5개로 돈 관리하는 방법",
]


def infer_category(title: str) -> str:
    if any(k in title for k in ("ETF", "주식", "달러")):
        return "ETF·주식"
    if any(k in title for k in ("연금", "퇴직", "노후")):
        return "연금·보험"
    if any(k in title for k in ("세", "소득공제", "연말정산", "ISA")):
        return "절세·세금"
    if any(k in title for k in ("청약", "전세", "월세", "주택")):
        return "부동산·청약"
    if any(k in title for k in ("적금", "예금", "월급", "비상금")):
        return "적금·예금"
    return "이슈·트렌드"


def keyword_bundle(title: str, category: str) -> tuple[str, str, str]:
    if category == "ETF·주식":
        return ("etf 투자 방법", "분할매수, 리밸런싱, 총보수", "초보 투자자")
    if category == "연금·보험":
        return ("연금 절세 전략", "세액공제, 수령시기, 인출계획", "직장인/은퇴 준비자")
    if category == "절세·세금":
        return ("세금 줄이는 방법", "종합소득세, 공제항목, 증빙", "근로소득자/프리랜서")
    if category == "부동산·청약":
        return ("청약 준비 방법", "자격요건, 점수, 자금계획", "무주택 실수요자")
    if category == "적금·예금":
        return ("목돈 관리 방법", "만기자금, 비상금, 자동이체", "사회초년생/가정")
    return ("재테크 이슈 정리", "시장변동, 리스크관리, 실행루틴", "일반 독자")


def build_content(title: str, category: str, idx: int) -> str:
    main_kw, sub_kw, audience = keyword_bundle(title, category)
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""[카테고리] {category}

{title}

SEO 요약 스니펫
이 글은 '{main_kw}'을 검색한 독자를 위해 작성되었습니다. 핵심은 {sub_kw}이며, {audience}가 바로 실행할 수 있는 기준을 제공합니다.

핵심 키워드
- 메인 키워드: {main_kw}
- 서브 키워드: {sub_kw}
- 검색 의도: 정보 탐색 + 실행 가이드

1) 검색 의도 기반 핵심 정리
많은 독자가 단기 수익 숫자만 찾다가 실제 실행 기준을 놓칩니다. 이 글은 검색 후 바로 적용할 수 있도록 점검 순서를 먼저 제시합니다.

2) 실행 원칙
- 목표 기간을 분리하고 자금 성격을 구분합니다.
- 자동이체와 점검 루틴으로 실행률을 높입니다.
- 총비용(수수료/세금/환전비용)을 반영해 비교합니다.

3) 실전 계산 예시
월 납입금, 예상 수익률, 기간을 고정한 뒤 비용 차이 0.3~0.5%p가 장기 성과에 주는 영향을 비교합니다.
수익률만 높은 선택보다 비용 통제가 되는 선택이 누적 성과에서 유리합니다.

4) 체크리스트
- [ ] 이번 달 자동이체 실행 확인
- [ ] 자산 비중 상한선 준수
- [ ] 지출 변동 반영
- [ ] 분기 점검 일정 등록

5) FAQ
Q1. {main_kw}을 시작할 때 가장 먼저 할 일은?
A1. 목표 기간과 월 납입 가능 금액을 먼저 확정해야 합니다.

Q2. 수익률이 기대보다 낮으면 중단해야 하나요?
A2. 단기 성과보다 실행률과 비용 통제가 유지되는지 먼저 확인하세요.

Q3. 초보자가 피해야 할 실수는?
A3. 한 상품 집중, 잦은 매매, 증빙 누락입니다.

6) 참고 출처
- 국세청: https://www.nts.go.kr
- 금융감독원: https://www.fss.or.kr
- KOSIS: https://kosis.kr
- 정부24: https://www.gov.kr

[업데이트]
본 문서는 {today} 기준으로 SEO 및 내용 품질을 재검토했습니다.

[면책]
본 글은 일반 정보 제공 목적이며 투자·세무·법률 자문이 아닙니다.
"""


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM posts ORDER BY id ASC")
    rows = cur.fetchall()

    for idx, (post_id, old_title) in enumerate(rows):
        new_title = SEO_TITLES[idx] if idx < len(SEO_TITLES) else old_title
        category = infer_category(new_title)
        content = build_content(new_title, category, idx)
        cur.execute(
            "UPDATE posts SET title = ?, content = ?, author = ? WHERE id = ?",
            (new_title, content, "머니인사이트", post_id),
        )

    conn.commit()
    print(f"rewritten_posts_v4 {len(rows)}")
    conn.close()


if __name__ == "__main__":
    main()
