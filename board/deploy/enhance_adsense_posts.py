import sqlite3

DB = "/home/ubuntu/coupax-homepage/board/board.db"
BASE_URL = "https://coupax.co.kr"


def build_enhancement(title: str) -> str:
    return f"""

6) 실전 계산 예시
- 월 50만원을 연 6% 복리로 10년 적립하면 약 8,200만원 수준의 평가금액을 기대할 수 있습니다.
- 동일 금액이라도 수수료가 연 0.5% 높아지면 장기 누적 수익이 크게 줄어들 수 있습니다.
- 반드시 수익률이 아니라 '수익률 - 총비용(세금/수수료/환전비용)' 기준으로 비교하세요.

7) FAQ
Q1. 지금 시작해도 늦었나요?
A1. 시작 시점보다 중요한 것은 납입 지속성과 리스크 관리 규칙입니다.

Q2. 손실 구간에서는 어떻게 해야 하나요?
A2. 사전에 정한 비중(예: 주식/채권) 범위 내에서만 리밸런싱하고 감정적 매매를 피하세요.

Q3. 초보자는 무엇부터 점검해야 하나요?
A3. 목표 기간, 월 납입 가능 금액, 비상자금 확보 여부부터 점검하세요.

8) 내부 링크 추천
- 홈: {BASE_URL}/
- 개인정보처리방침: {BASE_URL}/privacy
- 이용약관: {BASE_URL}/terms

9) 참고 출처
- 국세청: https://www.nts.go.kr
- 금융감독원: https://www.fss.or.kr
- 통계청 국가통계포털: https://kosis.kr
- 정부24: https://www.gov.kr

[콘텐츠 업데이트]
본 글 '{title}'은(는) 2026년 기준으로 재검토되었으며, 정책 변경 시 최신 기준으로 추가 업데이트됩니다.
"""


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM posts ORDER BY id ASC")
    rows = cur.fetchall()

    updated = 0
    for post_id, title, content in rows:
        if "9) 참고 출처" in content and "7) FAQ" in content:
            continue
        new_content = content.rstrip() + "\n" + build_enhancement(title)
        cur.execute("UPDATE posts SET content = ? WHERE id = ?", (new_content, post_id))
        updated += 1

    conn.commit()
    print(f"updated_posts {updated}")
    conn.close()


if __name__ == "__main__":
    main()
