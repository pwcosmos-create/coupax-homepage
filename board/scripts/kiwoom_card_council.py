"""
차수거래 학습 카드 — 9개 젬마 전원 협업 제작.

  python scripts/kiwoom_card_council.py compose --title "..." --dry-run
  python scripts/kiwoom_card_council.py create --max 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

DIVISION = "kiwoom-chasu"

# 카드 1장 제작 시 참여 순서 (큐레이터는 확정·export 담당)
COUNCIL_AGENT_IDS: tuple[str, ...] = (
    "kiwoom_reader",
    "kiwoom_risk",
    "kiwoom_order",
    "kiwoom_account",
    "kiwoom_structurer",
    "kiwoom_privacy",
    "kiwoom_error_fix",
    "kiwoom_rl",
    "kiwoom_curator",
)

AGENT_LABELS: dict[str, tuple[str, str]] = {
    "kiwoom_reader": ("차수 젬마", "📈"),
    "kiwoom_risk": ("리스크 젬마", "🛡️"),
    "kiwoom_order": ("주문 젬마", "📋"),
    "kiwoom_account": ("계좌 젬마", "💳"),
    "kiwoom_structurer": ("구조 젬마", "🗂️"),
    "kiwoom_privacy": ("보안 젬마", "🔒"),
    "kiwoom_error_fix": ("오류해결 에이전트", "🔧"),
    "kiwoom_rl": ("회간 젬마", "🌀"),
    "kiwoom_curator": ("큐레이터 젬마", "✅"),
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _blob(spec: dict) -> str:
    return f"{spec.get('title') or ''} {spec.get('body') or ''}"


def _has_any(blob: str, words: tuple[str, ...]) -> bool:
    return any(w in blob for w in words)


def _contrib_reader(spec: dict) -> str:
    b = _blob(spec)
    lines = [
        "1차는 시드·추세 확인 후 분할 진입, 2·3차는 조건 충족 시만 추가한다.",
        "차수마다 진입 조건·수량 비율·스킵 규칙을 한 줄로 남긴다.",
    ]
    if _has_any(b, ("ETF", "배당", "월배당")):
        lines.append("배당·락 일정은 차수 일정과 분리해 기록한다.")
    if _has_any(b, ("계좌간", "이체", "CMA")):
        lines.append("이체 완료 전에는 다음 차수 주문을 열지 않는다.")
    return " ".join(lines)


def _contrib_risk(spec: dict) -> str:
    b = _blob(spec)
    lines = [
        "원히어로는 손절 자동매도 없이 sell_pcts 익절만 사용한다.",
        "합산 평단이 손실이면 개별 슬롯 익절선 충족해도 매도하지 않는다.",
    ]
    if _has_any(b, ("cascade", "멀티", "multi")):
        lines.append("1번 3차+ 차단·cascade 계좌 이전 규칙을 명시한다.")
    if _has_any(b, ("ATR", "buy_gaps", "atr")):
        lines.append("ATR 갱신 시점·gap·익절% 범위를 종목별로 기록한다.")
    return " ".join(lines)


def _contrib_order(spec: dict) -> str:
    return (
        "지정가·시장가·조건부 지정가 기준을 차수마다 명시하고, "
        "미체결은 장 마감 전 정정·취소 규칙을 둔다. "
        "체결가·수량·수수료를 차수 ID와 함께 기록한다."
    )


def _contrib_account(spec: dict) -> str:
    b = _blob(spec)
    base = (
        "차수 추가 전 예수금·주문가능·미체결 합계를 점검한다. "
        "필요 현금 = (수량×가격)+수수료+버퍼."
    )
    if _has_any(b, ("이체", "계좌간", "CMA", "대체")):
        base += " 이체 반영 후 주문가능 갱신을 확인한 뒤 다음 차수를 연다."
    if _has_any(b, ("연금", "ISA", "IRP")):
        base += " 연금·ISA는 계좌별 제한을 먼저 확인한다."
    return base


def _contrib_structurer(spec: dict) -> str:
    return (
        "태그에 슬롯·1·2·3차·ATR·익절·sell_pcts·cascade·계좌를 포함하고, "
        "확정 시 kiwoom_knowledge_pack·Wiki(kiwoom-chasu)에 반영한다."
    )


def _contrib_privacy(spec: dict) -> str:
    return (
        "계좌번호 전체·비밀번호·API키·전화번호는 카드에 넣지 않는다. "
        "필요 시 계좌 유형(위탁·CMA)만 텍스트로 남긴다."
    )


def _contrib_error(spec: dict) -> str:
    return (
        "제작 오류(too_short·pii·tag_missing·duplicate)는 learning_errors playbook을 "
        "참고해 수정한다. 동일 오류 3회 시 meta 학습 카드를 갱신한다."
    )


def _contrib_rl(spec: dict) -> str:
    return (
        "RL 밴딧은 갭·오류·확정 피드백으로 다음 카드 우선순위를 조정한다. "
        "실패한 제목·카테고리는 가중치를 올려 재시도한다."
    )


def _contrib_curator(spec: dict) -> str:
    return (
        "협업 검수 후 확정·export·CURSOR_KIWOM_LEARN.md 동기화. "
        "투자 권유·자동 매매 아님 — 운용 메모·지식 정리 목적."
    )


_CONTRIB_FN = {
    "kiwoom_reader": _contrib_reader,
    "kiwoom_risk": _contrib_risk,
    "kiwoom_order": _contrib_order,
    "kiwoom_account": _contrib_account,
    "kiwoom_structurer": _contrib_structurer,
    "kiwoom_privacy": _contrib_privacy,
    "kiwoom_error_fix": _contrib_error,
    "kiwoom_rl": _contrib_rl,
    "kiwoom_curator": _contrib_curator,
}


def compose_card_body(spec: dict) -> tuple[str, list[dict]]:
    """본문 + 에이전트별 협업 섹션."""
    base = (spec.get("body") or "").strip()
    title = (spec.get("title") or "").strip()
    contributors: list[dict] = []
    blocks: list[str] = []

    for aid in COUNCIL_AGENT_IDS:
        fn = _CONTRIB_FN.get(aid)
        if not fn:
            continue
        text = fn(spec).strip()
        if not text:
            continue
        name, emoji = AGENT_LABELS.get(aid, (aid, "🤖"))
        header = f"■ {emoji} {name}"
        blocks.append(f"{header}\n{text}")
        contributors.append(
            {
                "agent_id": aid,
                "name": name,
                "emoji": emoji,
                "summary": text[:220],
                "ts": _now(),
            }
        )

    if blocks:
        body = (
            f"{base}\n\n"
            f"---\n"
            f"【에이전트 협업 검수 — {title}】\n"
            f"참여 {len(contributors)}명: "
            + ", ".join(c["name"] for c in contributors)
            + "\n\n"
            + "\n\n".join(blocks)
        )
    else:
        body = base
    return body[:24000], contributors


def log_council_feed(title: str, contributors: list[dict], *, card_id: int | None = None) -> None:
    try:
        import agent_office_log

        for c in contributors:
            cid_note = f" · 카드 #{card_id}" if card_id else ""
            agent_office_log.append_message(
                from_id=c["agent_id"],
                kind="task",
                text=(
                    f"[카드 협업{cid_note}] {title}\n"
                    f"{c.get('summary', '')[:300]}"
                )[:1200],
                division=DIVISION,
            )
        agent_office_log.append_message(
            from_id="kiwoom_curator",
            kind="conclusion",
            text=(
                f"[협업 제작 완료] {title} — "
                f"{len(contributors)}개 젬마 참여"
                + (f" · #{card_id}" if card_id else "")
            )[:1200],
            division=DIVISION,
        )
    except Exception:
        pass


def create_card_via_council(
    spec: dict,
    *,
    source: str = "council",
    confirm: bool = True,
    log_feed: bool = True,
) -> dict | None:
    """9젬마 협업 본문 → 카드 저장 → (선택) 확정·Wiki."""
    import agent_office_kiwoom_learn as learn
    import kiwoom_card_validate as kval
    import kiwoom_learning_errors as kerr

    try:
        import kiwoom_card_title_compose as kt

        spec = kt.enrich_spec(
            spec,
            error_kind=str(spec.get("error_kind") or ""),
        )
    except Exception:
        pass

    title = learn.normalize_title(spec.get("title") or "")
    if not title:
        return None
    if learn.title_taken(title):
        kerr.record("duplicate", "제목 중복 — 제작 생략", title=title)
        return None
    body, contributors = compose_card_body(spec)
    ok, kind, hint = kval.validate_spec(title, body)
    if not ok:
        kerr.record(kind, hint, title=title)
        return None

    try:
        card = learn.add_card(
            body=body,
            title=title,
            source=source,
            note=f"council×{len(contributors)}",
            use_council=False,
        )
    except ValueError as e:
        kerr.record("too_short", str(e)[:200], title=title)
        return None

    cid = card.get("id")
    if not isinstance(cid, int):
        return None

    store = learn.load_store()
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == cid:
            c["council"] = contributors
            c["council_agents"] = [x["agent_id"] for x in contributors]
            if spec.get("catalog_seed"):
                c["catalog_seed"] = str(spec.get("catalog_seed"))[:120]
            if spec.get("error_kind"):
                c["error_kind"] = str(spec.get("error_kind"))[:40]
            break
    learn.save_store(store)

    if log_feed:
        log_council_feed(title, contributors, card_id=cid)

    if not confirm:
        return {"card_id": cid, "title": title, "contributors": contributors, "confirmed": False}

    ok2, kind2, hint2 = kval.validate_card(
        next(c for c in learn.load_store().get("cards") or [] if c.get("id") == cid)
    )
    if not ok2:
        learn.delete_card(cid)
        kerr.record(kind2, hint2, title=title, card_id=cid)
        return None

    confirmed = learn.confirm_card(cid, export_pack_now=False)
    if not confirmed:
        learn.delete_card(cid)
        kerr.record("confirm_failed", "확정 실패", title=title, card_id=cid)
        return None

    try:
        import agent_office_wiki_store as wiki

        for c in learn.load_store().get("cards") or []:
            if isinstance(c, dict) and c.get("id") == cid:
                wiki.save_kiwoom_card_to_knowledge(c)
                break
    except Exception:
        pass

    try:
        import kiwoom_card_rl_engine as rle

        for c in learn.load_store().get("cards") or []:
            if isinstance(c, dict) and c.get("id") == cid:
                rle.record_confirm_success(c)
                break
    except Exception:
        pass

    learn.export_pack()
    return {
        "card_id": cid,
        "title": title,
        "contributors": contributors,
        "confirmed": True,
        "agent_count": len(contributors),
    }


def council_enabled() -> bool:
    return os.getenv("KIWOM_CARD_COUNCIL_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    comp = sub.add_parser("compose")
    comp.add_argument("--title", required=True)
    comp.add_argument("--body", default="")
    comp.add_argument("--dry-run", action="store_true")
    crt = sub.add_parser("create")
    crt.add_argument("--max", type=int, default=1)
    args = p.parse_args()

    if args.cmd == "compose":
        body, contrib = compose_card_body({"title": args.title, "body": args.body})
        print(body[:2000])
        print("--- contributors", len(contrib))
        return 0

    if args.cmd == "create":
        import kiwoom_card_gap_detector as gap_det
        import kiwoom_card_rl_engine as rle

        if council_enabled():
            rle.train_step()
        gaps = gap_det.detect_gaps()
        added = 0
        for m in (gaps.get("missing") or [])[: args.max]:
            spec = m.get("spec")
            if not isinstance(spec, dict):
                continue
            r = create_card_via_council(spec, source="council_compose")
            if r:
                added += 1
        print(json.dumps({"added": added}, ensure_ascii=False))
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
