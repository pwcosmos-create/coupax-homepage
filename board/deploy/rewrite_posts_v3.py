import sqlite3
from datetime import datetime

DB = "/home/ubuntu/coupax-homepage/board/board.db"

INTRO_SNIPPETS = [
    "시장의 변동성이 커질수록 단순한 감보다 기록 기반 의사결정이 성과를 좌우합니다.",
    "자산관리는 상품 선택보다 현금흐름 설계가 먼저입니다.",
    "좋은 전략도 실행 루틴이 없으면 성과로 이어지지 않습니다.",
    "손실 회피보다 규칙 유지가 장기 성과에 더 큰 영향을 줍니다.",
    "수익률 숫자 하나보다 비용 구조를 먼저 보는 습관이 필요합니다.",
]

EXAMPLE_AMOUNTS = [30, 40, 50, 60, 70, 80]
EXAMPLE_RETURNS = [4, 5, 6, 7, 8, 9]
EXAMPLE_YEARS = [3, 5, 7, 10, 12]


def infer_category(title: str) -> str:
    if any(k in title for k in ("ETF", "주식", "달러")):
        return "ETF·주식"
    if any(k in title for k in ("연금", "퇴직", "노후")):
        return "연금·보험"
    if any(k in title for k in ("세", "소득공제", "연말정산", "ISA")):
        return "절세·세금"
    if any(k in title for k in ("청약", "전세", "월세", "주택")):
        return "부동산·청약"
    if any(k in title for k in ("적금", "예금", "월급날", "비상금")):
        return "적금·예금"
    return "이슈·트렌드"


def category_tips(category: str) -> tuple[str, str, str]:
    if category == "ETF·주식":
        return (
            "지수 분산, 환노출, 총보수 비교를 먼저 확인합니다.",
            "변동성 구간에서는 매수 간격을 고정하고 일시 집중 매수를 피합니다.",
            "지수 추종 오차와 거래량을 함께 보는 습관이 필요합니다.",
        )
    if category == "연금·보험":
        return (
            "세액공제 한도와 인출 조건을 동시에 체크합니다.",
            "상품 수익률보다 수수료와 인출 계획의 정합성이 더 중요합니다.",
            "연금 개시 시점 가정(수명/물가/의료비)을 문서화하세요.",
        )
    if category == "절세·세금":
        return (
            "증빙 누락이 가장 큰 손실 요인입니다.",
            "공제 항목은 소득구간과 요건 충족 여부를 함께 확인해야 합니다.",
            "신고 직전이 아니라 월별 정리 루틴으로 리스크를 줄이세요.",
        )
    if category == "부동산·청약":
        return (
            "청약은 점수 체계와 일정 관리가 핵심입니다.",
            "자금계획 없이 당첨만 목표로 하면 실거주/계약 단계에서 리스크가 커집니다.",
            "규제/대출/세금 변화를 분기마다 재점검하세요.",
        )
    if category == "적금·예금":
        return (
            "목돈 목표와 유동성 목표를 분리해 계좌를 운영합니다.",
            "만기 자금은 한 번에 이동하지 말고 목적별로 분할하세요.",
            "금리보다 실수 방지 자동화(이체/알림)가 장기 성과에 유리합니다.",
        )
    return (
        "이슈성 정보는 기간이 짧아 재검토 주기를 더 짧게 가져가야 합니다.",
        "헤드라인보다 실제 실행비용을 먼저 계산하세요.",
        "단기 트렌드 추종 시 비중 상한선을 사전에 정해두세요.",
    )


def build_post(title: str, category: str, idx: int) -> str:
    intro = INTRO_SNIPPETS[idx % len(INTRO_SNIPPETS)]
    amount = EXAMPLE_AMOUNTS[idx % len(EXAMPLE_AMOUNTS)]
    ret = EXAMPLE_RETURNS[idx % len(EXAMPLE_RETURNS)]
    years = EXAMPLE_YEARS[idx % len(EXAMPLE_YEARS)]
    tip1, tip2, tip3 = category_tips(category)
    today = datetime.now().strftime("%Y-%m-%d")

    q1 = f"{category} 초보가 첫 달에 가장 먼저 해야 할 일은?"
    q2 = "손실/변동 구간에서 계획을 바꾸는 기준은?"
    q3 = "바쁜 직장인이 최소한으로 유지할 점검 루틴은?"

    return f"""[카테고리] {category}

{title}

요약
- {intro}
- 이 글은 {category} 관점에서 실행 가능한 규칙을 제시합니다.
- 목표 수익이 아니라 목표 행동(납입, 분산, 점검)을 기준으로 설계합니다.

1) 시작 전 진단
현재 자금은 소비/예비비/투자 세 바구니로 분리되어 있는지 점검합니다.
분리가 안 되어 있으면 좋은 상품을 고르더라도 중도 해지나 계획 이탈 가능성이 높습니다.

2) 실행 원칙
- 월 납입금은 자동이체로 고정합니다.
- 단기 변동에 따라 납입을 중단하지 않습니다.
- 분기 1회만 성과를 점검해 과도한 매매를 줄입니다.

3) 카테고리별 핵심 포인트
- {tip1}
- {tip2}
- {tip3}

4) 실전 계산 예시
월 {amount}만원을 연 {ret}% 가정으로 {years}년 유지할 때와,
동일 조건에서 총비용이 0.4%p 높은 경우를 비교해 차이를 확인합니다.
이 비교만으로도 '수익률 착시'를 크게 줄일 수 있습니다.

5) 실패를 줄이는 체크리스트
- [ ] 목표 기간(단기/중기/장기) 구분 완료
- [ ] 자동이체 설정 및 실행 확인
- [ ] 자산 비중 상한선 문서화
- [ ] 월말 20분 점검 일정 등록

6) FAQ
Q1. {q1}
A1. 계좌 분리와 자동이체 설정입니다. 상품 선택보다 먼저 해야 합니다.

Q2. {q2}
A2. 사전에 정한 비중 이탈 범위(예: ±5%)를 넘을 때만 조정합니다.

Q3. {q3}
A3. 월말 1회 지출/납입/비중 3가지만 확인해도 성과 편차를 줄일 수 있습니다.

7) 참고 출처
- 국세청: https://www.nts.go.kr
- 금융감독원: https://www.fss.or.kr
- KOSIS: https://kosis.kr
- 정부24: https://www.gov.kr

[업데이트]
본 글은 {today} 기준으로 검토되었습니다.

[면책]
본 글은 일반 정보 제공 목적이며 투자·세무·법률 자문이 아닙니다.
최종 의사결정 책임은 이용자에게 있습니다.
"""


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM posts ORDER BY id ASC")
    rows = cur.fetchall()

    for idx, (post_id, title) in enumerate(rows, start=1):
        category = infer_category(title)
        content = build_post(title, category, idx)
        cur.execute(
            "UPDATE posts SET content = ?, author = ? WHERE id = ?",
            (content, "머니인사이트", post_id),
        )

    conn.commit()
    print(f"rewritten_posts_v3 {len(rows)}")
    conn.close()


if __name__ == "__main__":
    main()
