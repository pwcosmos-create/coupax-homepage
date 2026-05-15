import sqlite3
from datetime import datetime

DB = "/home/ubuntu/coupax-homepage/board/board.db"


def section_numbers(i: int) -> tuple[int, int, int]:
    base = 3 + (i % 4)
    return base, base + 2, base + 4


def build_content(title: str, category: str, idx: int) -> str:
    v1, v2, v3 = section_numbers(idx)
    now = datetime.now().strftime("%Y-%m-%d")
    return f"""[카테고리] {category}

{title}

핵심 요약
- 이 글은 {category} 영역에서 실제 실행 가능한 판단 기준을 제시합니다.
- 수익률 숫자보다 총비용(세금·수수료·실수 비용) 통제를 우선합니다.
- 오늘 바로 적용할 수 있는 체크리스트와 FAQ를 포함했습니다.

1) 현재 상황 진단
2026년에는 금리와 환율 변동이 동시에 나타나면서, 단일 지표만 보고 의사결정하면 오판 가능성이 커졌습니다.
따라서 목표 기간, 현금흐름, 위험 허용 범위를 먼저 확정한 뒤 전략을 세워야 합니다.

2) 실행 전략
- 목표 기간을 3년/5년/10년으로 나눠 자금 성격을 분리합니다.
- 월 자동이체 금액을 먼저 고정하고, 남는 금액으로 추가 매수를 고려합니다.
- 한 상품 비중이 40%를 넘으면 분산 후보를 검토합니다.
- 성과 평가는 월 단위가 아니라 분기 단위로 진행합니다.

3) 실전 계산 예시
- 월 {v1}0만원 적립, 연 {v2}% 수익률 가정, {v3}년 유지 시 복리 효과를 비교합니다.
- 수수료가 0.3%p만 높아져도 장기 누적 성과는 체감 이상으로 감소합니다.
- 세금 반영 전후 결과를 분리해 보면 의사결정 오류를 줄일 수 있습니다.

4) 리스크 관리 규칙
- 연속 하락 구간에서 추가 매수는 사전 계획 범위 내에서만 진행합니다.
- 손실 자체보다 원칙 이탈(충동 매매)을 더 큰 리스크로 관리합니다.
- 비상자금 3~6개월은 투자 자금과 반드시 분리합니다.

5) 체크리스트
- [ ] 이번 달 자동이체 정상 실행 확인
- [ ] 상품별 비중 점검
- [ ] 최근 1개월 지출 변동 반영
- [ ] 과도한 낙관/비관 시나리오 제거

6) FAQ
Q1. 지금 시작하면 늦나요?
A1. 늦고 빠름보다 중요한 것은 납입 지속성과 비용 통제입니다.

Q2. 수익률이 낮은데 계속해야 하나요?
A2. 단기 수익률보다 계획 대비 실행률(납입, 분산, 재점검)을 먼저 확인하세요.

Q3. 초보자에게 가장 중요한 한 가지는?
A3. 목표 기간별 자금 분리입니다. 이 원칙 하나로 실수 대부분을 줄일 수 있습니다.

7) 참고 출처
- 국세청: https://www.nts.go.kr
- 금융감독원: https://www.fss.or.kr
- KOSIS 국가통계포털: https://kosis.kr
- 정부24: https://www.gov.kr

[콘텐츠 업데이트]
본 문서는 {now} 기준으로 재점검되었습니다. 제도 변경 시 후속 업데이트를 반영합니다.

[면책]
본 글은 일반 정보 제공 목적이며 투자·세무·법률 자문이 아닙니다. 최종 결정 책임은 이용자에게 있습니다.
"""


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


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM posts ORDER BY id ASC")
    rows = cur.fetchall()

    for idx, (post_id, title) in enumerate(rows, start=1):
        category = infer_category(title)
        content = build_content(title, category, idx)
        cur.execute("UPDATE posts SET content = ?, author = ? WHERE id = ?", (content, "머니인사이트", post_id))

    conn.commit()
    print(f"rewritten_posts {len(rows)}")
    conn.close()


if __name__ == "__main__":
    main()
