"""숏폼공장 — 위치(IP·헤더)·Accept-Language 기반 locale 감지."""

from __future__ import annotations

import ipaddress
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from flask import Request

SUPPORTED = frozenset({"ko", "en", "ja", "zh", "es"})

_COUNTRY_LANG: dict[str, str] = {
    "KR": "ko",
    "JP": "ja",
    "CN": "zh",
    "TW": "zh",
    "HK": "zh",
    "MO": "zh",
    "SG": "en",
    "ES": "es",
    "MX": "es",
    "AR": "es",
    "CO": "es",
    "CL": "es",
    "PE": "es",
    "VE": "es",
    "EC": "es",
    "GT": "es",
    "CU": "es",
    "BO": "es",
    "DO": "es",
    "HN": "es",
    "PY": "es",
    "SV": "es",
    "NI": "es",
    "CR": "es",
    "PA": "es",
    "UY": "es",
    "PR": "es",
    "GQ": "es",
}

_COUNTRY_HEADERS = (
    "CF-IPCountry",
    "X-Country-Code",
    "CloudFront-Viewer-Country",
    "X-AppEngine-Country",
)

_GEO_ENABLED = os.getenv("SHORTS_GEOIP_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
_GEO_TTL_SEC = int(os.getenv("SHORTS_GEOIP_CACHE_SEC", "86400"))
_geo_cache: dict[str, tuple[float, str | None]] = {}


def _client_ip(req: Request) -> str | None:
    forwarded = (req.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip
    real = (req.headers.get("X-Real-IP") or "").strip()
    if real:
        return real
    return (req.remote_addr or "").strip() or None


def _is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local)


def _country_from_headers(req: Request) -> str | None:
    for header in _COUNTRY_HEADERS:
        code = (req.headers.get(header) or "").strip().upper()
        if code and code not in ("XX", "T1"):
            return code
    return None


def _fetch_country_code(ip: str) -> str | None:
    """공인 IP → ISO 국가코드 (ipwho.is, 실패 시 ip-api.com)."""
    providers = (
        f"https://ipwho.is/{ip}?fields=country_code,success",
        f"http://ip-api.com/json/{ip}?fields=status,countryCode",
    )
    for url in providers:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "coupax-shorts/1.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            continue

        if "country_code" in data:
            if data.get("success") is False:
                continue
            code = (data.get("country_code") or "").strip().upper()
            if code:
                return code
        if data.get("status") == "success":
            code = (data.get("countryCode") or "").strip().upper()
            if code:
                return code
    return None


def _country_from_ip(ip: str | None) -> str | None:
    if not _GEO_ENABLED or not ip or not _is_public_ip(ip):
        return None

    now = time.time()
    cached = _geo_cache.get(ip)
    if cached and now - cached[0] < _GEO_TTL_SEC:
        return cached[1]

    code = _fetch_country_code(ip)
    _geo_cache[ip] = (now, code)
    if len(_geo_cache) > 5000:
        oldest = sorted(_geo_cache.items(), key=lambda x: x[1][0])[:1000]
        for k, _ in oldest:
            _geo_cache.pop(k, None)
    return code


def _country_from_request(req: Request) -> str | None:
    """CDN 헤더 → IP 지오룩업 순으로 국가 코드."""
    return _country_from_headers(req) or _country_from_ip(_client_ip(req))


def _lang_from_accept_language(req: Request) -> str | None:
    """브라우저/OS 사용 언어 목록에서 지원 locale 매칭."""
    for lang, _q in req.accept_languages or []:
        code = (lang or "").lower().replace("_", "-")
        if not code:
            continue
        primary = code.split("-")[0]
        if primary in SUPPORTED:
            return primary
    return None


def _locale_for_country(country: str, accept: str | None) -> str | None:
    if country == "KR":
        return "ko"
    if country == "JP":
        return "ja"
    if country in ("CN", "TW", "HK", "MO"):
        return "zh"
    if _COUNTRY_LANG.get(country) == "es":
        return "es"
    if country in _COUNTRY_LANG:
        mapped = _COUNTRY_LANG[country]
        if country == "SG" and accept:
            return accept
        return mapped
    return None


def detect_locale(req: Request) -> str:
    """브라우저 사용 언어(Accept-Language) 우선 → 위치(IP) → en."""
    accept = _lang_from_accept_language(req)
    if accept:
        return accept

    country = _country_from_request(req)
    if country:
        by_country = _locale_for_country(country, None)
        if by_country:
            return by_country

    return "en"


LOCALE_META: dict[str, dict[str, str]] = {
    "ko": {
        "html_lang": "ko",
        "title": "숏폼공장 — 소상공인 AI 숏폼",
        "description": (
            "소상공인 매장 홍보용 9:16 숏폼을 Gemini·Imagen·Veo·Lyria로 자동 생성합니다. "
            "구독 후 바로 사용 — API 키 불필요."
        ),
        "og_description": "구독 한 번으로 AI 숏폼 홍보 파이프라인을 이용하세요.",
    },
    "en": {
        "html_lang": "en",
        "title": "숏폼공장 — AI Shorts for Local Business",
        "description": (
            "Create 9:16 promo shorts with Gemini, Imagen, Veo, and Lyria. "
            "Subscribe and generate — no API key needed."
        ),
        "og_description": "Subscribe once. We run the AI pipeline for your shop promos.",
    },
    "ja": {
        "html_lang": "ja",
        "title": "숏폼공장 — 小規模店舗向けAIショート動画",
        "description": (
            "Gemini・Imagen・Veo・Lyriaで9:16の宣伝ショートを自動生成。"
            "サブスクで今すぐ利用 — APIキー不要。"
        ),
        "og_description": "サブスク登録でAIショート動画パイ프라インをご利用ください。",
    },
    "zh": {
        "html_lang": "zh-Hans",
        "title": "숏폼공장 — 小微店铺 AI 短视频",
        "description": (
            "用 Gemini、Imagen、Veo、Lyria 自动生成 9:16 宣传短视频。"
            "订阅即用 — 无需 API 密钥。"
        ),
        "og_description": "订阅一次，即可使用 AI 短视频宣传流水线。",
    },
    "es": {
        "html_lang": "es",
        "title": "숏폼공장 — Shorts con IA para negocios locales",
        "description": (
            "Crea shorts promocionales 9:16 con Gemini, Imagen, Veo y Lyria. "
            "Suscríbete y genera — sin clave API."
        ),
        "og_description": "Suscríbete una vez. Ejecutamos el pipeline de IA para tu negocio.",
    },
}


def meta_for(locale: str) -> dict[str, str]:
    return LOCALE_META.get(locale, LOCALE_META["en"])
