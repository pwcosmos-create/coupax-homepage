import sqlite3

DB = "/home/ubuntu/coupax-homepage/board/board.db"

IMAGE_MAP = {
    "ETF·주식": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=80",
    "연금·보험": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1400&q=80",
    "절세·세금": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=1400&q=80",
    "부동산·청약": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1400&q=80",
    "적금·예금": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=1400&q=80",
    "이슈·트렌드": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1400&q=80",
}


def infer_category_from_content(content: str) -> str:
    if "[카테고리]" in content:
        first = content.splitlines()[0]
        for category in IMAGE_MAP:
            if category in first:
                return category
    return "이슈·트렌드"


def build_image_html(title: str, category: str, image_url: str) -> str:
    return (
        "<figure class=\"post-image\">"
        f"<img src=\"{image_url}\" alt=\"{title} 관련 대표 이미지\" loading=\"lazy\">"
        f"<figcaption>{category} 실전 가이드 대표 이미지</figcaption>"
        "</figure>"
    )


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, title, content FROM posts ORDER BY id ASC")
    rows = cur.fetchall()
    updated = 0

    for post_id, title, content in rows:
        if "<figure class=\"post-image\">" in content:
            continue
        category = infer_category_from_content(content)
        image_url = IMAGE_MAP.get(category, IMAGE_MAP["이슈·트렌드"])
        image_html = build_image_html(title, category, image_url)
        new_content = f"{image_html}\n\n{content}"
        cur.execute("UPDATE posts SET content = ? WHERE id = ?", (new_content, post_id))
        updated += 1

    conn.commit()
    print(f"images_attached {updated}")
    conn.close()


if __name__ == "__main__":
    main()
