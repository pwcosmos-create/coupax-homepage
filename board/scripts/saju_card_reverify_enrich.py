#!/usr/bin/env python3
"""
학습 카드 본문 구체화 — 작성 시·재검증 시 주제별 절차·키워드·주의 문단.

  python scripts/saju_card_reverify_enrich.py --card-id 10
  python scripts/saju_card_reverify_enrich.py batch --count 161

작성 시: add_card / confirm_card 에서 compose_new_card() 자동 호출
  (SAJU_CARD_COMPOSE_ON_CREATE=1, 기본 켜짐)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402

FOOTER_MARK = "본 내용은 명리 참고용"
STANDARD_FOOTER = (
    " 본 내용은 명리 참고용이며 확정 예언·의학·법률·투자 자문이 아닙니다. "
    "가능성·경향으로 해석하며, 학파·환경에 따라 달라질 수 있습니다."
)

REVERIFY_MODES = frozenset(
    {
        "initial",
        "retry_fail",
        "recert_after_fix",
        "reverify_pass",
        "copy_optimize",
    }
)

MIN_BODY = 900
_STYLE_VARIABLE = "variable"
_STYLE_INTERPRETIVE = "interpretive"
_VARIABLE_MARKERS = ("【개요】", "【풀이 절차】", "【활용 키워드】", "【핵심】")
_INTERPRETIVE_MARKERS = (
    "【인사·성향】",
    "【명식·구조】",
    "【오행·십신 해석】",
    "【테마 풀이】",
    "【실천 조언】",
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def enrich_enabled() -> bool:
    return os.getenv("SAJU_REVERIFY_ENRICH", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def compose_on_create_enabled() -> bool:
    return os.getenv("SAJU_CARD_COMPOSE_ON_CREATE", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _strip_footer(text: str) -> str:
    out = (text or "").strip()
    while FOOTER_MARK in out:
        out = out[: out.find(FOOTER_MARK)].rstrip()
    return out


def detect_card_style(
    title: str,
    body_hint: str = "",
    *,
    source: str = "",
    explicit: str | None = None,
) -> str:
    """variable(변수형) | interpretive(해석형 본문)."""
    if explicit in (_STYLE_VARIABLE, _STYLE_INTERPRETIVE):
        return explicit
    t = (title or "").strip()
    if t.startswith("변수·"):
        return _STYLE_VARIABLE
    if t.startswith("해석·") or t.startswith("심층·"):
        return _STYLE_INTERPRETIVE
    if (source or "").startswith("interpretive"):
        return _STYLE_INTERPRETIVE
    blob = f"{t}\n{body_hint}"
    if "【인사·성향】" in blob or "【테마 풀이】" in blob:
        return _STYLE_INTERPRETIVE
    if "【개요】" in blob and "【풀이 절차】" in blob:
        return _STYLE_VARIABLE
    interpretive_kw = (
        "무료",
        "풀이",
        "테마",
        "궁합",
        "연애",
        "재물",
        "직업",
        "성향",
        "해석",
        "일주",
        "대운",
        "세운",
        "용신",
        "격국",
        "조합",
    )
    if any(k in t for k in interpretive_kw):
        return _STYLE_INTERPRETIVE
    return _STYLE_INTERPRETIVE


def _has_rich_structure(body: str) -> bool:
    core = _strip_footer(body)
    if "【풀이 절차】" in core or "【활용 키워드】" in core:
        return False
    v_hit = sum(1 for m in _VARIABLE_MARKERS if m in core)
    i_hit = sum(1 for m in _INTERPRETIVE_MARKERS if m in core)
    if len(core) >= MIN_BODY and i_hit >= 3:
        return True
    if len(core) >= 420 and i_hit >= 2:
        return True
    return len(core) >= 1200


def _caution() -> str:
    return (
        "【주의】위 내용은 명리학적 경향을 읽어 드리는 참고 풀이이며, "
        "특정 사건·시기·질병·투자·이혼 등을 확정하지 않습니다. "
        "개인의 선택·환경·노력에 따라 달라질 수 있으니, "
        "중요한 결정은 전문가 상담과 함께 신중히 판단해 주시기 바랍니다."
    )


def format_readable_body(body: str) -> str:
    """절·기둥 제목 앞 줄바꿈 — 카드 본문 가독성."""
    b = (body or "").strip()
    if not b:
        return b
    b = re.sub(r"[ \t]+【", "\n\n【", b)
    b = re.sub(r"【([^】]+)】\s*", r"【\1】\n", b)
    for label in (
        "년주(年柱)",
        "월주(月柱)",
        "일주(日柱)",
        "시주(時柱)",
    ):
        b = re.sub(rf"([。.!?])\s*{re.escape(label)}", rf"\1\n\n{label}", b)
        b = re.sub(rf"(?<!\n)\s*{re.escape(label)}", f"\n\n{label}", b)
    b = re.sub(r"\n{3,}", "\n\n", b)
    return b.strip()


def _rich_saju_palja_section(
    *, topic: str = "", header: str = "【명식·구조】【사주팔자】"
) -> str:
    """사주팔자 섹션 — 기둥별 단락 분리 (읽기 좋게)."""
    hook = f"\n「{topic}」과 연결해 읽을 때도 같은 순서를 씁니다." if topic else ""
    return format_readable_body(
        f"""{header}

