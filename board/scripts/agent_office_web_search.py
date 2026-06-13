"""
탐정 젬마 — 외부 웹 팩트 수집 (사무실 작업·팩트 펄스 전용).

젬마24 홈/댓글 답변(RAG)과 분리됩니다. 블로그 방문자에게 웹 원문을 직접 노출하지 않고,
작업 보고·Wiki 요약에만 스니펫을 넣습니다.

환경 변수:
  AGENT_OFFICE_WEB_SEARCH_ENABLED  기본 1
  AGENT_OFFICE_WEB_SEARCH_MAX      기본 5 (건수)
  AGENT_OFFICE_WEB_TOPIC_ENABLED   기본 1 — 웹 검색으로 블로그 글감 후보 선정
  AGENT_OFFICE_WEB_TOPIC_MAX       기본 3 (글감 건수)
  TAVILY_API_KEY                   있으면 Tavily 우선
  BRAVE_SEARCH_API_KEY             Tavily 없을 때 Brave
  (둘 다 없으면 DuckDuckGo HTML — 키 불필요, 품질·가용성은 서버마다 다름)
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

_PII_PATTERNS = (
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
    re.compile(r"\d{6}-?\d{7}"),
)
_UA = "Mozilla/5.0 (compatible; CoupaxAgentOffice/1.0; +https://coupax.co.kr)"
_DDG_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class WebHit:
    title: str
    url: str
    snippet: str
    provider: str


@dataclass
class BlogTopicSuggestion:
    topic: str
    reason: str
    url: str
    provider: str


def web_search_enabled() -> bool:
    return os.getenv("AGENT_OFFICE_WEB_SEARCH_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def max_results() -> int:
    try:
        n = int(os.getenv("AGENT_OFFICE_WEB_SEARCH_MAX", "5") or "5")
    except ValueError:
        n = 5
    return max(1, min(n, 8))


def topic_search_enabled() -> bool:
    return web_search_enabled() and os.getenv(
        "AGENT_OFFICE_WEB_TOPIC_ENABLED", "1"
    ).strip().lower() in ("1", "true", "yes")


def max_topic_suggestions() -> int:
    try:
        n = int(os.getenv("AGENT_OFFICE_WEB_TOPIC_MAX", "3") or "3")
    except ValueError:
        n = 3
    return max(1, min(n, 5))


def _redact_pii(text: str) -> str:
    out = text or ""
    for rx in _PII_PATTERNS:
        out = rx.sub("[PII]", out)
    return out


def build_query(title: str, body: str, keywords: list[str] | None = None) -> str:
    """검색어 — 한국 금융 맥락 힌트 포함."""
    parts: list[str] = []
    for chunk in (title or "", body or ""):
        chunk = _redact_pii(re.sub(r"\s+", " ", chunk).strip())
        if chunk:
            parts.append(chunk)
    if keywords:
        parts.extend(keywords[:6])
    q = " ".join(parts).strip()
    if len(q) > 140:
        q = q[:140].rsplit(" ", 1)[0] or q[:140]
    if q and not re.search(r"(한국|금융|연금|etf|금리|세금)", q, re.I):
        q = f"{q} 금융"
    return q or "한국 금융 시장 이슈"


def should_search_web(primary_id: str, title: str, body: str) -> bool:
    """탐정 젬마 또는 외부 팩트가 필요한 지시."""
    if not web_search_enabled():
        return False
    aid = (primary_id or "").strip()
    if aid == "researcher":
        return True
    blob = f"{title} {body}".lower()
    triggers = (
        "웹검색",
        "웹 검색",
        "인터넷",
        "뉴스",
        "속보",
        "발표",
        "금리",
        "한은",
        "fed",
        "fomc",
        "cpi",
        "실시간",
        "오늘",
        "이슈",
        "공시",
        "web search",
    )
    return any(t in blob for t in triggers)


def should_pick_blog_topics(primary_id: str, title: str, body: str) -> bool:
    """웹 검색으로 블로그 신규 글감 후보를 뽑을 작업인지."""
    if not topic_search_enabled():
        return False
    aid = (primary_id or "").strip()
    t = (title or "").strip()
    blob = f"{t} {body or ''}"
    if aid == "creator":
        return True
    if "블로그 글감" in t or "글감" in t:
        return True
    keys = ("글감", "새 주제", "주제 선정", "주제 제안", "신규 주제", "글 주제", "콘텐츠 기획")
    return any(k in blob for k in keys)


def build_topic_query(title: str, body: str, keywords: list[str] | None = None) -> str:
    """블로그 글감용 검색어 — 금융·경제 뉴스 쪽으로 고정."""
    t = (title or "").strip()
    blob = f"{t} {body or ''}"
    if "블로그 글감" in t or re.search(r"글감|주제\s*선정|신규\s*주제", blob):
        return "한국 금융 경제 이슈 연금 절세 ETF 금리 뉴스"
    q = build_query(title, body, keywords)
    if not re.search(r"(이슈|트렌드|뉴스)", q, re.I):
        q = f"{q} 금융 경제 뉴스"
    return q[:160]


_TOPIC_NOISE = re.compile(
    r"(홈페이지|로그인|회원가입|광고|쿠팡|네이버\s*블로그|youtube|유튜브|"
    r"글감\s*찾|주제\s*찾|키워드\s*찾|블로그\s*운영|수익\s*올리|티스토리\s*수익)",
    re.I,
)


def _clean_topic_line(raw: str) -> str:
    t = html.unescape(raw or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s*[-|·|:]\s*[^-|·:]{0,30}$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) < 10 or len(t) > 88:
        return ""
    if _TOPIC_NOISE.search(t):
        return ""
    return t


def suggest_blog_topics(
    title: str,
    body: str,
    keywords: list[str] | None = None,
    *,
    limit: int | None = None,
) -> list[BlogTopicSuggestion]:
    """웹 검색 결과에서 블로그 장문 글감 후보를 선정."""
    if not topic_search_enabled():
        return []
    lim = limit if limit is not None else max_topic_suggestions()
    query = build_topic_query(title, body, keywords)
    hits = search_web(query, limit=max(lim * 2, 6))
    seen: set[str] = set()
    out: list[BlogTopicSuggestion] = []
    for h in hits:
        topic = _clean_topic_line(h.title)
        if not topic:
            continue
        key = topic[:40].lower()
        if key in seen:
            continue
        seen.add(key)
        reason = (h.snippet or "최근 웹 검색 상위 결과").strip()[:220]
        out.append(
            BlogTopicSuggestion(
                topic=topic,
                reason=reason,
                url=h.url,
                provider=h.provider,
            )
        )
        if len(out) >= lim:
            break
    return out


_YOUTUBE_URL = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    re.I,
)


def is_youtube_url(url: str) -> bool:
    return bool(_YOUTUBE_URL.search(url or ""))


def youtube_video_id(url: str) -> str:
    m = _YOUTUBE_URL.search(url or "")
    return m.group(1) if m else ""


def _unwrap_ddg_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("//"):
        u = "https:" + u
    if "duckduckgo.com/l/" in u and "uddg=" in u:
        parsed = urllib.parse.urlparse(u)
        qs = urllib.parse.parse_qs(parsed.query)
        inner = (qs.get("uddg") or [""])[0]
        if inner:
            return urllib.parse.unquote(inner)
    return u


def _search_youtube_data_api(query: str, api_key: str, limit: int) -> list[WebHit]:
    params = urllib.parse.urlencode(
        {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": str(limit),
            "order": "relevance",
            "relevanceLanguage": "ko",
            "key": api_key,
        }
    )
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _DDG_UA}, method="GET")
        timeout = int(os.getenv("AGENT_OFFICE_WEB_SEARCH_TIMEOUT_SEC", "25") or "25")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        ValueError,
        OSError,
    ):
        return []
    hits: list[WebHit] = []
    for row in data.get("items") or []:
        if not isinstance(row, dict):
            continue
        vid = row.get("id") or {}
        video_id = vid.get("videoId") if isinstance(vid, dict) else ""
        sn = row.get("snippet") or {}
        title = (sn.get("title") or "").strip()
        if not video_id:
            continue
        watch = f"https://www.youtube.com/watch?v={video_id}"
        desc = (sn.get("description") or "").strip()[:400]
        channel = (sn.get("channelTitle") or "").strip()
        snippet = f"{channel}: {desc}" if channel else desc
        hits.append(
            WebHit(title=title or watch, url=watch, snippet=snippet, provider="youtube_api")
        )
        if len(hits) >= limit:
            break
    return hits


def search_youtube(query: str, *, limit: int | None = None) -> list[WebHit]:
    """YouTube 영상 검색 — site:youtube.com + URL 필터."""
    q = _redact_pii((query or "").strip())
    if not q:
        return []
    if not web_search_enabled():
        return []
    lim = limit if limit is not None else max_results()
    lim = max(1, min(lim, 10))

    yt_key = (os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_YOUTUBE_API_KEY") or "").strip()
    if yt_key:
        api_hits = _search_youtube_data_api(q, yt_key, lim)
        if api_hits:
            return api_hits

    def _filter_yt(hits: list[WebHit]) -> list[WebHit]:
        out: list[WebHit] = []
        seen: set[str] = set()
        for h in hits:
            vid = youtube_video_id(h.url)
            if not vid:
                continue
            if vid in seen:
                continue
            seen.add(vid)
            provider = h.provider
            if "youtube" not in provider:
                provider = f"{provider}+youtube"
            out.append(
                WebHit(
                    title=h.title,
                    url=h.url,
                    snippet=h.snippet,
                    provider=provider,
                )
            )
            if len(out) >= lim:
                break
        return out

    primary_q = q if "site:youtube.com" in q.lower() else f"site:youtube.com {q}"
    hits = _filter_yt(search_web(primary_q, limit=lim * 3))
    if len(hits) >= lim:
        return hits

    hits.extend(
        _filter_yt(
            search_web(f"유튜브 {q}", limit=lim * 3),
        )
    )
    seen_v: set[str] = set()
    merged: list[WebHit] = []
    for h in hits:
        vid = youtube_video_id(h.url)
        if vid in seen_v:
            continue
        seen_v.add(vid)
        merged.append(h)
        if len(merged) >= lim:
            break
    return merged


def search_web(query: str, *, limit: int | None = None) -> list[WebHit]:
    """Tavily → Brave → DuckDuckGo 순으로 시도."""
    q = _redact_pii((query or "").strip())
    if not q:
        return []
    lim = limit if limit is not None else max_results()
    tavily_key = (os.getenv("TAVILY_API_KEY") or "").strip()
    brave_key = (os.getenv("BRAVE_SEARCH_API_KEY") or "").strip()
    if tavily_key:
        hits = _search_tavily(q, tavily_key, lim)
        if hits:
            return hits
    if brave_key:
        hits = _search_brave(q, brave_key, lim)
        if hits:
            return hits
    return _search_duckduckgo_html(q, lim)


def _search_tavily(query: str, api_key: str, limit: int) -> list[WebHit]:
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": limit,
        "search_depth": "basic",
        "include_answer": False,
    }
    try:
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout = int(os.getenv("AGENT_OFFICE_WEB_SEARCH_TIMEOUT_SEC", "25") or "25")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        ValueError,
        OSError,
    ):
        return []
    hits: list[WebHit] = []
    for row in data.get("results") or []:
        if not isinstance(row, dict):
            continue
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        snippet = (row.get("content") or row.get("snippet") or "").strip()[:400]
        if title or snippet:
            hits.append(WebHit(title=title or url[:60], url=url, snippet=snippet, provider="tavily"))
        if len(hits) >= limit:
            break
    return hits


def _search_brave(query: str, api_key: str, limit: int) -> list[WebHit]:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "count": str(limit),
            "search_lang": "ko",
            "country": "KR",
            "text_decorations": "0",
        }
    )
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
            method="GET",
        )
        timeout = int(os.getenv("AGENT_OFFICE_WEB_SEARCH_TIMEOUT_SEC", "25") or "25")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        ValueError,
        OSError,
    ):
        return []
    hits: list[WebHit] = []
    web = data.get("web") if isinstance(data, dict) else {}
    for row in (web.get("results") if isinstance(web, dict) else []) or []:
        if not isinstance(row, dict):
            continue
        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        snippet = (row.get("description") or "").strip()[:400]
        if title or snippet:
            hits.append(WebHit(title=title or url[:60], url=url, snippet=snippet, provider="brave"))
        if len(hits) >= limit:
            break
    return hits


def _search_duckduckgo_html(query: str, limit: int) -> list[WebHit]:
    """API 키 없을 때 폴백 — HTML 파싱 (브라우저 UA)."""
    body = urllib.parse.urlencode({"q": query}).encode("utf-8")
    try:
        req = urllib.request.Request(
            "https://html.duckduckgo.com/html/",
            data=body,
            headers={
                "User-Agent": _DDG_UA,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        timeout = int(os.getenv("AGENT_OFFICE_WEB_SEARCH_TIMEOUT_SEC", "25") or "25")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            page = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return []

    hits: list[WebHit] = []
    seen: set[str] = set()
    patterns = (
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        r'href="([^"]+)"[^>]*class="result__a"[^>]*>([^<]+)</a>',
    )
    for pat in patterns:
        for m in re.finditer(pat, page, re.I):
            url = _unwrap_ddg_url(urllib.parse.unquote(m.group(1).strip()))
            if not url or url in seen:
                continue
            seen.add(url)
            title = re.sub(r"\s+", " ", html.unescape(m.group(2))).strip()
            if not title:
                continue
            hits.append(
                WebHit(title=title[:120], url=url[:500], snippet="", provider="duckduckgo")
            )
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break

    snips = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|span|div)>',
        page,
        re.I | re.S,
    )
    for i, h in enumerate(hits):
        if i < len(snips):
            raw = re.sub(r"<[^>]+>", " ", snips[i])
            h.snippet = re.sub(r"\s+", " ", html.unescape(raw)).strip()[:400]
    return hits


def provider_status() -> str:
    """상태 한 줄 (팩트 펄스·헬스용)."""
    if not web_search_enabled():
        return "웹검색 OFF"
    parts: list[str] = []
    if (os.getenv("TAVILY_API_KEY") or "").strip():
        parts.append("Tavily")
    if (os.getenv("BRAVE_SEARCH_API_KEY") or "").strip():
        parts.append("Brave")
    if (os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_YOUTUBE_API_KEY") or "").strip():
        parts.append("YouTube API")
    if parts:
        return "웹검색 ON (" + "+".join(parts) + ")"
    return "웹검색 ON (DuckDuckGo 폴백)"
