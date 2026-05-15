from flask import Flask, render_template, request, redirect, url_for, flash, g, Response
import json
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "board-secret-key-2026")


@app.template_filter("intcomma")
def intcomma_filter(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


DB_PATH = os.environ.get(
    "BOARD_DB_PATH",
    os.path.join(os.path.dirname(__file__), "board.db"),
)
SITE_NAME = os.environ.get("SITE_NAME", "머니인사이트")
SITE_CONTACT_EMAIL = os.environ.get("SITE_CONTACT_EMAIL", "admin@coupax.co.kr")
ADSENSE_CLIENT = os.environ.get("ADSENSE_CLIENT", "").strip()

# 시드 글 등 본문에 붙는 카테고리 태그 (deploy/seed_adsense_posts.py 와 동일)
ETF_CATEGORY_MARKER = "[카테고리] ETF·주식"
ETF_THEME_ORDER = (
    "월배당·현금흐름",
    "적립식·매수·리스크",
    "해외·환율·글로벌",
    "배당·분배금",
    "세금·비용·계좌",
    "기타 ETF 주제",
)

# 배당·종목 조회 등 외부 참고(제3자 서비스, 내용·가용성은 해당 사이트 기준).
ETF_EXTERNAL_LINKS = (
    {
        "title": "Search ETF — 최근 배당",
        "url": "https://search-etf.com/recent_dividend.php",
        "description": "ETF 분배·배당 흐름을 한눈에 보기 좋은 국내형 조회 화면으로 자주 쓰입니다.",
    },
    {
        "title": "ETF CHECK",
        "url": "https://www.etfcheck.co.kr/mobile/main",
        "description": "상장 ETF 검색·시세·구성 등 모바일 중심 ETF 정보 허브입니다.",
    },
)


def load_monthly_dividend_sheet():
    """스프레드시트 형식 월배당 데이터(JSON). 파일이 없거나 오류 시 빈 시트."""
    path = os.path.join(os.path.dirname(__file__), "data", "monthly_dividend_etfs.json")
    if not os.path.isfile(path):
        return {
            "year": 2026,
            "rows": [],
            "dividend_unit": "",
            "note": "",
            "pipeline_note": "",
            "data_sources": [],
        }
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {
                "year": 2026,
                "rows": [],
                "dividend_unit": "",
                "note": "",
                "pipeline_note": "",
                "data_sources": [],
            }
        data.setdefault("year", 2026)
        data.setdefault("rows", [])
        data.setdefault("dividend_unit", "")
        data.setdefault("note", "")
        data.setdefault("pipeline_note", "")
        data.setdefault("data_sources", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {
            "year": 2026,
            "rows": [],
            "dividend_unit": "",
            "note": "",
            "pipeline_note": "",
            "data_sources": [],
        }


def fetch_etf_related_posts(db):
    """제목·본문의 ETF 언급 또는 시드 카테고리 태그로 관련 글 수집."""
    return db.execute(
        """
        SELECT * FROM posts
        WHERE content LIKE ?
           OR instr(lower(title), 'etf') > 0
           OR instr(lower(content), 'etf') > 0
        ORDER BY id DESC
        """,
        (f"%{ETF_CATEGORY_MARKER}%",),
    ).fetchall()


def extract_post_keywords_line(content: str) -> str:
    """시드 글의 [키워드] 블록 첫 줄 — 본문 공통 면책 문구와 섞이지 않게 분류에만 사용."""
    if not content or "[키워드]" not in content:
        return ""
    tail = content.split("[키워드]", 1)[1]
    for line in tail.splitlines():
        s = line.strip()
        if s and not s.startswith("["):
            return s
    return ""


def classify_etf_theme(title: str, content: str) -> str:
    blob = f"{title}\n{extract_post_keywords_line(content)}"
    if "월배당" in blob or "월 배당" in blob:
        return "월배당·현금흐름"
    if any(
        k in blob
        for k in (
            "적립",
            "매수 규칙",
            "분할매수",
            "손실",
            "리밸런싱",
            "낙폭",
            "DCA",
        )
    ):
        return "적립식·매수·리스크"
    if any(
        k in blob
        for k in (
            "해외ETF",
            "해외 ETF",
            "미국",
            "S&P",
            "나스닥",
            "달러",
            "환전",
            "환율",
            "글로벌",
            "환헤지",
        )
    ):
        return "해외·환율·글로벌"
    if "배당" in blob or "분배" in blob:
        return "배당·분배금"
    if any(
        k in blob
        for k in (
            "세금",
            "과세",
            "ISA",
            "양도",
            "절세",
            "소득세",
            "배당소득",
        )
    ):
        return "세금·비용·계좌"
    return "기타 ETF 주제"


def group_etf_posts_by_theme(rows):
    buckets = {k: [] for k in ETF_THEME_ORDER}
    for row in rows:
        theme = classify_etf_theme(row["title"], row["content"])
        if theme not in buckets:
            theme = "기타 ETF 주제"
        buckets[theme].append(row)
    return [(k, buckets[k]) for k in ETF_THEME_ORDER if buckets[k]]


def fetch_monthly_dividend_posts(db):
    return db.execute(
        """
        SELECT * FROM posts
        WHERE title LIKE '%월배당%'
           OR content LIKE '%월배당%'
           OR title LIKE '%월 배당%'
           OR content LIKE '%월 배당%'
        ORDER BY id DESC
        """
    ).fetchall()


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                title    TEXT NOT NULL,
                author   TEXT NOT NULL,
                content  TEXT NOT NULL,
                password TEXT NOT NULL,
                views    INTEGER DEFAULT 0,
                created  TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id  INTEGER NOT NULL,
                author   TEXT NOT NULL,
                content  TEXT NOT NULL,
                password TEXT NOT NULL,
                created  TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')
        db.commit()


@app.context_processor
def inject_site_settings():
    return {
        "site_name": SITE_NAME,
        "site_contact_email": SITE_CONTACT_EMAIL,
        "adsense_client": ADSENSE_CLIENT,
    }


# ── 홈(랜딩) / 블로그 목록 / ETF 허브 ─────────────────────────────────────────
def _blog_list_context():
    """글 목록·검색·페이지네이션에 필요한 값만 계산."""
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    per_page = 15
    db = get_db()
    if q:
        total = db.execute(
            "SELECT COUNT(*) FROM posts WHERE title LIKE ? OR author LIKE ?",
            (f"%{q}%", f"%{q}%"),
        ).fetchone()[0]
        posts = db.execute(
            "SELECT * FROM posts WHERE title LIKE ? OR author LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (f"%{q}%", f"%{q}%", per_page, (page - 1) * per_page),
        ).fetchall()
    else:
        total = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        posts = db.execute(
            "SELECT * FROM posts ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page),
        ).fetchall()
    total_pages = (total + per_page - 1) // per_page
    return {
        "posts": posts,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "q": q,
    }


@app.route("/")
def index():
    """메인 랜딩. 예전 북마크용 `/?page=`·`?q=` 는 블로그로 넘깁니다."""
    if request.args.get("page") is not None or request.args.get("q", "").strip():
        safe = {}
        p = request.args.get("page", type=int)
        if p is not None and p > 0:
            safe["page"] = p
        qv = request.args.get("q", "").strip()
        if qv:
            safe["q"] = qv
        return redirect(url_for("blog", **safe))
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    return render_template("home.html", total=total)


@app.route("/blog")
def blog():
    ctx = _blog_list_context()
    return render_template("blog.html", **ctx)


# ── 글쓰기 ────────────────────────────────────────────────────────────────────
@app.route('/write', methods=['GET', 'POST'])
def write():
    if request.method == 'POST':
        title   = request.form['title'].strip()
        author  = request.form['author'].strip()
        content = request.form['content'].strip()
        password = request.form['password']

        if not all([title, author, content, password]):
            flash('모든 항목을 입력해주세요.', 'error')
            return render_template('write.html')

        db = get_db()
        db.execute(
            "INSERT INTO posts (title, author, content, password, created) VALUES (?,?,?,?,?)",
            (title, author, content, password, datetime.now().strftime('%Y-%m-%d %H:%M'))
        )
        db.commit()
        flash('게시글이 등록되었습니다.', 'success')
        return redirect(url_for('blog'))

    return render_template('write.html')


# ── 상세보기 ──────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>')
def view(post_id):
    db = get_db()
    db.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
    db.commit()

    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        flash('존재하지 않는 게시글입니다.', 'error')
        return redirect(url_for('blog'))

    comments = db.execute(
        "SELECT * FROM comments WHERE post_id = ? ORDER BY id ASC", (post_id,)
    ).fetchall()
    related_posts = db.execute(
        "SELECT id, title, created FROM posts WHERE id != ? ORDER BY id DESC LIMIT 4",
        (post_id,),
    ).fetchall()
    return render_template(
        'view.html',
        post=post,
        comments=comments,
        related_posts=related_posts,
    )


# ── 수정 ──────────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return redirect(url_for('blog'))

    if request.method == 'POST':
        password = request.form['password']
        if password != post['password']:
            flash('비밀번호가 틀렸습니다.', 'error')
            return render_template('edit.html', post=post)

        title   = request.form['title'].strip()
        content = request.form['content'].strip()
        if not all([title, content]):
            flash('제목과 내용을 입력해주세요.', 'error')
            return render_template('edit.html', post=post)

        db.execute(
            "UPDATE posts SET title=?, content=? WHERE id=?",
            (title, content, post_id)
        )
        db.commit()
        flash('수정되었습니다.', 'success')
        return redirect(url_for('view', post_id=post_id))

    return render_template('edit.html', post=post)


# ── 삭제 ──────────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete(post_id):
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return redirect(url_for('blog'))

    password = request.form.get('password', '')
    if password != post['password']:
        flash('비밀번호가 틀렸습니다.', 'error')
        return redirect(url_for('view', post_id=post_id))

    db.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash('게시글이 삭제되었습니다.', 'success')
    return redirect(url_for('blog'))


# ── 댓글 등록 ─────────────────────────────────────────────────────────────────
@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    author  = request.form['author'].strip()
    content = request.form['content'].strip()
    password = request.form['password']

    if not all([author, content, password]):
        flash('댓글 항목을 모두 입력해주세요.', 'error')
        return redirect(url_for('view', post_id=post_id))

    db = get_db()
    db.execute(
        "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
        (post_id, author, content, password, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    db.commit()
    return redirect(url_for('view', post_id=post_id))


# ── 댓글 삭제 ─────────────────────────────────────────────────────────────────
@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    db = get_db()
    comment = db.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
    if not comment:
        return redirect(url_for('blog'))

    post_id = comment['post_id']
    password = request.form.get('password', '')
    if password != comment['password']:
        flash('비밀번호가 틀렸습니다.', 'error')
    else:
        db.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        db.commit()

    return redirect(url_for('view', post_id=post_id))


@app.route('/products/etf-data')
def data_product_etf():
    """ETF 정보 수집·재가공·제공(라이선스) 모델 소개(베타)."""
    return render_template('data_product_etf.html')


@app.route('/etf')
def etf_hub():
    db = get_db()
    etf_posts = fetch_etf_related_posts(db)
    return render_template(
        'etf_hub.html',
        etf_posts=etf_posts,
        themed_posts=group_etf_posts_by_theme(etf_posts),
        monthly_posts=fetch_monthly_dividend_posts(db),
        dividend_sheet=load_monthly_dividend_sheet(),
        etf_external_links=ETF_EXTERNAL_LINKS,
        etf_count=len(etf_posts),
    )


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/robots.txt')
def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap():
    db = get_db()
    posts = db.execute("SELECT id, created FROM posts ORDER BY id DESC LIMIT 500").fetchall()
    pages = [
        url_for('index', _external=True),
        url_for('blog', _external=True),
        url_for('etf_hub', _external=True),
        url_for('data_product_etf', _external=True),
        url_for('about', _external=True),
        url_for('contact', _external=True),
        url_for('privacy', _external=True),
        url_for('terms', _external=True),
    ]
    post_urls = [url_for('view', post_id=row['id'], _external=True) for row in posts]
    urls = pages + post_urls

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for loc in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{loc}</loc>")
        xml_lines.append("  </url>")
    xml_lines.append('</urlset>')
    return Response("\n".join(xml_lines), mimetype='application/xml')


@app.route('/ads.txt')
def ads_txt():
    if ADSENSE_CLIENT.startswith("ca-pub-"):
        pub_id = ADSENSE_CLIENT.replace("ca-pub-", "", 1)
        content = f"google.com, pub-{pub_id}, DIRECT, f08c47fec0942fa0\n"
    else:
        content = "# ads.txt not configured\n"
    return Response(content, mimetype='text/plain')


if __name__ == '__main__':
    init_db()
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5001")),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
