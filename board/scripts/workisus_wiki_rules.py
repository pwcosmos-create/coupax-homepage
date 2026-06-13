"""wonkisus Gemma24 Wiki 정본 — wonkisus-grid-trading-rules (board 학습 카드 대체)."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

WIKI_ID = "wonkisus-grid-trading-rules"
WIKI_TITLE = "원키스us 차수거래 및 무손실 매매 규칙"
WIKI_SHORT_TITLE = "10분할 무손실 리밸런싱"

_BOARD_CANON = Path(__file__).resolve().parents[1] / "data" / "workisus_canonical" / "wonkisus-grid-trading-rules.md"

_FALLBACK_WIKI = (
    str(_BOARD_CANON),
    r"C:\커셔\주식\wonkisus\gemma24\10_Wiki\wonkisus-grid-trading-rules.md",
    "/home/opc/coupax-homepage/board/data/workisus_canonical/wonkisus-grid-trading-rules.md",
    "/home/ubuntu/coupax-homepage/board/data/workisus_canonical/wonkisus-grid-trading-rules.md",
    "/home/opc/wonkisus/gemma24/10_Wiki/wonkisus-grid-trading-rules.md",
)

_FALLBACK_META = (
    r"C:\커셔\주식\wonkisus\gemma24\20_Meta\wonkisus-grid-trading-rules.meta.json",
    "/home/opc/wonkisus/gemma24/20_Meta/wonkisus-grid-trading-rules.meta.json",
    str(_BOARD_CANON.parent / "wonkisus-grid-trading-rules.meta.json"),
)

# 공식 요약 bullet (pulse·UI·에이전트 공통)
CANON_BULLETS: tuple[str, ...] = (
    "현금 10% + 9종목 각 10% = 10자산 100%",
    "Trim to 10%: Profit>0일 때만 초과분 매도",
    "Buy up to 10%: 미달분만 매수·하락 괴리 최대 종목 우선",
    "Cycle당 최대 2건 점진 매매 (rebalance_max_trades_per_cycle)",
    "손실 구간 매도·자동 손절 없음 (무손실)",
)


def resolve_rules_path() -> Path | None:
    env = os.getenv("WONKISUS_WIKI_RULES_PATH", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    for raw in _FALLBACK_WIKI:
        try:
            p = Path(raw)
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def resolve_meta_path() -> Path | None:
    env = os.getenv("WONKISUS_WIKI_META_PATH", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    wiki = resolve_rules_path()
    if wiki:
        same_dir = wiki.parent / f"{wiki.stem}.meta.json"
        if same_dir.is_file():
            return same_dir
        gemma_meta = wiki.parent.parent / "20_Meta" / f"{WIKI_ID}.meta.json"
        if gemma_meta.is_file():
            return gemma_meta
    for raw in _FALLBACK_META:
        try:
            p = Path(raw)
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def load_meta() -> dict:
    try:
        p = resolve_meta_path()
    except OSError:
        return {}
    if not p:
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except OSError:
        return {}
    except Exception:
        return {}


def load_rules_markdown() -> str:
    p = resolve_rules_path()
    if not p:
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def wiki_status() -> dict:
    p = resolve_rules_path()
    meta = load_meta()
    if not p:
        return {
            "ok": False,
            "wiki_id": WIKI_ID,
            "title": WIKI_TITLE,
            "short_title": WIKI_SHORT_TITLE,
            "path": "",
            "meta_path": str(resolve_meta_path() or ""),
            "updated_at": (meta.get("updated") or "")[:16].replace("T", " "),
            "chars": 0,
            "bullets": list(CANON_BULLETS),
            "error": "wonkisus-grid-trading-rules.md 경로 없음 (WONKISUS_WIKI_RULES_PATH 설정)",
        }
    text = load_rules_markdown()
    mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    updated = (meta.get("updated") or "")[:19].replace("T", " ") or mtime
    return {
        "ok": True,
        "wiki_id": WIKI_ID,
        "title": meta.get("title") or WIKI_TITLE,
        "short_title": WIKI_SHORT_TITLE,
        "path": str(p),
        "meta_path": str(resolve_meta_path() or ""),
        "updated_at": updated,
        "chars": len(text),
        "bullets": list(CANON_BULLETS),
        "error": "",
    }


def summary_lines(max_lines: int = 5) -> list[str]:
    if not resolve_rules_path():
        return ["정본 Wiki 미연결 — WONKISUS_WIKI_RULES_PATH 확인"]
    return list(CANON_BULLETS[:max_lines])


def export_trading_context(*, max_chars: int = 18000) -> str:
    """HTS·Cursor 플레이북 — wonkisus Wiki 정본."""
    st = wiki_status()
    body = load_rules_markdown()
    if not body:
        return (
            f"# 원키스US 매매 정본\n\n"
            f"⚠ {st.get('error') or 'Wiki 파일 없음'}\n"
            f"ID: {WIKI_ID}\n"
        )
    if body.startswith("---"):
        end = body.find("---", 3)
        if end > 0:
            body = body[end + 3 :].lstrip()
    header = (
        f"# 원키스US — {WIKI_SHORT_TITLE} ({WIKI_ID})\n"
        f"path: {st.get('path', '')} · meta: {st.get('meta_path', '')} · "
        f"갱신 {st.get('updated_at', '')}\n\n"
    )
    out = header + body
    if len(out) > max_chars:
        out = out[: max_chars - 80] + "\n\n…(truncated)\n"
    return out


# 젬마 pulse 초점 (wonkisus-grid-trading-rules §1~§5)
AGENT_FOCUS: dict[str, str] = {
    "workisus_watch": "10분할·Trim/Buy·Cycle≤2·무손실",
    "workisus_knowledge": f"정본 {WIKI_ID}·meta·index.json",
    "workisus_mode": "§3 자동/안전·리밸런스·격자",
    "workisus_balance": "현금10%+9×10% 실비중",
    "workisus_stocks": "9종목·enabled·목표10%",
    "workisus_rules": "target_cash_weight_pct=10·settings",
    "workisus_risk": "§2 Profit>0만 Trim·손절 없음",
    "workisus_rebalance": "Trim 10%(이익)·Buy 10%(하락우선)·max 2/cycle",
    "workisus_token": "KIS US 토큰·잔고 API",
    "workisus_reconcile": "US 슬롯·잔고 정합",
    "workisus_order": "[3002]·슬롯(격자 병행)",
    "workisus_auto": "리밸런스 자동·Cycle 2건 제한",
    "workisus_multi": "10자산·단일 해외계좌",
    "workisus_slots": "차수·슬롯 DB(격자)",
    "workisus_hts": "workisus 3001~3005",
    "workisus_atr": "§4 gap·PPO·atr_timer",
    "workisus_ops": "§2 점진2건·실행확인·게이트",
}


def focus_for_agent(agent_id: str) -> str:
    return AGENT_FOCUS.get((agent_id or "").strip()) or WIKI_SHORT_TITLE
