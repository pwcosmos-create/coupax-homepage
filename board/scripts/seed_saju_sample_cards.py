#!/usr/bin/env python3
"""샘플 사주 풀이 2건 추가·확정 후 구조화 감사 실행."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402

SAMPLES = [
    {
        "title": "갑목 일주 · 오행 균형 샘플",
        "body": (
            "일주 갑목(甲木)으로 뿌리가 굳건한 명식입니다. 오행은 목·화가 상대적으로 "
            "강하고 금·수가 약한 편입니다. 십신으로 보면 비겁과 식상이 두드러져 "
            "자기 주장과 표현력이 함께 나타납니다. 재성은 중간 강도, 관성은 약해 "
            "조직·규율보다 자율 환경에 적합합니다. 대운은 초년 수·중년 화·후년 토 "
            "흐름으로, 30대 전후 화 기운에서 활동성이 커집니다. 용신은 수(水)로 "
            "목을 돕고 과한 화를 조절하는 방향이 유리합니다. 기신은 과다한 금 기운으로 "
            "판단은 신중하되 고집·완고함에 주의가 필요합니다. 격국은 식신생재에 가까운 "
            "형태로, 재능을 현실 수익·성과로 연결할 때 운이 살아납니다."
        ),
    },
    {
        "title": "정화 일주 · 대운·세운 해석 샘플",
        "body": (
            "일주 정화(丁火)로 세밀하고 직관적인 기질이 강합니다. 오행은 화·토가 "
            "중심이고 수·목이 보완 역할을 합니다. 십신에서 인성·관성이 함께 있어 "
            "학습·자격·책임감이 동반됩니다. 재성은 안정적, 비겁은 과하지 않아 "
            "협업 시 조율이 가능합니다. 대운 흐름은 20대 목·30대 화·40대 토로 "
            "이어지며, 세운·월운에서 화·토가 겹칠 때 업무·재정 이벤트가 늘기 쉽습니다. "
            "용신은 목(木)으로 정화를 지지하고, 기신은 과한 토로 우유부단·지체를 "
            "유발할 수 있습니다. 신살 측면에서는 문창·천을 등 학문·멘토 기운이 "
            "있어 기록·교육·상담 분야와 궁합이 좋습니다. 명리 해석 시 시기별로 "
            "대운과 세운을 분리해 말하는 것이 모순을 줄입니다."
        ),
    },
]


def main() -> int:
    ids: list[int] = []
    for s in SAMPLES:
        card = learn.add_card(body=s["body"], title=s["title"], source="sample_seed")
        cid = card.get("id")
        if isinstance(cid, int):
            ids.append(cid)
            print(f"added #{cid}: {s['title'][:40]}")

    for cid in ids:
        out = learn.confirm_card(cid)
        print(f"confirmed #{cid} -> wiki may sync: {out is not None}")

    import saju_structure_audit  # noqa: E402

    return saju_structure_audit.main()


if __name__ == "__main__":
    raise SystemExit(main())
