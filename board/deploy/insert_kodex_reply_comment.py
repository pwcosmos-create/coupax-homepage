"""One-off: insert blog comment on production (run on server)."""
import random
import sqlite3
from datetime import datetime

DB = "/home/ubuntu/coupax-homepage/board/board.db"
NICKS = [
    "산책하는북스", "커피한잔", "동네고양이", "숫자9", "비오는날", "탐험R",
    "파도보기", "구름위", "새벽공기", "투자새내기", "우체통12", "책읽기0",
    "겨울햇살", "코드노트", "퇴근길7", "은하수3", "창가자리", "걷기좋은날",
]

CONTENT = """안녕하세요. 질문 주신 **Kodex 미국배당커버드콜액티브(종목코드 441640)**는, 미국 **배당주**에 더해 **커버드콜(보유 주식에 대한 콜옵션 매도)** 전략을 사용하는 ETF입니다. 옵션에서 나오는 **프리미엄**과 주식 **배당·분배**를 함께 활용해, 상대적으로 **분배 현금흐름**을 중시하는 구조로 이해하시면 됩니다.

**장점으로 많이 이야기되는 점**
- 분배·옵션 프리미엄이 맞물리면 **월 단위 분배 규모가 크게 느껴질 수** 있습니다.
- 변동성이 있는 시기에는 옵션 프리미엄이 일정 부분 **완충** 역할을 할 수도 있습니다(시장 상황에 따라 다름).

**꼭 같이 보셔야 할 점**
- 주가가 **크게 오르는 구간**에서는 이미 매도해 둔 콜 때문에 **상승 참여가 제한**될 수 있습니다. “배당만 크면 된다”고 보기 어렵고, **주가 변동**과 함께 봐야 합니다.
- 분배금은 **운용·시장·옵션 구조**에 따라 달라질 수 있어, 과거·시트 수치만으로 미래를 단정할 수는 없습니다.
- **세금(배당·분배 소득 등)**·계좌 종류(ISA 등)도 본인 기준으로 확인이 필요합니다.

**사이트 월배당 시트 참고(투자 권유 아님)**
국내 상장 월·월중 분배 ETF 목록에 포함돼 있고, 갱신 시점의 **월별 분배·누적 배당수익률·YTD**는 참고용입니다. **최종 확인은 운용사 공시·간이투자설명서·KRX**를 보시는 것이 좋습니다.

위 내용은 **일반적인 설명**이며 특정 매수·매도를 권하는 것은 아닙니다. 더 궁금한 점이 있으면 구체적으로 남겨 주세요."""

# Markdown ** stripped for plain display - actually view uses | replace('\n','<br>') not markdown
# User content had ** for bold - the template doesn't render markdown. I'll use plain text without **

CONTENT_PLAIN = CONTENT.replace("**", "")

PASSWORD = "coupax-bot-" + "".join(random.choice("0123456789abcdef") for _ in range(8))


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, title FROM posts WHERE title LIKE '%Kodex%' AND title LIKE '%커버드%' ORDER BY id DESC"
    ).fetchall()
    if not rows:
        rows = cur.execute(
            "SELECT id, title FROM posts WHERE title LIKE '%미국배당%' AND title LIKE '%커버드%' ORDER BY id DESC"
        ).fetchall()
    if not rows:
        rows = cur.execute(
            "SELECT id, title FROM posts ORDER BY id DESC LIMIT 5"
        ).fetchall()
        print("No exact match; latest posts:")
        for r in rows:
            print(r["id"], r["title"][:60])
        conn.close()
        return 1
    pid = rows[0]["id"]
    title = rows[0]["title"]
    author = random.choice(NICKS)
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur.execute(
        "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
        (pid, author, CONTENT_PLAIN, PASSWORD, created),
    )
    conn.commit()
    conn.close()
    print("OK post_id=", pid)
    print("title=", title[:80])
    print("author=", author)
    print("comment_password_for_delete=", PASSWORD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