사주팔자(四柱八字)는 태어난 연·월·일·시의 천간(天干)·지지(地支) 네 쌍,
여덟 글자로 인생의 큰 지도를 그립니다.

먼저 년 · 월 · 일 · (시) 천간지지를 차례로 적고,
각 기둥이 어떤 삶의 영역을 말하는지 짚어 드리겠습니다.{hook}

시주(時柱)를 모르시면 일주·월주를 중심으로 참고해 주세요.
해석은 환경·대운에 따라 달라질 수 있습니다.

년주(年柱) — 조상 · 유년 · 초기 환경
조상·가문·유년기·초기 환경을 봅니다.
어린 시절 분위기, 집안의 기대, 타고난 기질의 뿌리가 여기에 드러나기 쉽습니다.
쉽게 말하면 「어디서 자랐는지」의 색깔에 가깝습니다.

월주(月柱) — 부모 · 직장 · 사회성
부모·형제·청년기·직장·사회성과 맞닿습니다.
월지(月支)에는 계절의 기운이 가장 강하게 깃들어, 격국(格局)·직업·일터 톤을 잡을 때 특히 중요합니다.
「사회에서 어떻게 버티는지」를 보는 자리라고 생각하시면 됩니다.

일주(日柱) — 본인 · 배우자궁
본인(日干)과 배우자궁(日支)입니다.
일간(日干)은 겉으로 드러나는 성향·추진 방식, 일지(日支)는 마음·관계·가정의 안정감을 보여 줍니다.
상담에서는 일주를 가장 많이 보는 편입니다.

시주(時柱) — 자녀 · 말년 · 실행
자녀·말년·실행·세부 직무·말년 흐름에 가깝습니다.
시간·분 단위는 민감할 수 있어, 모를 때는 「말년·실행」 키워드만 가볍게 참고하세요.

