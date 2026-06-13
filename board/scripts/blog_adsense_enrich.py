"""
블로그 초안 — AdSense·E-E-A-T용 본문 보강 (멱등).

  python scripts/blog_adsense_enrich.py --post-id 12
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from html import escape
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import board_env  # noqa: E402

DB_PATH = board_env.resolve_db_path()
SITE_URL = os.environ.get("SITE_URL", "https://coupax.co.kr").rstrip("/")
MARKER = "<!-- coupax-adsense-enriched -->"
MIN_TEXT_LEN = int(os.environ.get("BLOG_ADSENSE_MIN_CHARS", "1500") or "1500")


def _strip_html(html: str) -> str:
    t = re.sub(r"<script[^>]*>.*?</script>", " ", html or "", flags=re.I | re.S)
    t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.I | re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def adsense_score(content: str) -> int:
    """발행 적합도 점수 (높을수록 우선)."""
    text = _strip_html(content)
    c = content or ""
    score = 0
    if len(text) >= MIN_TEXT_LEN:
        score += 50
    elif len(text) >= 900:
        score += 25
    if re.search(r"\[카테고리\]", c):
        score += 10
    if re.search(r"FAQ|자주\s*묻는\s*질문", c, re.I):
        score += 15
    if re.search(r"면책|투자\s*권유|세무·법률\s*자문", c):
        score += 15
    if re.search(r"참고\s*출처|nts\.go\.kr|fss\.or\.kr|bok\.or\.kr", c, re.I):
        score += 10
    if re.search(r"<h[23]>", c, re.I):
        score += 5
    return score


def is_enriched(content: str) -> bool:
    return MARKER in (content or "") or "9) 참고 출처" in (content or "")


def build_enrichment_block(title: str) -> str:
    t = escape((title or "본 글")[:80])
    return f"""
{MARKER}
<h3>실전 체크 포인트</h3>
<ul>
<li>본 글 「{t}」은 일반 정보이며, 개인 상황에 따라 적용 결과가 달라질 수 있습니다.</li>
<li>수치·한도·금리는 정책 변경 시 달라질 수 있으므로 글 상단 안내 시점과 함께 공식 출처를 확인하세요.</li>
<li>특정 상품 매수·매도나 수익을 약속하는 표현은 피하고, 본인 목표·기간·리스크에 맞게 판단하세요.</li>
</ul>
<h3>자주 묻는 질문 (FAQ)</h3>
<p><strong>Q1.</strong> 이 글만 보고 바로 실행해도 되나요?</p>
<p><strong>A1.</strong> 아닙니다. 본문은 이해를 돕는 참고 자료이며, 최종 결정 전에 공식 안내·약관을 확인하세요.</p>
<p><strong>Q2.</strong> 세금·연금·청약은 어디서 최신 기준을 보나요?</p>
<p><strong>A2.</strong> 국세청·금융감독원·한국은행·청약홈 등 1차 출처를 우선 확인하세요.</p>
<p><strong>Q3.</strong> 글이 오래되면 어떻게 하나요?</p>
<p><strong>A3.</strong> 정책·금리·한도는 수시로 바뀔 수 있어, 중요한 숫자는 발행 시점 기준으로 다시 검증하세요.</p>
<h3>참고 출처</h3>
<ul>
<li>국세청: <a href="https://www.nts.go.kr" rel="noopener noreferrer">https://www.nts.go.kr</a></li>
<li>금융감독원: <a href="https://www.fss.or.kr" rel="noopener noreferrer">https://www.fss.or.kr</a></li>
<li>한국은행: <a href="https://www.bok.or.kr" rel="noopener noreferrer">https://www.bok.or.kr</a></li>
<li>청약홈: <a href="https://www.applyhome.co.kr" rel="noopener noreferrer">https://www.applyhome.co.kr</a></li>
</ul>
<p><small>내부 링크: <a href="{SITE_URL}/">홈</a> · <a href="{SITE_URL}/blog">블로그</a> · <a href="{SITE_URL}/privacy">개인정보처리방침</a></small></p>
<p class="post-disclaimer"><strong>면책</strong> 본 글은 일반적인 금융·재테크 정보 제공 목적이며, 투자·세무·법률 자문이 아닙니다.</p>
"""


def enrich_content(title: str, content: str) -> str:
    body = (content or "").rstrip()
    if is_enriched(body):
        return body
    return body + "\n" + build_enrichment_block(title)


def enrich_post(post_id: int, *, db_path: Path | None = None) -> dict:
    path = db_path or DB_PATH
    if not path.is_file():
        return {"ok": False, "error": "db_missing"}
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT id, title, content, COALESCE(is_draft, 0) FROM posts WHERE id=?",
            (post_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "not_found"}
        pid, title, content, is_draft = row
        new_content = enrich_content(title or "", content or "")
        if new_content != content:
            conn.execute("UPDATE posts SET content=? WHERE id=?", (new_content, pid))
            conn.commit()
        return {
            "ok": True,
            "post_id": pid,
            "is_draft": bool(is_draft),
            "score": adsense_score(new_content),
            "text_len": len(_strip_html(new_content)),
            "enriched": new_content != content,
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--post-id", type=int, required=True)
    args = p.parse_args()
    r = enrich_post(args.post_id)
    print(r)
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
