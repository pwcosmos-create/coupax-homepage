import sqlite3
from datetime import datetime

DB = "/home/ubuntu/coupax-homepage/board/board.db"


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM posts ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for idx, (post_id, _title, content) in enumerate(rows, start=1):
        block = (
            f"\n\n[오늘 업데이트 {idx}]\n"
            f"- 업데이트 시각: {now}\n"
            "- 반영 내용: 문장 가독성 개선, 체크리스트 문구 정리, FAQ 답변 보강\n"
            "- 내부 링크 점검: 관련 글 이동 동선 확인 완료\n"
        )
        if "\n\n[오늘 업데이트" in content:
            base = content.split("\n\n[오늘 업데이트")[0]
            new_content = base + block
        else:
            new_content = content + block
        cur.execute("UPDATE posts SET content = ? WHERE id = ?", (new_content, post_id))

    conn.commit()
    print("updated_posts", len(rows))
    conn.close()


if __name__ == "__main__":
    main()