네 기둥이 서로 생(生)·극(剋)·합(合)·충(沖)을 이루면,
한 영역의 기운이 다른 영역으로 이어지는 그림이 선명해집니다."""
    )


def _blend_seed(core: str, detail: str) -> str:
    """풀 시드·주제 설명을 한 덩어리 서술로."""
    c = re.sub(r"\s+", " ", (core or "").strip())
    d = re.sub(r"\s+", " ", (detail or "").strip())
    if c and d and c not in d and len(c) > 20:
        return f"{c} 또한 {d}"
    return c or d or "명리 전반의 균형과 흐름을 함께 살펴야 합니다."


def _soft(s: str) -> str:
    """단정 완화."""
    return (
        s.replace("반드시", "흔히")
        .replace("확정", "가능성")
        .replace("무조건", "경향상")
    )


def _stem_detail(key: str) -> str:
    stems = {
        "갑목": "양목·큰 나무·개척·원칙·성장. 금 극 시 스트레스, 수 생조 시 학습·확장, 화 설기 시 표현.",
        "을목": "음목·덩굴·협상·인내·적응. 금 과다 시 절단감, 화 생 시 표현·인정욕구.",
        "병화": "양화·태양·열정·추진·체면. 수 보완 시 균형, 토 과다 시 걱정·우유부단.",
        "정화": "음화·촛불·세밀·직관·예술. 금 과다 시 자기비판, 목 생 시 성장.",
        "무토": "양토·산·중재·포용·책임. 목 극 시 고집, 화 생 시 따뜻한 추진.",
        "기토": "음토·밭·실무·끈기·신뢰. 수·목 보완으로 유연·성장.",
        "경금": "양금·쇠·원칙·결단·승부. 화 단련 시 성취, 목 극 시 압박·갈등 주의 톤.",
        "신금": "음금·보석·정밀·미감·완성도. 화 단련·수 설기로 균형.",
        "임수": "양수·강·바다·포용·지혜. 목 설기 시 성장, 화 과다 시 조급함.",
        "계수": "음수·이슬·분석·직관·기록. 임수보다 섬세·은밀.",
    }
    for name, detail in stems.items():
        if name in key:
            return detail
    return "천간 오행·음양·일간 강약과 함께 격국·용신을 연계해 본다."


def _branch_detail(key: str) -> str:
    if "삼합" in key:
        return "인오술(火)·해묘미(木)·사유축(金)·신자진(水) 국 성립 시 해당 오행 결집·인맥·지역·계절 키워드."
    if "충" in key:
        return "자오·축미·인신·묘유·진술·사해 등 — 변동·이동·관계 갈등. 겹치면 과도기 강조."
    if "합" in key or "육합" in key:
        return "자축·인해·묘술·진유·사신·오미 등 — 인연·협력·결합. 겉 합 속 충이면 양면 서술."
    return "지지는 계절·환경·육친·관계(합·충·형·파·해)로 읽으며 단정은 피한다."


def _ten_god_detail(key: str) -> str:
    mp = {
        "비견": "자아·동료·경쟁·고집. 과다 시 분재·협업 역할 분담.",
        "겁재": "경쟁·추진·파트너십. 재성·관성 약하면 현실화 필요.",
        "식신": "생산·표현·요리·교육·온화 창업.",
        "상관": "돌파·마케팅·예술·말·기술. 과다 시 규칙·말 이슈.",
        "편재": "사업·프로젝트·변동 수입·유통.",
        "정재": "월급·저축·안정 수입·가정 재정.",
        "편관": "압박·경쟁·권위·변동 속 성취.",
        "정관": "규율·직장·명분·책임·안정 조직.",
        "편인": "독학·직관·특수 기술·영성.",
        "정인": "학습·자격·보호·전통·안정.",
    }
    for k, v in mp.items():
        if k in key:
            return v
    return "십신은 일간 기준으로 월지·통근·대운과 조합해 해석한다."


def _topic_and_detail(title: str) -> tuple[str, str]:
    t = title.strip()
    key = t.replace("변수·", "").replace("심층·", "").replace("해석·", "").strip()

    if t.startswith("해석·"):
        sub = key
        if "도화" in sub:
            return "신살", (
                "도화(桃花)는 인연·매력·사교의 보조 신살로, "
                "일지·세운·월운과 겹칠 때 관계 이슈가 부각될 수 있습니다."
            )
        if "역마" in sub:
            return "신살", (
                "역마(驛馬)는 이동·출장·환경 변화·해외·이직 키워드. "
                "충·합과 겹치면 변동 톤만, 시기 단정은 하지 않습니다."
            )
        if "화개" in sub:
            return "신살", (
                "화개(華蓋)는 고독·연구·예술·종교·기록에 가깝게 읽히기도 하며, "
                "관계에서 거리감이 생길 수 있어 의도적 소통을 권합니다."
            )
        if "천을" in sub or "귀인" in sub:
            return "신살", (
                "천을귀인은 위기 시 도움·멘토·완충. "
                "사건·시기 단정 없이 지원·조언 흐름만 안내합니다."
            )
        if "월운" in sub:
            return "운", "월운은 해당 월의 십신 키워드 1~2문장. 세운·대운과 함께 보라고 안내."
        if "궁합" in sub or "연애" in sub or "배우자" in sub or "부부" in sub:
            return "궁합·관계", _branch_detail("궁합")
        if "건강" in sub or "번아웃" in sub or "컨디션" in sub:
            return "건강 톤", (
                "오행·신살로 컨디션·수면·리듬만. 질병명·시기 단정 금지, "
                "전문 의료 상담 권장."
            )

    if t.startswith("변수·천간") or "천간 " in t:
        topic, detail = "천간", _stem_detail(key)
    elif t.startswith("변수·지지") and "관계" not in t:
        topic, detail = "지지", f"{key} 지지의 계절·방위·육친 톤. 지장간·통근 여부를 함께 본다."
    elif "지지관계" in t or "삼합" in t or "충" in t or "형" in t:
        topic, detail = "지지 관계", _branch_detail(key)
    elif "십신" in t or "십신" in key:
        topic, detail = "십신", _ten_god_detail(key)
    elif "오행" in t:
        topic, detail = (
            "오행",
            "목·화·토·금·수 개수·과다·부족, 상생상극, 일간 생극(비겁·식상·재성·관성·인성)으로 연결.",
        )
    elif "신살" in t:
        topic, detail = (
            "신살",
            "문창·역마·도화·천을 등은 본격(격·용신) 다음 1~2문장 보조. 신살만으로 길흉 단정 금지.",
        )
    elif "격" in t or "격국" in t:
        topic, detail = (
            "격국",
            "월지 본기 정기로 격을 잡고 일간 강약·종격·화격 여부는 참고만. 격 vs 용신 충돌 시 분리.",
        )
    elif "희신" in t:
        el = key.replace("희신", "").strip() or key
        topic, detail = (
            "희신",
            f"희신 {el}은(는) 균형·기운을 돕는 보조 방향으로 읽습니다. "
            "용신·기신과 겹치면 보완 톤, 상극이면 조절·완충을 권합니다.",
        )
    elif "용신" in t or "기신" in t:
        label = "용신" if "용신" in t else "기신"
        el = re.sub(r"(변수·|용신|기신|운)", "", key).strip() or key
        topic, detail = (
            label,
            f"{label} {el}은(는) 일간·월지·대운과 함께 보며, "
            "한 오행만으로 길흉을 단정하지 않습니다. "
            "과다하면 조절·완충, 부족하면 보완 방향을 안내합니다.",
        )
    elif ("운" in t or "대운" in t or "세운" in t) and not ("용신" in t or "기신" in t):
        topic, detail = (
            "운",
            "대운(10년)→세운(1년)→월운(선택). 용신·기신과 맞물리면 확장·조정 톤. 충·합은 변동만.",
        )
    elif t.startswith("심층·"):
        topic, detail = (
            "풀이 섹션",
            f"{key} 절: 2~4문장, 전문 용어 뒤 쉬운 풀이 1문장. 시주 미상이면 일주 기준 명시.",
        )
    elif "일주" in t or "일간" in t or "일주" in key:
        topic, detail = (
            "일주·일간",
            "일간=겉 성향, 일지=내면·배우자궁. 시주 있으면 자녀·말년·직장 환경 보조.",
        )
    elif any(k in t for k in ("식신", "상관", "식상")):
        topic, detail = "식상", _ten_god_detail("식신") + " " + _ten_god_detail("상관")
    elif "관성" in t or "편관" in t or "정관" in t:
        topic, detail = "관성", "직장·책임·규율·압박. 과다 시 스트레스·자기억압, 용신 방향 취미·학습 권장."
    elif "재성" in t or "재물" in t:
        topic, detail = "재성", "현실·수입·지출·계약. 종목·날짜 단정 없이 현금흐름·역할 중심."
    elif "인성" in t or "학습" in t:
        topic, detail = "인성", "학습·자격·보호·멘토. 과다 시 실행 지연 — 식상·재성 보완."
    elif "비겁" in t or "겁재" in t:
        topic, detail = "비겁", _ten_god_detail("비견") + " 협업 시 지분·역할 명확화."
    elif "궁합" in t or "배우자" in t or "연애" in t:
        topic, detail = (
            "궁합·관계",
            "일간 상생·상극, 일지 충합, 대운 방향 비교. 보완·마찰 포인트만, 이혼·만남 시기 단정 금지.",
        )
    elif (
        "지지관계" in t
        or "원진" in t
        or "삼합" in t
        or "육합" in t
        or any(x in t for x in ("충·", "합·", "형·", "파·", "해·"))
        or (any(x in key for x in ("충", "합", "형", "파", "해", "원진")) and not t.startswith("해석·"))
    ):
        topic, detail = "지지 관계", _branch_detail(key)
    elif "무료" in t or "풀이 글 구조" in t or "심층" in t:
        topic, detail = (
            "풀이 구성",
            "인사→팔자→오행→십신·격→용신→대운·세운→테마 1~2→실천→면책. 절당 2~4문장.",
        )
    elif "십이운성" in t:
        stage = key.replace("십이운성", "").strip() or key
        topic, detail = (
            "십이운성",
            f"{stage}(十二運星)은 일간이 특정 지지에서 받는 기운 단계. "
            "장생·목욕·관대·건록·제왕은 성장·왕성, 쇠·병·사·묘·절·태·양은 소모·휴식·전환. "
            "월지·대운·세운과 겹칠 때만 톤을 붙이고 시기 단정은 하지 않는다.",
        )
    elif "지장간" in t:
        br = key.replace("지장간", "").strip() or key
        topic, detail = (
            "지장간",
            f"{br} 지지 속 숨은 천간(人元). 겉 지지보다 미세한 성향·직무·관계 톤. "
            "통근·뿌리 여부와 함께 보며 한 지장간만으로 길흉 단정 금지.",
        )
    elif "천간합" in t:
        topic, detail = (
            "천간합",
            "甲己合土·乙庚合金 등 — 인연·결합·화기(合化) 참고. "
            "합이 깨지거나 충·극이 겹치면 양면 서술. 시기·사건 단정 금지.",
        )
    elif "재생관" in t or "식상생재" in t or "재생관" in key:
        topic, detail = (
            "십신 관계",
            "재성(財)이 관성(官)을 생(生)하는 흐름 — 책임·조직·명분이 재물·현실화로 이어지는 그림. "
            "과다 시 압박·지출, 부족 시 실행·현실화 보완.",
        )
    elif "납음" in t:
        topic, detail = "납음", "60갑자 음성·오행 보조. 용신 단정 금지, 격국·오행 우선."
    elif "조후" in t or "통관" in t or "공망" in t:
        topic, detail = "보조 이론", "본격(격·용신) 다음 참고. 한열·공망·통관은 톤만, 의학·재난 단정 금지."
    else:
        topic, detail = (
            "명리 학습",
            f"「{key or t}」 테마를 오행·십신·격국·용신·대운 순으로 연결해 2~4문장씩 서술한다.",
        )
    return topic, detail


def _example_sentence(topic: str, title: str) -> str:
    examples = {
        "천간": "예) '일간 ○○은 △△한 성향이 두드러지며, 대운에서 ◇◇ 기운이 들어올 때 표현·직장 환경에 변화가 생기기 쉽습니다.'",
        "지지": "예) '월지 ○○은 청년기·직장 환경을 보며, 세운에서 충이 오면 이동·재정비 키워드를 붙입니다.'",
        "십신": "예) '관성이 강하면 책임·조직 테마가 커지므로, 식상·인성으로 스트레스 완화 방향을 함께 씁니다.'",
        "오행": "예) '화가 과다하면 열정·표현이 강한 경향이 있어, 수·금 기운으로 리듬·현실 감각을 보완하는 조언이 맞습니다.'",
        "격국": "예) '정관격이면 규율·명분을 중시하는 톤으로, 격과 다른 용신 방향이 있으면 분리해 설명합니다.'",
        "운": "예) '올해 세운에 재성이 오면 수입·계약 이슈를 「가능성」으로만 언급하고 날짜는 쓰지 않습니다.'",
        "궁합·관계": "예) '두 사람의 일지가 충이면 마찰 포인트를 짚고, 역할 분담·소통 공간을 제안합니다.'",
        "일주·일간": "예) '○○ 일주는 겉으로는 ◇◇하나 일지에서 △△한 내면이 드러난다고 씁니다.'",
    }
    ex = examples.get(topic, f"예) '{title}' 주제는 「~경향이 있습니다」「~를 보완하면 좋습니다」 형식으로 씁니다.")
    return f"【예시 서술】{ex}"


def _interpretive_example(topic: str, title: str) -> str:
    examples = {
        "관성": (
            "예) '귀하의 사주에는 관성 기운이 두드러져, 조직·책임·명분 이슈가 인생의 "
            "큰 줄기가 될 수 있습니다. 다만 올해 세운에서 식상이 들어오면 스트레스를 "
            "풀 표현·취미로 완화하는 편이 좋아 보입니다.'"
        ),
        "재성": (
            "예) '재성이 안정적으로 자리 잡은 편이라 월급·저축·계약 관리에 강점이 "
            "있을 수 있습니다. 다만 지출 구조를 점검하시면 흐름이 더 좋아질 수 있습니다.'"
        ),
        "궁합·관계": (
            "예) '두 분의 일지가 상생이라 기본적으로 보완 관계에 가깝습니다. "
            "다만 ○○ 대운에는 각자의 속도 차이를 조율할 여지가 있어 보입니다.'"
        ),
        "운": (
            "예) '현재 대운에서 화 기운이 강해지는 시기로, 활동·표현·이동이 늘기 쉬운 "
            "흐름입니다. 무리한 확장보다 리듬 조절을 권합니다.'"
        ),
    }
    ex = examples.get(
        topic,
        f"예) '{title}' 주제는 인사 한 줄 → 팔자 요약 → 핵심 해석 → 시기 → "
        "테마 1~2 → 실천 조언 순으로 2~4문장씩 이어 씁니다.",
    )
    return f"【풀이 예문】{ex}"


def _build_interpretive_sections(
    title: str, core: str, *, at_create: bool = False
) -> str:
    """해석형 — 상담 풀이에 가까운 서술형 본문 (메타 설명 없음)."""
    topic, detail = _topic_and_detail(title)
    t = title.replace("해석·", "").replace("심층·", "").strip() or title.strip()
    seed = _soft(_blend_seed(core, detail))

    parts = [
        (
            f"【인사·성향】안녕하세요. 오늘은 귀하의 사주에서 「{t}」에 해당하는 "
            f"기운을 중심으로 성향과 흐름을 짚어 드리겠습니다. {seed} "
            "일간은 겉으로 드러나는 태도와 추진 방식을, 일지(日支)는 마음속 안정감·"
            "관계에서의 습관을 보여 주는 자리로, 두 층을 나누어 읽는 것이 좋습니다. "
            "전체적으로는 한 가지 기운이 튀기보다, 여러 십신이 조화를 이루거나 "
            "서로 견제하는 패턴이 보일 때 해석이 풍부해집니다."
        ),
        _rich_saju_palja_section(topic=t),
        (
            f"【오행·십신 해석】먼저 목·화·토·금·수의 분포를 살피면, "
            f"어떤 기운이 풍부하고 어디가 보완이 필요한지 윤곽이 잡힙니다. "
            f"이번 주제인 {topic}과 연결하면, {detail} "
            "십신은 일간을 기준으로 비겁·식상·재성·관성·인성 중 어디에 "
            "무게가 실렸는지를 보며, 두세 가지를 엮어 「강점—주의—보완」 "
            "순으로 설명하는 것이 읽기 좋습니다. 용신·기신은 학파마다 견해가 "
            "달라 「참고 방향」으로만 말씀드리며, 단정하지 않겠습니다."
        ),
        (
            "【시기·운세】인생의 큰 줄기는 대운(大運), 한 해의 색깔은 세운(歲運)으로 "
            "읽습니다. 지금 흐름의 기운이 일간과 상생하면 확장·도전·관계 개방에 "
            "유리한 경향이, 상극·충·형이 겹치면 속도 조절·계약·이동·감정 "
            "정리가 필요해 보일 수 있습니다. 다만 특정 달·날짜에 사건이 "
            "정해진다고 말씀드리지는 않으며, 「변화의 기운이 강해지는 시기」 "
            "정도로만 안내드립니다."
        ),
        (
            f"【테마 풀이】{t}와 관련해 재물·일·관계·건강 리듬 중 "
            "가장 눈에 띄는 테마를 골라 깊게 보겠습니다. "
            "재성이 받쳐 주면 현실 감각·수입·지출 관리에 강점이, "
            "관성이 두드러지면 책임·조직·명분 이슈가 커질 수 있습니다. "
            "식상이 살아 있으면 표현·기술·창의가 재물이나 직업으로 "
            "이어지기 쉬운 구조입니다. 투자 종목·합격·이혼·질병명 등은 "
            "단정하지 않고, 생활 속에서 조절할 포인트만 말씀드립니다."
        ),
        (
            "【실천 조언】마지막으로 당장 실천하실 수 있는 방향을 두 가지 "
            "제안드립니다. 첫째, 기운이 과한 부분은 쉬는 리듬·기록·대화로 "
            "완화하고, 부족한 부분은 작은 습관(산책·학습·가계부·일정 정리)으로 "
            "채워 보세요. 둘째, 중요한 계약·관계 결정은 감정이 고조된 날보다 "
            "하루 이상 숙성한 뒤 판단하시면 흐름에 맞기 쉽습니다. "
            "사주는 가능성의 지도이니, 스스로의 선택이 결과를 만든다는 "
            "점도 함께 기억해 주시면 좋겠습니다."
        ),
        _caution(),
    ]
    if at_create and topic in ("관성", "재성", "궁합·관계", "운", "일주·일간"):
        parts.insert(5, _interpretive_example(topic, t))
    return " ".join(parts)


def _build_variable_sections(title: str, core: str, *, at_create: bool = False) -> str:
    """변수형 — 상담 톤 6절 (메타 절차·키워드 가이드 없음)."""
    topic, detail = _topic_and_detail(title)
    t = title.replace("변수·", "").strip() or title.strip()
    seed = _soft(_blend_seed(core, detail))

    parts = [
        (
            f"【인사·성향】안녕하세요. 오늘은 귀하의 사주에서 「{t}」에 해당하는 "
            f"기운을 중심으로 성향과 흐름을 짚어 드리겠습니다. "
            f"{topic}은(는) 일간·일주와 맞물릴 때 본인의 태도와 관계 습관에 "
            f"드러나기 쉽습니다. {seed} "
            "따뜻하되 과장하지 않고 격식을 갖춘 말투로 안내드리며, 시주를 "
            "모르시면 일주 기준으로 참고해 주시기 바랍니다. 환경·대운에 따라 "
            "해석은 달라질 수 있습니다."
        ),
        (
            f"【명식·구조】사주팔자에서 「{t}」이 년·월·일·시 중 어디에 "
            f"앉았는지에 따라 체감 강도가 달라집니다. "
            f"년지에 가깝면 가문·유년 환경, 월지면 직장·사회성, "
            f"일지면 마음·배우자궁, 시지면 말년·실행 쪽 톤이 붙기 쉽습니다. "
            f"{detail} "
            "일간과의 십신·생극(生剋)으로 강·약을 함께 보고, "
            "한 변수만으로 길흉을 단정하지 않습니다."
        ),
        (
            f"【오행·십신 해석】「{t}」이 강할 때는 그 기운의 장점과 "
            f"과잉(고집·소모·압박·산만함)을 함께 짚습니다. "
            f"약할 때는 보완·노력·협업 방향을 안내합니다. "
            f"관성과 인성이 맞물리면 책임·학습·자격, "
            f"식상과 재성이 맞물리면 표현·기술이 수입·사업으로 "
            f"이어지는 그림을 그릴 수 있습니다. "
            f"월지·대운·세운과 겹칠 때만 시기 키워드를 붙이며, "
            f"「~경향이 있습니다」「~보이기 쉽습니다」로 완화합니다."
        ),
        (
            f"【테마 풀이】{t}와 연결해 재물·연애·직업·건강 리듬 중 "
            f"1~2가지 테마를 골라 말씀드립니다. "
            f"{seed} "
            "같은 팔자라도 선택·환경·대운에 따라 체감이 달라지므로, "
            "가능성과 경향으로 받아들여 주시기 바랍니다. "
            "질병명·투자 종목·이혼·사망·합격·승진 시기 등은 단정하지 않습니다."
        ),
        (
            "【실천 조언】강한 기운은 기록·대화·휴식 리듬으로 과잉을 완화하고, "
            "약한 기운은 작은 습관(산책·학습·가계·일정)으로 채워 보세요. "
            "계약·투자·관계의 큰 결정은 하루 이상 숙성한 뒤 판단하시면 "
            "후회가 줄어드는 경향이 있습니다. "
            "건강·법률·투자는 전문가 상담을 병행해 주시기 바랍니다."
        ),
        _caution(),
    ]
    if at_create and topic in ("관성", "재성", "궁합·관계", "운", "일주·일간", "지지"):
        parts.insert(2, _rich_saju_palja_section(topic=t, header="【사주팔자】"))
    return " ".join(parts)


def _theme_header_for_title(title: str, topic: str) -> str:
    t = title.replace("변수·", "").replace("해석·", "").strip()
    if "기신" in t:
        return "기신"
    if "용신" in t or "희신" in t:
        return "용신" if "용신" in t else "희신"
    if "일운" in t or "오늘" in t:
        return "일운"
    if "월운" in t:
        return "월운"
    if "세운" in t:
        return "세운"
    if "대운" in t:
        return "대운"
    if topic in ("재성", "관성", "식상", "인성", "비겁"):
        return "테마 풀이"
    return "핵심"


def _build_variable_slim_sections(title: str, core: str) -> str:
    """변수형 — 채팅·조합용 짧은 본문 (테마 절 + 주의)."""
    topic, detail = _topic_and_detail(title)
    t = title.replace("변수·", "").strip() or title.strip()
    seed = _soft(_blend_seed(core, detail))
    header = _theme_header_for_title(title, topic)
    parts = [
        (
            f"【{header}】귀하의 사주에서 「{t}」에 해당하는 흐름을 짚어 드립니다. "
            f"{detail} {seed} "
            "일간·월지·대운과 함께 보며, 한 변수만으로 길흉을 단정하지 않습니다."
        ),
        (
            "【실천 조언】강한 기운은 기록·대화로 완화하고, "
            "약한 기운은 작은 습관으로 채워 보세요."
        ),
        _caution(),
    ]
    return " ".join(parts)


def _build_interpretive_slim_sections(title: str, core: str) -> str:
    """해석형 — 테마 중심 짧은 본문."""
    topic, detail = _topic_and_detail(title)
    t = title.replace("해석·", "").replace("심층·", "").strip() or title.strip()
    seed = _soft(_blend_seed(core, detail))
    parts = [
        (
            f"【인사·성향】「{t}」 주제를 중심으로 성향과 흐름을 짚어 드립니다. "
            f"{seed} {detail}"
        ),
        (
            f"【테마 풀이】{t}와 연결해 재물·일·관계 중 눈에 띄는 테마를 "
            "2~4문장으로 안내합니다. 시기·사건 단정은 하지 않습니다."
        ),
        _caution(),
    ]
    return " ".join(parts)


def _build_sections(
    title: str,
    core: str,
    *,
    at_create: bool = False,
    card_style: str | None = None,
    source: str = "",
) -> str:
    style = detect_card_style(title, core, source=source, explicit=card_style)
    if (title or "").strip().startswith("심층·"):
        return _build_interpretive_sections(title, core, at_create=at_create)
    if style == _STYLE_INTERPRETIVE:
        if at_create:
            return _build_interpretive_sections(title, core, at_create=at_create)
        return _build_interpretive_slim_sections(title, core)
    if at_create:
        return _build_variable_sections(title, core, at_create=at_create)
    return _build_variable_slim_sections(title, core)


def _normalize_title(title: str, style: str) -> str:
    t = (title or "").strip()
    if not t:
        return t
    if style == _STYLE_INTERPRETIVE and not t.startswith("해석·"):
        if not t.startswith("변수·") and not t.startswith("심층·"):
            return f"해석·{t}"[:120]
    return t[:120]


def _finalize_compose(title: str, body: str, *, card_style: str = "") -> dict:
    try:
        from saju_card_copy_optimize import optimize_summary, optimize_tags, optimize_title

        title = optimize_title({"title": title, "body": body})
        summary = optimize_summary(title, body)
        tags = optimize_tags(body, title, None)
    except ImportError:
        summary = learn._summary(body, 158)
        tags = learn._extract_tags(f"{title}\n{body}")
    body = format_readable_body(body)
    try:
        from saju_reading_display import optimize_card_body

        body = optimize_card_body(body)
    except ImportError:
        try:
            from saju_reading_display import normalize_body_for_reading

            body = normalize_body_for_reading(body)
        except ImportError:
            pass
    return {
        "title": title[:120],
        "body": body[:24000],
        "summary": summary,
        "tags": tags[:16],
        "card_style": card_style,
    }


def compose_new_card(
    title: str,
    body_hint: str = "",
    *,
    force: bool = False,
    at_create: bool = True,
    card_style: str | None = None,
    source: str = "",
) -> dict:
    """신규 카드 작성용 — 변수형·해석형 본문으로 확장."""
    hint = _strip_footer(body_hint or "")
    style = detect_card_style(title, hint, source=source, explicit=card_style)
    title = _normalize_title(title or learn._summary(hint, 50), style)
    if not title:
        title = "해석·명리 참고" if style == _STYLE_INTERPRETIVE else "명리 학습·참고"

    if not force and hint and _has_rich_structure(hint):
        body = hint if FOOTER_MARK in hint else hint + STANDARD_FOOTER
        return _finalize_compose(title, body, card_style=style)

    body = _build_sections(
        title, hint, at_create=at_create, card_style=style, source=source
    )
    if FOOTER_MARK not in body:
        body = body.rstrip("。. ") + STANDARD_FOOTER
    return _finalize_compose(title, body, card_style=style)


def compose_pending_card(card_id: int) -> bool:
    """확정 전 pending 카드 본문 구체화."""
    card = learn.get_card(card_id)
    if not card or (card.get("status") or "") != "pending":
        return False
    if _has_rich_structure(card.get("body") or ""):
        return False
    pkg = compose_new_card(
        card.get("title") or "",
        card.get("body") or "",
        at_create=True,
        card_style=card.get("card_style"),
        source=card.get("source") or "",
    )
    store = learn.load_store()
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            c["title"] = pkg["title"]
            c["body"] = pkg["body"]
            c["summary"] = pkg["summary"]
            c["tags"] = pkg["tags"]
            c["card_style"] = pkg.get("card_style") or c.get("card_style")
            c["composed_at"] = _now()
            learn.save_store(store)
            return True
    return False


def enrich_card_fields(card: dict, *, force: bool = False) -> tuple[dict, list[str]]:
    """재검증용 구체 본문·요약·태그 생성."""
    patches: list[str] = []
    title = (card.get("title") or "").strip()
    core = _strip_footer(card.get("body") or "")

    if not force and _has_rich_structure(card.get("body") or ""):
        return {}, patches

    try:
        from saju_deep_section_rich import rich_body_for_title

        deep_body = rich_body_for_title(title)
        if deep_body:
            pkg = {
                "title": title[:120],
                "body": deep_body,
                "summary": learn._summary(deep_body, 160),
                "tags": learn._extract_tags(f"{title}\n{deep_body}")[:16],
                "card_style": "interpretive",
            }
            if pkg["body"] != (card.get("body") or "").strip():
                patches.append("심층·풍부화")
                return pkg, patches
            return {}, patches
    except ImportError:
        pass

    pkg = compose_new_card(
        title,
        core,
        force=True,
        at_create=True,
        card_style=card.get("card_style"),
        source=card.get("source") or "",
    )
    if pkg["body"] == (card.get("body") or "").strip():
        return {}, patches

    patches.append("재검증·구체화")
    return pkg, patches


def apply_enrich(card_id: int, *, force: bool = False) -> dict:
    card = learn.get_card(card_id)
    if not card or (card.get("status") or "") != "confirmed":
        return {"ok": False, "card_id": card_id, "error": "not_confirmed"}

    if not force and _has_rich_structure(card.get("body") or ""):
        return {"ok": True, "card_id": card_id, "skipped": True}

    fields, patches = enrich_card_fields(card, force=force)
    if not patches:
        return {"ok": True, "card_id": card_id, "skipped": True}

    note = f"{(card.get('note') or '').strip()}\n[구체화 {_now()}] {', '.join(patches)}".strip()[:500]
    updated = learn.update_confirmed_card(
        card_id,
        title=fields.get("title"),
        body=fields.get("body"),
        summary=fields.get("summary"),
        tags=fields.get("tags"),
        note=note,
        council_enriched_at=_now(),
    )
    return {
        "ok": bool(updated),
        "card_id": card_id,
        "patches": patches,
        "title": (fields.get("title") or "")[:50],
    }


def enrich_before_verify(card_id: int, mode: str) -> bool:
    """재검증 직전 구체화. 변경 있으면 True."""
    if not enrich_enabled():
        return False
    if mode not in REVERIFY_MODES:
        return False
    r = apply_enrich(card_id)
    return bool(r.get("ok") and not r.get("skipped"))


def batch_enrich(
    count: int = 200,
    *,
    force: bool = False,
    sleep_sec: float = 0,
    only_short: bool = False,
    min_len: int = 520,
) -> dict:
    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]
    if only_short:
        cards = [
            c
            for c in cards
            if len(_strip_footer(c.get("body") or "")) < int(min_len)
        ]
    cards.sort(key=lambda c: int(c.get("id") or 0))
    count = min(int(count), len(cards))
    changed = 0
    for c in cards[:count]:
        r = apply_enrich(int(c["id"]), force=force)
        if r.get("ok") and not r.get("skipped"):
            changed += 1
        if sleep_sec > 0:
            import time

            time.sleep(sleep_sec)
    if changed:
        learn.export_pack()
    return {"requested": count, "enriched": changed}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--card-id", type=int, default=0)
    p.add_argument("--force", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    b = sub.add_parser("batch")
    b.add_argument("--count", type=int, default=200)
    b.add_argument("--sleep", type=float, default=0)
    b.add_argument("--force", action="store_true")
    b.add_argument("--only-short", action="store_true")
    b.add_argument("--min-len", type=int, default=520)
    args = p.parse_args()
    if args.card_id:
        print(apply_enrich(args.card_id, force=args.force))
        return 0
    if args.cmd == "batch":
        print(
            batch_enrich(
                args.count,
                force=args.force,
                sleep_sec=args.sleep,
                only_short=args.only_short,
                min_len=args.min_len,
            )
        )
        return 0
    print(batch_enrich(200))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
