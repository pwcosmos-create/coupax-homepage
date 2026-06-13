#!/usr/bin/env python3
"""
사주 학습 카드 자동 추가 (UI 변경 없음).

  python scripts/saju_auto_add_cards.py              # 대기 풀에서 최대 5건
  python scripts/saju_auto_add_cards.py --per-minute 10  # 분당 10장 (sleep 5)
  python scripts/saju_auto_add_cards.py --hourly 10   # 시간당 10장
  python scripts/saju_auto_add_cards.py --max 2 --sleep 3
  python scripts/saju_auto_add_cards.py --interpretive --max 5
  python scripts/saju_auto_add_cards.py --all

cron 예: 0 * * * * cd .../board && python3 scripts/saju_auto_add_cards.py --hourly 10 --sleep 3
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
from saju_card_usage_priority import (  # noqa: E402
    get_inventory,
    sort_specs_by_usage,
    usage_score_for_spec,
)

# 자동 추가 풀 — 제목 중복 시 스킵
# (풀이 매칭 빈도 높음 → HIGH_USAGE_AUTO_POOL 로 앞에 배치)
AUTO_CARD_POOL: list[dict] = [
    {
        "title": "충·합·형·파·해·원진",
        "body": (
            "지지 충(冲)은 변동·이동·관계 갈등, 합(合)은 인연·협력·결합, 형(刑)은 "
            "압박·자기갈등, 파(破)는 깨짐·재정비, 해(害)는 방해·소모, 원진은 "
            "거리감·오해로 풀이한다. 두 지지가 동시에 있으면 「겉 합 속 충」처럼 "
            "양면을 함께 쓴다. 시기는 세운·월운에서 해당 관계가 성립할 때만 "
            "언급하고 사건을 단정하지 않는다."
        ),
    },
    {
        "title": "식신·상관 강한 명식",
        "body": (
            "식신·상관이 강하면 표현·기술·창의·말·글에 재능이 쏟아진다. "
            "식신은 안정적 창작·생산, 상관은 돌파·비판·마케팅·자유직에 가깝다. "
            "과다하면 말 많음·산만·규칙 거부에 주의. 재성이 있으면 「식상생재」로 "
            "재능→수익 연결, 없으면 「표현은 강하나 현실화 경로 설계 필요」로 "
            "조언한다."
        ),
    },
    {
        "title": "관성 강한 명식",
        "body": (
            "정관·편관이 강하면 책임·조직·규율·상하관계 이슈가 인생 테마가 되기 쉽다. "
            "정관은 공식·명분·안정 직장, 편관은 압박·경쟁·변동·권위와 맞닿는다. "
            "관성 과다 시 스트레스·자기억압을 완화하려면 용신(식상·인성) 방향의 "
            "취미·학습을 권한다. 관재·관살 겹침은 법규·계약·건강 리듬 점검 톤으로만."
        ),
    },
    {
        "title": "재성 강한 명식·재물",
        "body": (
            "정재·편재가 강하면 현실 감각·돈·물건·실행력이 두드러진다. "
            "정재는 월급·저축·안정 수입, 편재는 사업·프로젝트·변동 수입에 가깝다. "
            "재다신재(재 많고 약함)는 돈이 들어와도 나가기 쉬움 — 지출 구조·버퍼를 "
            "조언한다. 투자 종목·날짜는 쓰지 않고 「현금흐름·역할 분담」 중심."
        ),
    },
    {
        "title": "인성 강한 명식·학습",
        "body": (
            "정인·편인이 강하면 학습·보호·직관·멘토·자격증 테마가 강하다. "
            "정인은 전통·학교·안정적 스승, 편인은 독학·영성·특수 지식에 가깝다. "
            "인성 과다 시 생각만 많고 실행이 늦을 수 있어 식상·재성 보완을 "
            "권한다. 「공부운·자격운」은 세운 인성 기운과 겹칠 때만 언급."
        ),
    },
    {
        "title": "병화 일주 성향",
        "body": (
            "일간 병화(丙火)는 밝고 열정적이며 드러내는 불꽃에 가깝다. "
            "인정·체면·속도감을 중시하고 추진력이 강하다. "
            "수 기운이 보완되면 균형, 목이 있으면 지속, 토가 많으면 "
            "우유부단·걱정이 붙을 수 있다. 여름생·낮생은 화 기운이 겹칠 때 "
            "과열·번아웃 주의만 서술한다."
        ),
    },
    {
        "title": "임수 일주 성향",
        "body": (
            "일간 임수(壬水)는 큰 강·바다처럼 포용·유연·지혜가 있다. "
            "겉은 차분해도 내면은 깊고 목표가 크다. 금이 생하면 "
            "의리·결단, 목이 설기하면 성장·표현으로 흐른다. "
            "토가 많으면 고집·답답함, 화가 과하면 조급·감정 기복을 "
            "완화하라고 조언한다."
        ),
    },
    {
        "title": "경금 일주 성향",
        "body": (
            "일간 경금(庚金)은 쇠·도구·원칙·결단에 가깝다. "
            "직선적·정의감·승부욕이 있고 기준이 분명하다. "
            "화가 단련하면 성취, 수가 설기하면 유연, 목이 극하면 "
            "압박·부상·갈등 키워드는 「주의」 톤만. "
            "금 과다 시 완고·냉정함을 인성·수로 완화한다고 쓴다."
        ),
    },
    {
        "title": "기토 일주 성향",
        "body": (
            "일간 기토(己土)는 밭·정원의 흙처럼 포용·실무·중재에 강하다. "
            "신뢰·끈기·현실 적응력이 좋고 묵묵히 결과를 만든다. "
            "목이 과하면 고집, 수가 많으면 걱정·체중·소화 리듬만 "
            "「생활 리듬」으로 언급(의학 단정 금지). "
            "화가 생하면 따뜻한 리더십·식상 표현으로 연결한다."
        ),
    },
    {
        "title": "월지 계절·격 보조",
        "body": (
            "월지는 계절 기운·부모·청년·직장 환경을 본다. 인월·묘월은 목의 "
            "성장, 사·오는 화의 확장, 신·유는 금의 수확, 해·자는 수의 "
            "저장으로 톤을 잡는다. 격은 월지 본기로 잡되 일간 강약에 따라 "
            "「종격·화격」 여부를 검토한다고만 쓰고 확정하지 않는다."
        ),
    },
    {
        "title": "일지·배우자궁 톤",
        "body": (
            "일지(日支)는 배우자·가정·말년·내면 안정을 본다. 일지와 일간 "
            "관계가 생·극·합·충이면 가정·연애 표현에 반영한다. "
            "「배우자 성격 단정」 대신 「관계에서 필요한 소통·공간」을 "
            "제안한다. 일지 식신은 돌봄·요리·편안함, 일지 관성은 책임·"
            "원칙, 일지 재성은 현실·재정 협의로 풀어 쓴다."
        ),
    },
    {
        "title": "십성·궁합 참고 톤",
        "body": (
            "궁합은 두 사주의 일간 오행 상생·상극, 일지 충합, 대운 방향을 "
            "비교한다. 「잘 맞는다/이혼한다」 대신 「보완·마찰 포인트」로 "
            "쓴다. 한쪽만 강한 오행이면 역할 분담을 제안한다. "
            "연애·부부·사업 파트너 모두 동일 프레임, 사업은 재성·관성 "
            "비중을 조금 더 본다."
        ),
    },
    {
        "title": "세운·월운 키워드 맵",
        "body": (
            "세운 천간·지지를 일간과의 십신으로 바꿔 키워드를 뽑는다. "
            "비겁 세운: 경쟁·협업·자존감. 식상: 표현·이직·창업 기회. "
            "재성: 수입·지출·계약. 관성: 승진·책임·압박. 인성: 학습·휴식·"
            "이동. 충·합이 있으면 「변화의 해」 정도로만. "
            "월운은 1~2문장으로 해당 달 하이라이트만 덧붙인다."
        ),
    },
    {
        "title": "을목 일주 성향",
        "body": (
            "일간 을목(乙木)은 풀·덩굴처럼 유연·적응·인내가 강하다. "
            "겉은 부드우나 뿌리는 집요하고 관계에 섬세하다. "
            "금이 극하면 스트레스·절단 감정, 화가 생하면 "
            "표현·인정욕구, 수가 있으면 성장·학습운으로 연결한다. "
            "을목은 큰 나무(갑목)보다 협상·조율·디테일에 강점이 있다고 쓴다."
        ),
    },
    {
        "title": "정수 일주 성향",
        "body": (
            "일간 정수(丁火)는 촛불·등불처럼 세밀·따뜻·집중력이 있다. "
            "감정 표현은 은은하나 관찰력이 뛰어나다. "
            "목이 생하면 성장, 토가 많으면 걱정·완벽주의, "
            "금이 과하면 냉정·자기비판에 주의. "
            "정화(丙火)보다 디테일·내면·예술·상담 적성을 강조한다."
        ),
    },
    {
        "title": "신금 일주 성향",
        "body": (
            "일간 신금(辛金)은 보석·바늘처럼 예민·정밀·미감이 있다. "
            "품격·체계·깔끔함을 중시하고 날카로운 판단이 가능하다. "
            "화가 단련하면 브랜드·완성도, 수가 설기하면 유연, "
            "토가 많으면 고민·피로 누적만 「리듬 관리」로. "
            "경금보다 섬세·협상·디자인·금융 디테일에 가깝다고 쓴다."
        ),
    },
    {
        "title": "갑목 일주 성향",
        "body": (
            "일간 갑목(甲木)은 큰 나무·개척·원칙·성장. 곧게 뻗으나 굽히기 어려움. "
            "금이 극하면 스트레스·절단, 수가 생하면 성장, 화가 설기하면 표현·인정. "
            "을목보다 리더·개혁·큰 그림에 강점."
        ),
    },
    {
        "title": "정화 일주 성향",
        "body": (
            "일간 정화(丁火)은 촛불·세밀·따뜻·직관. 은은한 표현·예술·상담. "
            "병화보다 디테일·내면·완벽주의. 토·금 과다 시 자기비판·피로 리듬만 언급."
        ),
    },
    {
        "title": "무토 일주 성향",
        "body": (
            "일간 무토(戊土)은 산·댐·중재·포용·책임. 느리지만 묵직·신뢰. "
            "목이 극하면 고집, 수가 설기하면 지혜, 화가 생하면 따뜻한 추진."
        ),
    },
    {
        "title": "계수 일주 성향",
        "body": (
            "일간 계수(癸水)은 이슬·샘·직관·분석·기록. "
            "깊이·회피 경향. 임수보다 섬세·연구·은밀. 화·목 보완으로 균형."
        ),
    },
    {
        "title": "비겁·겁재 과다 톤",
        "body": (
            "비겁·겁재가 과다하면 자아·경쟁·고집·분재 키워드. "
            "협업 시 역할·지분 명확화. 재성·관성이 약하면 현실화·규율 보완 권한다."
        ),
    },
    {
        "title": "식상생재·창업 톤",
        "body": (
            "식신·상관이 재성을 생(식상생재)하면 재능→수익 연결. "
            "창업·프리랜스·콘텐츠·기술 창업 톤. 과다 상관은 말·규칙 이슈 주의."
        ),
    },
    {
        "title": "관인상생·자격·직장",
        "body": (
            "관성+인성(관인상생)은 직장·자격·책임·학습 조합. "
            "공무원·대기업·전문직 톤만 참고. 승진·합격 날짜 단정 금지."
        ),
    },
    {
        "title": "재다신약·지출 관리",
        "body": (
            "재성은 많은데 일간이 약(재다신약)하면 돈 들어와도 나가기 쉬움. "
            "버퍼·지출 구조·공동 투자 주의. 투자 종목 단정 금지."
        ),
    },
    {
        "title": "삼합·방합 인맥",
        "body": (
            "지지 삼합·방합이 있으면 인맥·팀·지역·계절 기운 결집. "
            "해당 오행 국(水木火金) 방향 키워드. 사업 파트너는 재성·관성도 함께 본다."
        ),
    },
    {
        "title": "천간·지지 극(剋) 톤",
        "body": (
            "천간 극·지지 충이 겹치면 내적·외적 갈등·변동. "
            "「나쁜 사주」 대신 「조율·선택·타이밍」 조언. 의학·사고 단정 금지."
        ),
    },
    {
        "title": "여성 명식·연애 보조",
        "body": (
            "여성 명식도 동일 프레임. 관성=연애·책임, 식상=표현, 재성=현실. "
            "도화·홍염은 매력·인기 톤만. 배우자 성격 단정 금지."
        ),
    },
    {
        "title": "남성 명식·직업 보조",
        "body": (
            "남성 명식: 관성=직장·책임, 재성=재물·실행, 식상=기술·창업. "
            "편관 강하면 압박·경쟁·리더 시험 톤. 승진 시기 단정 금지."
        ),
    },
]

# phase3 — 기존 seed/변수 카드에 없는 주제 (제목 중복 시 스킵)
AUTO_CARD_POOL_PHASE3: list[dict] = [
    {
        "title": "변수·통관(通關)",
        "body": (
            "【통관】오행이 한쪽으로 쏠릴 때 중간 오행이 막힘을 풀어 준다. "
            "예: 목화토가 겹치면 수로 목→화를 이어 주거나, 금수목이 겹치면 화로 "
            "금→수를 완충한다. 용신과 함께 보되 「반드시 이 오행」 단정은 피한다. "
            "학파·조후와 충돌 시 「참고 견해」로 완화한다."
        ),
    },
    {
        "title": "변수·육친(父母·配偶·子女)",
        "body": (
            "【육친】년주=조상·부모 기운, 월주=부모·형제·청년 환경, 일주=본인·배우자궁, "
            "시주=자녀·말년·실행. 남녀 모두 관성·재성으로 배우자·연애 톤만 조정하고 "
            "팔자 자체는 바꾸지 않는다. 육친 단정(불효·이혼) 금지, 「관계·역할」로 서술."
        ),
    },
    {
        "title": "변수·입춘·절입 시주",
        "body": (
            "【절기】사주 월지는 입춘(立春) 기준으로 바뀐다. 입춘 전후 며칠은 "
            "「절기 경계 — 월지 확인 필요」를 한 줄 명시한다. 시주는 분 단위 "
            "민감할 수 있어 2시간 범위(時辰)로만 쓰고 분 단정은 피한다. "
            "윤달·양력 변환 오류 시 일주만 참고용으로 풀 수 있다고 안내한다."
        ),
    },
    {
        "title": "변수·괴강(魁罡)",
        "body": (
            "【괴강】庚辰·庚戌·壬辰·戊戌 일주 등. 강한 의지·독립·리더·완고. "
            "「흉살」 단정 금지 — 책임·압박·조직 내 마찰을 「성향」으로만. "
            "관성·비겁과 겹치면 협업·지분·규칙 명확화를 권한다. 본격(격·용신) 우선."
        ),
    },
    {
        "title": "변수·천덕·월덕",
        "body": (
            "【천덕·월덕】위기 시 도움·완충·인복 보조 신살. 천을귀인과 비슷한 톤으로 "
            "「귀인·멘토·지원」만. 사건·시기 단정 금지. 격국·용신 다음 1~2문장 보조."
        ),
    },
    {
        "title": "변수·대운 교운기",
        "body": (
            "【교운】대운이 바뀌는 해 전후 1~2년은 과도기. 직장·거주·관계·재정 "
            "「조정·선택」 키워드. 좋다/나쁘다보다 환경 재배치. "
            "이전 대운과 다음 대운의 십신 대비로 톤만 잡고 사건 단정은 금지한다."
        ),
    },
    {
        "title": "변수·일운 참고",
        "body": (
            "【일운】당일 천간·지지를 일간 십신으로 환산해 「오늘의 톤」 1~2문장. "
            "월운·세운보다 가볍게. 중요 결정은 세운·대운과 함께 보라고 안내. "
            "투자·이사·수술 날짜 단정 금지."
        ),
    },
    {
        "title": "변수·신살 학당",
        "body": (
            "【학당】문창과 유사 — 시험·자격·기록·학원·온라인 강의. "
            "인성·문창·학당이 겹칠 때 학습운 강조(참고). 합격·불합격 단정 금지. "
            "신살만으로 길흉 결정하지 않는다."
        ),
    },
    {
        "title": "변수·비겁격",
        "body": (
            "【비겁격】월지 비견·겁재. 자아·경쟁·협업·분재·독립 테마. "
            "재성·관성이 약하면 현실화·규율 보완. 사업 파트너는 지분·역할 명시 권장. "
            "월지 본기 기준, 종격 여부는 일간 강약으로 별도 검토만 언급."
        ),
    },
    {
        "title": "변수·태원·명궁 보조",
        "body": (
            "【태원·명궁】태원(胎元)=선천·모체·잠재, 명궁=인생 방향 보조. "
            "본원 사주(년월일시) 다음 참고층. 단독으로 용신 단정 금지. "
            "무료 풀이에서는 생략 가능 — 있으면 1문장 보조만."
        ),
    },
    {
        "title": "변수·복인·윤달 참고",
        "body": (
            "【복인·윤달】절기·시주 계산 시 만세력·입춘·중기·윤달 여부를 확인한다. "
            "오류 시 일주 중심 참고용으로 전환. 사용자에게 「생시·절기 확인 권장」 "
            "한 줄. 잘못된 시주로 단정 예언 금지."
        ),
    },
    {
        "title": "변수·납음 甲子海中金",
        "body": (
            "【납음 예】甲子 — 海中金(해중금). 깊은 잠재력·내수·유통·적응. "
            "년·일 납음 보조로 쓰고 용신 단정 금지. 오행 개수·월지 격이 우선. "
            "참고용이며 확정 예언·의학·법률 단정은 금지한다."
        ),
    },
    {
        "title": "변수·납음 庚午路旁土",
        "body": (
            "【납음 예】庚午 — 路旁土(노방토). 길·이동·현장·실무·서비스. "
            "화가 단련한 금·토 조합. 납음만으로 직업·재물 단정 금지. "
            "십신·대운과 함께 「현장·유통·기술」 톤 참고만."
        ),
    },
    {
        "title": "변수·천간충(甲庚·乙辛 등)",
        "body": (
            "【천간충】甲庚、乙辛、丙壬、丁癸 등 — 겉·속 갈등·급한 결정. "
            "지지 충과 겹치면 변동 키워드만. 「사고·파산」 단정 금지. "
            "조율·속도 조절·상대 오행 보완을 권한다."
        ),
    },
    {
        "title": "변수·지지 삼형(寅巳申)",
        "body": (
            "【삼형】寅巳申(무은之刑)、丑戌未、子卯 등 — 압박·자기갈등·관계 마찰. "
            "형만으로 흉 단정 금지. 세운·월운에서 해당 지지가 성립할 때만 언급. "
            "의학·법률·사고 예언 금지."
        ),
    },
    {
        "title": "변수·건강 서술 톤(非医学)",
        "body": (
            "【건강 톤】오행 과다·부족·신살 병·쇠 등으로 「컨디션·리듬·휴식」만. "
            "질병명·수명·수술 시기 단정 금지. 「전문 의료 상담 권장」 필수. "
            "토=소화 리듬, 수=수면, 화=번아웃 등 생활 습관 조언 수준."
        ),
    },
    {
        "title": "무료풀이·PASS 카드 조합",
        "body": (
            "【조합 풀이】위원회 PASS 인증 카드가 2장 이상 맞으면 LLM 없이 "
            "카드 본문을 이어 붙여 무료 풀이 초안을 만든다. FAIL·미검증 카드는 "
            "RAG·조합에서 제외. 부족하면 LLM 보조. 각 절마다 참고용 면책 문구 유지."
        ),
    },
]

# P0 — 심층 10섹션 매칭·Groq 보축 최소화 (띠·칠살·희신·조후·원진)
_AUTO_ZODIAC: list[tuple[str, str, str]] = [
    ("자", "鼠", "子"),
    ("축", "牛", "丑"),
    ("인", "虎", "寅"),
    ("묘", "兔", "卯"),
    ("진", "龙", "辰"),
    ("사", "蛇", "巳"),
    ("오", "马", "午"),
    ("미", "羊", "未"),
    ("신", "猴", "申"),
    ("유", "鸡", "酉"),
    ("술", "狗", "戌"),
    ("해", "猪", "亥"),
]

AUTO_CARD_POOL_P0: list[dict] = [
    {
        "title": f"변수·띠 {ko}({han})",
        "body": (
            f"【띠·지지】{ko}띠 — 지지 {ji}({han}). 년지·일지에 있으면 성향·인연·가족 "
            f"테마에 투영. 띠만으로 길흉·직업·결혼 시기 단정 금지. "
            f"일간·격국·용신과 함께 본다. 참고용이며 확정 예언·의학·법률 단정은 금지한다."
        ),
    }
    for ko, han, ji in _AUTO_ZODIAC
]
AUTO_CARD_POOL_P0.extend(
    [
        {
            "title": "변수·격 칠살격",
            "body": (
                "【칠살격】월지 편관(七殺)이 격을 이루는 경우. 압박·경쟁·권위·실행력·"
                "위기 속 성취 테마. 식신·인성으로 제어·학습·완충. "
                "「흉격」 단정 금지 — 직장·법규·건강 리듬만 참고. 일간 강약·종격은 별도 검토."
            ),
        },
        {
            "title": "변수·격 종격(從格) 참고",
            "body": (
                "【종격】일간이 극약해 월지·사주 기세를 따르는 격. "
                "종재·종살·종아·종왕 등 학파별 분류. "
                "「반드시」 단정 금지 — 강약·계절·대운과 함께 「참고 견해」로만 서술."
            ),
        },
        {
            "title": "변수·격 잡격·무격 참고",
            "body": (
                "【잡격·무격】월지 본기가 불명확하거나 여러 십신이 겹칠 때. "
                "일간·오행 개수·대운으로 주제를 잡고 한 격만 고집하지 않는다. "
                "무료 풀이에서는 「격 확인 필요」 한 줄 후 십신·용신 중심으로 풀이."
            ),
        },
        {
            "title": "변수·지지관계 원진",
            "body": (
                "【원진】子未·丑午·寅酉·卯申·辰亥·巳戌 — 거리감·오해·소모·인간 마찰. "
                "충·형과 겹치면 관계·이동 키워드만. 이혼·불화·사고 단정 금지. "
                "소통·기대 조절·역할 분담을 권한다."
            ),
        },
        {
            "title": "변수·조후(寒暖燥濕) 참고",
            "body": (
                "【조후】한난·조습·건조로 사주의 균형 방향을 보는 견해. "
                "억부·통관과 충돌할 수 있어 「학파·환경에 따라 다름」 명시. "
                "용신·기신 다음 참고층 — 오행 과다·부족과 함께 서술."
            ),
        },
    ]
    + [
        {
            "title": f"변수·희신 {el}",
            "body": (
                f"【희신】{el}行이 균형·기운을 돕는 방향으로 읽히는 경우(학파별 상이). "
                f"용신과 겹치면 보완 톤, 기신과 겹치면 조절·완충. "
                f"「반드시 {el}」 단정 금지 — 대운·세운·직업·연애는 십신 조합으로 연결."
            ),
        }
        for el in ("목", "화", "토", "금", "수")
    ]
)

# 풀이에 가장 자주 걸리는 해석형 (일주·테마·관계·운)
HIGH_USAGE_INTERPRETIVE_POOL: list[dict] = [
    {
        "title": "해석·충·합·형·파·해 종합",
        "body": (
            "지지 충은 변동·이동, 합은 인연·결합, 형은 압박·자기갈등, "
            "파·해는 재정비·소모. 겉 합 속 충은 양면 서술. 시기는 세운·월운만."
        ),
        "usage_tags": ["연애", "합", "충", "관계"],
    },
    {
        "title": "해석·십신·격국 한눈에",
        "body": (
            "월지 격국과 두드러진 십신 2~3개로 직장·재물·관계 큰 틀. "
            "한 십신만으로 길흉 단정 금지."
        ),
        "usage_tags": ["십신", "격국", "격"],
    },
    {
        "title": "해석·오행 과다·부족 실전",
        "body": (
            "오행 과다=강점+과잉, 부족=보완 습관. 상생상극으로 방향만."
        ),
        "usage_tags": ["오행", "목", "화", "토", "금", "수"],
    },
    {
        "title": "해석·대운·세운·월운 흐름",
        "body": (
            "대운 10년 흐름, 세운 올해, 월운 1~2문장. 사건·날짜 단정 금지."
        ),
        "usage_tags": ["대운", "세운", "월운", "운"],
    },
    {
        "title": "해석·일지·배우자궁 연애",
        "body": (
            "일지·도화·합충으로 소통·공간·기대 조절. 이혼·만남 시기 단정 금지."
        ),
        "usage_tags": ["연애", "배우자", "일지", "도화"],
    },
    {
        "title": "해석·재성·현금흐름",
        "body": (
            "정재·편재·식상생재로 수입·지출·계약. 종목·대박 단정 금지."
        ),
        "usage_tags": ["재물", "재성", "정재", "편재"],
    },
    {
        "title": "해석·관성·직장·책임",
        "body": (
            "정관·편관으로 조직·압박·규율. 승진·시기 단정 금지."
        ),
        "usage_tags": ["관성", "직업", "직장", "정관", "편관"],
    },
    {
        "title": "해석·식신·상관·표현·창업",
        "body": (
            "식상 강하면 기술·말·창업. 과다 시 규칙·집중 이슈."
        ),
        "usage_tags": ["식신", "상관", "직업", "창업"],
    },
    {
        "title": "해석·인성·학습·자격",
        "body": (
            "인성·문창·학당 겹치면 학습·기록 톤. 합격 날짜 단정 금지."
        ),
        "usage_tags": ["인성", "학습", "자격"],
    },
    {
        "title": "해석·비겁·협업·지분",
        "body": (
            "비겁 과다 시 고집·동업·지분·계약 명시."
        ),
        "usage_tags": ["비견", "겁재", "협업"],
    },
    {
        "title": "해석·용신·기신·균형",
        "body": (
            "용신·기신·희신은 학파별 상이. 대운과 방향만 참고."
        ),
        "usage_tags": ["용신", "기신", "희신"],
    },
    {
        "title": "해석·궁합·두 명식 비교",
        "body": (
            "일간·일지·대운 비교. 보완·마찰 포인트만."
        ),
        "usage_tags": ["궁합", "연애", "관계"],
    },
]

# P0(띠·칠살 등) 완료 후 → 고빈도 일주·테마 → 해석 풀 → 희규 변수(phase3)
HIGH_USAGE_AUTO_POOL: list[dict] = list(AUTO_CARD_POOL)

AUTO_CARD_POOL_FULL: list[dict] = (
    HIGH_USAGE_AUTO_POOL
    + AUTO_CARD_POOL_P0
    + AUTO_CARD_POOL_PHASE3
)

# 해석형 본문 카드 — 제목 해석· 접두, 작성 시 서술형 풀이 구조로 확장
INTERPRETIVE_CARD_POOL: list[dict] = [
    {
        "title": "해석·관성 강한 명식 풀이",
        "body": "정관·편관이 강한 경우 직장·책임·규율 테마. 스트레스 완화는 식상·인성.",
    },
    {
        "title": "해석·재성·재물운 풀이",
        "body": "정재·편재 비중으로 수입·지출·계약. 식상생재면 창업·기술 수익.",
    },
    {
        "title": "해석·연애·배우자궁 풀이",
        "body": "일지·도화·관성으로 소통·공간. 이혼·만남 시기 단정 금지.",
    },
    {
        "title": "해석·직업·이직 흐름",
        "body": "관성·식상·인성으로 조직 vs 자유. 세운·대운 겹칠 때만 변동.",
    },
    {
        "title": "해석·식상·표현·창업",
        "body": "식신·상관 강하면 말·기술·마케팅. 과다 시 규칙·집중 이슈.",
    },
    {
        "title": "해석·인성·학습·자격",
        "body": "정인·편인·문창·학당. 시험 합격 단정 없이 학습·기록 톤.",
    },
    {
        "title": "해석·비겁·협업·분재",
        "body": "비견·겁재 과다 시 고집·지분. 역할·계약 명확화.",
    },
    {
        "title": "해석·대운 전환기",
        "body": "대운 교체 전후 1~2년 과도기. 환경 재배치 키워드.",
    },
    {
        "title": "해석·세운·올해 흐름",
        "body": "올해 천간·지지를 일간 십신으로. 월운은 하이라이트만.",
    },
    {
        "title": "해석·오행 불균형 보완",
        "body": "과다 오행=과잉, 부족=노력. 상생상극으로 방향.",
    },
    {
        "title": "해석·용신·기신 실전",
        "body": "신강신약·억부. 조후·통관은 참고만.",
    },
    {
        "title": "해석·궁합·연인 비교",
        "body": "일간·일지·대운 비교. 보완·마찰 포인트.",
    },
    {
        "title": "해석·일주만 빠른 상담",
        "body": "시주 미상. 일간·일지 중심 5~8문장.",
    },
    {
        "title": "해석·건강·컨디션 리듬",
        "body": "오행·신살로 휴식·습관만. 의학 단정 금지.",
    },
    {
        "title": "해석·가족·육친 톤",
        "body": "년·월·시주로 부모·형제·자녀. 역할·거리감.",
    },
    {
        "title": "해석·사업·파트너십",
        "body": "편재·비겁·합충. 지분·계약·현금흐름.",
    },
    {
        "title": "해석·시험·승진 참고",
        "body": "관인·문창·인성. 합격·시기 단정 금지.",
    },
    {
        "title": "해석·이동·이직·역마",
        "body": "역마·충·합·편관. 이동 가능성만.",
    },
    {
        "title": "해석·말년·시주 운세",
        "body": "시주·대운 말년. 자녀·실행·휴식.",
    },
    {
        "title": "해석·종합 무료 풀이 샘플",
        "body": "인사→팔자→오행→십신→용신→대운→테마→조언→면책.",
    },
]

INTERPRETIVE_CARD_POOL_PHASE2: list[dict] = [
    {
        "title": "해석·도화·인연 매력",
        "body": (
            "도화는 인연·매력·사교의 보조 신살로, 일지·세운과 겹칠 때 "
            "관계 이슈가 부각될 수 있습니다. 이혼·불륜 단정 없이 소통·경계만."
        ),
    },
    {
        "title": "해석·역마·이동·해외",
        "body": (
            "역마는 이동·출장·유학·해외·환경 변화 키워드. "
            "충·합과 겹치면 이직·이사 가능성만, 시기 단정은 하지 않습니다."
        ),
    },
    {
        "title": "해석·화개·고독·창작",
        "body": (
            "화개는 고독·연구·종교·예술·기록에 가깝게 읽히기도 합니다. "
            "관계에서 거리감이 생길 수 있어 의도적 소통을 권합니다."
        ),
    },
    {
        "title": "해석·천을귀인·귀인운",
        "body": (
            "천을귀인은 위기 시 도움·멘토·완충. 사건 시기 단정 없이 "
            "「지원·조언을 구하기 좋은 흐름」 정도로만 안내합니다."
        ),
    },
    {
        "title": "해석·월운·이번 달 흐름",
        "body": (
            "월운은 해당 월의 천간·지지를 일간 십신으로 환산해 "
            "1~2문장 하이라이트. 중요 결정은 세운·대운과 함께 보라고 안내."
        ),
    },
    {
        "title": "해석·자녀·시주·식상",
        "body": (
            "시주·식상·편관 등으로 자녀·후손·창의·말년 실행을 봅니다. "
            "자녀 성별·수 단정 금지, 양육·소통·역할로 서술."
        ),
    },
    {
        "title": "해석·부부궁·일지 충합",
        "body": (
            "일지 충은 마찰·속도 차, 합은 끌림·결합. "
            "배우자 성격 단정 대신 생활·공간·재정 협의를 제안."
        ),
    },
    {
        "title": "해석·창업·사업 적성",
        "body": (
            "편재·식상·역마·비겁으로 사업·프리랜스 적성. "
            "성공·실패·시기 단정 없이 현금흐름·파트너·계약을 강조."
        ),
    },
    {
        "title": "해석·직장 스트레스·관살",
        "body": (
            "관성 과다·관살 겹침은 압박·규율·책임. "
            "식상·인성으로 완화, 퇴사·해고 시기는 쓰지 않습니다."
        ),
    },
    {
        "title": "해석·재물·지출·저축",
        "body": (
            "정재는 안정 수입·저축, 편재는 변동·프로젝트. "
            "재다신약이면 지출 구조·버퍼·역할 분담을 조언."
        ),
    },
    {
        "title": "해석·학업·문창·자격",
        "body": (
            "인성·문창·학당이 겹치면 학습·기록·시험 준비 톤. "
            "합격·불합격·날짜 단정 없이 습관·커리큘럼만."
        ),
    },
    {
        "title": "해석·명예·체면·관성",
        "body": (
            "정관·편관·관성 강하면 명분·체면·조직 내 위치. "
            "과하면 자기억압·완벽주의, 표현·휴식으로 균형."
        ),
    },
    {
        "title": "해석·내향·외향 성향",
        "body": (
            "일간 음양·오행으로 말·행동 에너지 방향. "
            "내향이어도 식상·화 기운이면 표현력이 살아날 수 있음."
        ),
    },
    {
        "title": "해석·번아웃·휴식",
        "body": (
            "화·토·관성 과다·신살 병 등으로 컨디션·수면·리듬. "
            "의학 진단·약물 단정 금지, 생활 습관·전문 상담 권장."
        ),
    },
    {
        "title": "해석·인맥·비겁·합",
        "body": (
            "비겁·합·삼합으로 협업·동업·친구·경쟁. "
            "지분·역할·계약서 명시를 권하며 배신·손실 단정은 피함."
        ),
    },
]

# 대운·세운 십신·테마 — 6번 섹션 매칭·운세 풀이 보강 (docs/SAJU-DEEP-READING-CARD-GUIDE.md)
_DAEUN_SEUN_FOOTER = (
    " 시기·사건·날짜 단정은 하지 않으며, 본 내용은 명리 참고용입니다."
)

DAEUN_SEUN_CARD_POOL: list[dict] = [
    {
        "title": "해석·세운·비겁·올해",
        "body": (
            "【시기·운세】【세운·비겁】올해 세운이 일간 기준 비견·겁재에 해당하면 "
            "경쟁·협업·자존감·지분·역할 분담 키워드가 부각됩니다. "
            "동료·친구·동업 관계에서 속도 차이·고집·계약 범위를 먼저 맞추는 것이 "
            "안정에 가깝습니다. 대운과 겹치면 확대·조정 톤을 함께 보되, "
            "승부·손실·파산 등은 쓰지 않습니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "비겁", "비견", "겁재", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·세운·식상·올해",
        "body": (
            "【시기·운세】【세운·식상】세운이 식신·상관에 가까우면 표현·기술·"
            "창업·이직·콘텐츠·말·기록 테마가 살아납니다. "
            "과다하면 규칙·집중·번아웃만 조심하면 되고, "
            "「반드시 창업·이직」처럼 단정하지 않습니다. "
            "대운에서 관성·재성과 조합해 직장·수입 흐름만 참고합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "식상", "식신", "상관", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·세운·재성·올해",
        "body": (
            "【시기·운세】【세운·재성】세운에 정재·편재 기운이 오면 "
            "수입·지출·계약·저축·프로젝트 수익 키워드를 「가능성」으로만 안내합니다. "
            "식상생재 구조와 겹치면 기술·표현이 재물로 이어지기 쉬운 흐름으로 읽을 수 "
            "있습니다. 종목·대박·파산·특정 날짜는 쓰지 않으며, "
            "현금흐름·계약서·버퍼 관리를 실천 조언으로 드립니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "재성", "재물", "정재", "편재", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·세운·관성·올해",
        "body": (
            "【시기·운세】【세운·관성】세운이 정관·편관에 가깝면 "
            "직장·책임·규율·승진·압박·자격·시험 테마가 올라올 수 있습니다. "
            "「합격·승진 확정」은 금지하고, 준비·기록·소통·휴식 리듬을 권합니다. "
            "대운과 방향이 같으면 역할 확대, 기신과 겹치면 속도 조절 톤만 붙입니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "관성", "정관", "편관", "직업", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·세운·인성·올해",
        "body": (
            "【시기·운세】【세운·인성】세운에 정인·편인 기운이 있으면 "
            "학습·자격·휴식·이동·멘토·기록·내면 정리 키워드가 강해집니다. "
            "공부운·자격운은 세운·월운에서 인성이 두드러질 때만 언급합니다. "
            "의학·입시 결과 단정은 하지 않으며, 습관·일정·수면을 실천 조언으로 드립니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "인성", "정인", "편인", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·대운·비겁·10년",
        "body": (
            "【시기·운세】【대운·비겁】현재 대운이 비견·겁재에 가깝면 "
            "약 10년 큰 흐름에서 자아·협업·경쟁·지분·독립성이 반복 주제가 됩니다. "
            "천간은 겉 역할·환경, 지지는 속마음·가정·내부 분위기로 읽습니다. "
            "교운 전후 1~2년은 과도기로만 안내하며, "
            "동업·계약·역할을 문서로 남기는 것을 권합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "비겁", "비견", "겁재", "운", "교운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·대운·식상·10년",
        "body": (
            "【시기·운세】【대운·식상】대운에 식신·상관이 중심이면 "
            "10년 흐름에서 표현·기술·교육·창업·콘텐츠·이직 가능성 키워드가 "
            "반복됩니다. 관성·재성과의 조합으로 「조직 vs 자유」 톤만 잡고, "
            "성패·시기 단정은 하지 않습니다. 용신 방향과 맞으면 확장, "
            "기신과 겹치면 집중·규칙 정리를 권합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "식상", "식신", "상관", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·대운·재성·10년",
        "body": (
            "【시기·운세】【대운·재성】대운에 정재·편재가 두드러지면 "
            "재물·계약·가계·사업·프로젝트가 10년 큰 줄기가 됩니다. "
            "비겁·식상과의 상생·상극으로 「수입원·지출·저축 성향」만 설명하고, "
            "투자·종목·파산·대박은 쓰지 않습니다. "
            "세운·월운은 해당 해·달 하이라이트로만 덧붙입니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "재성", "재물", "정재", "편재", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·대운·관성·10년",
        "body": (
            "【시기·운세】【대운·관성】대운이 정관·편관 중심이면 "
            "조직·규율·책임·자격·압박·사회적 역할이 10년 흐름의 축이 됩니다. "
            "식상·인성으로 스트레스 완화 방향을 함께 보며, "
            "승진·해고·시험 합격 날짜는 단정하지 않습니다. "
            "세운에서 충·합이 있으면 변동·이동 키워드만 「가능성」으로 붙입니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "관성", "정관", "편관", "직업", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·대운·인성·10년",
        "body": (
            "【시기·운세】【대운·인성】대운에 인성이 강하면 "
            "학습·자격·보호·휴식·이동·멘토·기록이 10년 큰 테마가 됩니다. "
            "식상·재성과 균형을 맞추면 실행·수익으로 이어지기 쉽고, "
            "과다하면 생각만 많아질 수 있어 일정·기록·작은 실행을 권합니다. "
            "세운·월운은 그해·그달 강조점만 1~2문장으로 보조합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "인성", "정인", "편인", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·용신·대운·확장",
        "body": (
            "【시기·운세】【용신·대운】대운 천간·지지가 용신·희신 방향과 "
            "맞을 때만 「확장·회복·집중·기회」 키워드를 붙입니다. "
            "학파·신강신약에 따라 용신 해석은 달라질 수 있음을 한 번 언급하고, "
            "「무조건 대길」 표현은 쓰지 않습니다. "
            "세운이 같은 방향이면 톤을 조금 키우고, 기신과 겹치면 속도 조절만 안내합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "용신", "희신", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·기신·대운·조절",
        "body": (
            "【시기·운세】【기신·대운】대운이 기신·과다 오행·충·극 방향과 "
            "겹치면 「조절·정리·인내·버퍼」 키워드로만 서술합니다. "
            "공포·파산·사고·이혼 단정은 금지하고, "
            "계약·건강 리듬·감정 정리·지출 관리를 실천 조언으로 드립니다. "
            "세운·월운에서 완화 기운이 오면 「호흡·회복」 정도만 덧붙입니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "기신", "용신", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·대운·세운·충돌·과도기",
        "body": (
            "【시기·운세】【대운·세운】대운과 세운이 충·형·파·해로 "
            "맞닿으면 「변동·이동·관계·재정 재배치」 키워드만 씁니다. "
            "대운·세운이 서로 다른 십신을 강조할 때는 "
            "「큰 줄기 vs 올해 색깔」을 분리해 말하면 모순이 줄어듭니다. "
            "교운 전후 1~2년·충돌 시기 모두 「과도기·선택」 톤으로만 안내합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["대운", "세운", "월운", "충", "합", "운", "교운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·재물·세운·테마",
        "body": (
            "【테마 풀이】【재물·세운】올해 세운이 재성·식상생재와 "
            "겹치면 수입·지출·계약·저축·프로젝트 이슈가 "
            "「가능성」으로 부각될 수 있습니다. "
            "정재는 안정·가계, 편재는 변동·사업·외부 기회 톤입니다. "
            "대운 재성 흐름과 함께 보되, 종목·날짜·대박 단정은 하지 않습니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "재물", "재성", "정재", "편재", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·연애·세운·테마",
        "body": (
            "【테마 풀이】【연애·세운】세운·월운에서 일지·도화·합·충이 "
            "성립할 때만 관계·소통·거리·기대 조절 키워드를 붙입니다. "
            "관성·재성 비중으로 연애 톤만 조정하며, "
            "만남·이혼·불륜·자녀 시기 단정은 금지합니다. "
            "대운과 세운을 분리해 「10년 큰 흐름 vs 올해」로 말하면 "
            "해석이 안정적입니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "연애", "도화", "합", "충", "운"],
        "card_style": "interpretive",
    },
    {
        "title": "해석·직업·세운·테마",
        "body": (
            "【테마 풀이】【직업·세운】세운에 관성·식상·역마·충·합이 "
            "겹치면 이직·이동·역할 변경·프로젝트 전환 "
            "「가능성」만 언급합니다. "
            "조직 vs 자유·기술 vs 관리 톤은 월지 격국·두드러진 십신으로 잡고, "
            "회사명·승진·합격 날짜는 쓰지 않습니다. "
            "대운 직업 줄기와 올해 세운을 함께 참고합니다."
            + _DAEUN_SEUN_FOOTER
        ),
        "tags": ["세운", "대운", "직업", "관성", "식상", "운"],
        "card_style": "interpretive",
    },
]

INTERPRETIVE_CARD_POOL_FULL: list[dict] = (
    DAEUN_SEUN_CARD_POOL
    + HIGH_USAGE_INTERPRETIVE_POOL
    + INTERPRETIVE_CARD_POOL
    + INTERPRETIVE_CARD_POOL_PHASE2
)


def _existing_titles() -> set[str]:
    return {(c.get("title") or "").strip() for c in learn.list_cards(limit=800)}


def _normalize_high_usage_spec(spec: dict) -> dict:
    """고빈도 풀 — 해석형 상담 본문으로 확장."""
    title = (spec.get("title") or "").strip()
    body = spec.get("body") or ""
    style = spec.get("card_style")
    if not title.startswith(("해석·", "변수·", "심층·")):
        title = f"해석·{title}"[:120]
        style = "interpretive"
    elif title.startswith("변수·") and usage_score_for_spec(spec) >= 150:
        style = style or "variable"
    else:
        style = style or ("interpretive" if title.startswith("해석·") else "variable")
    return {**spec, "title": title, "body": body, "card_style": style}


def _pending_from_pool(
    pool: list[dict],
    titles: set[str],
    *,
    high_usage_only: bool = False,
) -> list[dict]:
    inv = get_inventory()
    pending = [
        s
        for s in pool
        if _normalize_high_usage_spec(s).get("title", "").strip() not in titles
    ]
    if high_usage_only:
        pending = [
            s
            for s in pending
            if usage_score_for_spec(s, inventory=inv) >= 100
        ]
    return sort_specs_by_usage(pending, inventory=inv)


def ingest_p0_pool(*, sleep_sec: float = 0) -> int:
    """P0 풀(띠·칠살·희신·조후·원진)만 전부 추가."""
    titles = {c.get("title") for c in learn.list_cards(limit=500)}
    pending = [s for s in AUTO_CARD_POOL_P0 if s["title"] not in titles]
    added = 0
    for s in pending:
        card = learn.add_card(
            body=s["body"],
            title=s["title"],
            source="auto_pool_p0",
            card_style="variable",
        )
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid, export_pack_now=False)
        titles.add(s["title"])
        added += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if added:
        learn.export_pack()
    return added


def ingest_pool(
    *,
    max_add: int | None = None,
    all_pool: bool = False,
    sleep_sec: float = 0,
    high_usage_only: bool = True,
) -> int:
    titles = _existing_titles()
    pending = _pending_from_pool(
        AUTO_CARD_POOL_FULL, titles, high_usage_only=high_usage_only
    )
    if high_usage_only and not pending:
        pending = _pending_from_pool(
            AUTO_CARD_POOL_FULL, titles, high_usage_only=False
        )
        pending = [s for s in pending if usage_score_for_spec(s) >= 80]
        pending = sort_specs_by_usage(pending, inventory=get_inventory())
    if not all_pool and max_add is not None:
        pending = pending[: max(0, max_add)]
    elif not all_pool:
        pending = pending[:5]

    added = 0
    for raw in pending:
        s = _normalize_high_usage_spec(raw)
        card = learn.add_card(
            body=s["body"],
            title=s["title"],
            source="auto_pool_high_usage" if high_usage_only else "auto_pool",
            card_style=s.get("card_style"),
        )
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid, export_pack_now=False)
        titles.add(s["title"])
        added += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    if added:
        learn.export_pack()
    return added


def ingest_interpretive_pool(
    *,
    max_add: int | None = None,
    all_pool: bool = False,
    sleep_sec: float = 0,
    high_usage_only: bool = True,
) -> int:
    titles = _existing_titles()
    inv = get_inventory()
    if high_usage_only:
        pending = _pending_from_pool(
            HIGH_USAGE_INTERPRETIVE_POOL, titles, high_usage_only=False
        )
        if not pending:
            pending = _pending_from_pool(
                INTERPRETIVE_CARD_POOL_FULL, titles, high_usage_only=True
            )
    else:
        pending = _pending_from_pool(
            INTERPRETIVE_CARD_POOL_FULL, titles, high_usage_only=False
        )
    pending = sort_specs_by_usage(pending, inventory=inv)
    if not all_pool and max_add is not None:
        pending = pending[: max(0, max_add)]
    elif not all_pool:
        pending = pending[:3]

    added = 0
    for s in pending:
        card = learn.add_card(
            body=s["body"],
            title=s["title"],
            source="interpretive_high_usage" if high_usage_only else "interpretive_pool",
            card_style="interpretive",
        )
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid, export_pack_now=False)
        titles.add(s["title"])
        added += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if added:
        learn.export_pack()
    return added


def ingest_daeun_seun_pool(
    *,
    max_add: int | None = None,
    all_pool: bool = True,
    sleep_sec: float = 0,
) -> int:
    """대운·세운 십신·테마 카드 풀 — 6번 섹션 매칭 보강."""
    titles = _existing_titles()
    inv = get_inventory()
    pending = [
        s
        for s in DAEUN_SEUN_CARD_POOL
        if _normalize_high_usage_spec(s).get("title", "").strip() not in titles
    ]
    pending = sort_specs_by_usage(pending, inventory=inv)
    if not all_pool and max_add is not None:
        pending = pending[: max(0, max_add)]
    elif not all_pool:
        pending = pending[:16]

    added = 0
    for s in pending:
        card = learn.add_card(
            body=s["body"],
            title=s["title"],
            source="daeun_seun_pool",
            card_style=s.get("card_style") or "interpretive",
        )
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid, export_pack_now=False)
        extra_tags = s.get("tags") or []
        if extra_tags:
            merged = list(
                dict.fromkeys(list(card.get("tags") or []) + list(extra_tags))
            )[:12]
            learn.update_confirmed_card(cid, tags=merged)
        titles.add(s["title"])
        added += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if added:
        learn.export_pack()
    return added


def ingest_per_minute(
    total: int = 3,
    *,
    sleep_sec: float = 18,
    high_usage_only: bool = True,
) -> dict:
    """분당 N장 — 고빈도 해석·일주·테마 우선 (기본 80% 해석형)."""
    total = max(1, min(int(total), 10))
    n_int = max(1, (total * 4 + 4) // 5)
    n_var = max(0, total - n_int)
    v = ingest_pool(
        max_add=n_var, sleep_sec=sleep_sec, high_usage_only=high_usage_only
    )
    i = ingest_interpretive_pool(
        max_add=n_int, sleep_sec=sleep_sec, high_usage_only=high_usage_only
    )
    st = learn.stats()
    return {
        "per_minute_target": total,
        "high_usage_only": high_usage_only,
        "variable_added": v,
        "interpretive_added": i,
        "total_added": v + i,
        **st,
    }


def ingest_hourly(
    total: int = 10,
    *,
    sleep_sec: float = 3,
) -> dict:
    """시간당 N장 — 변수 풀·해석 풀 반반 (풀 소진 시 남은 쪽만)."""
    total = max(1, min(int(total), 30))
    n_var = (total + 1) // 2
    n_int = total // 2
    v = ingest_pool(max_add=n_var, sleep_sec=sleep_sec)
    i = ingest_interpretive_pool(max_add=n_int, sleep_sec=sleep_sec)
    st = learn.stats()
    return {
        "hourly_target": total,
        "variable_added": v,
        "interpretive_added": i,
        "total_added": v + i,
        **st,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="사주 학습 카드 자동 추가")
    p.add_argument("--max", type=int, default=5, help="이번 실행 최대 추가 건수")
    p.add_argument("--all", action="store_true", help="풀에 남은 카드 전부")
    p.add_argument(
        "--per-minute",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="분당 N장 (변수+해석, 기본 10, cron 권장)",
    )
    p.add_argument(
        "--hourly",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="시간당 N장 (변수+해석)",
    )
    p.add_argument(
        "--interpretive",
        action="store_true",
        help="해석형 본문 카드 풀만 추가",
    )
    p.add_argument(
        "--ingest-p0",
        action="store_true",
        help="P0 풀(띠12·칠살·희신5·조후·원진) 전부 추가",
    )
    p.add_argument(
        "--ingest-daeun-seun",
        action="store_true",
        help="대운·세운 십신·테마 카드 풀 전부 추가",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0,
        help="카드 추가 간 대기(초). 서버 부하 완화용",
    )
    p.add_argument(
        "--all-pool",
        action="store_true",
        help="희규 주제(phase3) 포함 전체 풀 (기본: 고빈도만)",
    )
    args = p.parse_args()
    high_usage_only = not args.all_pool

    if args.ingest_p0:
        added = ingest_p0_pool(sleep_sec=args.sleep or 1)
        st = learn.stats()
        print(f"p0_added={added} total={st['total']} confirmed={st['confirmed']}")
        return 0

    if args.ingest_daeun_seun:
        added = ingest_daeun_seun_pool(
            max_add=None if args.all else args.max,
            all_pool=args.all or args.ingest_daeun_seun,
            sleep_sec=args.sleep or 1,
        )
        st = learn.stats()
        print(
            f"daeun_seun_added={added} total={st['total']} "
            f"confirmed={st['confirmed']}"
        )
        return 0

    if args.per_minute is not None:
        n = 10 if args.per_minute is True else int(args.per_minute)
        print(
            ingest_per_minute(
                n, sleep_sec=args.sleep or 5, high_usage_only=high_usage_only
            )
        )
        return 0

    if args.hourly is not None:
        n = 10 if args.hourly is True else int(args.hourly)
        print(ingest_hourly(n, sleep_sec=args.sleep or 3))
        return 0

    max_add = None if args.all else args.max
    if args.interpretive:
        added = ingest_interpretive_pool(
            max_add=max_add,
            all_pool=args.all,
            sleep_sec=args.sleep,
            high_usage_only=high_usage_only,
        )
        kind = "interpretive"
    else:
        added = ingest_pool(
            max_add=max_add,
            all_pool=args.all,
            sleep_sec=args.sleep,
            high_usage_only=high_usage_only,
        )
        kind = "variable"
    st = learn.stats()
    print(
        f"auto_added={added} kind={kind} total={st['total']} "
        f"confirmed={st['confirmed']} pack={st['confirmed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
