"""agent_registry.json — 주식 시황부 젬마 에이전트 추가·갱신."""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BOARD / "data" / "agent_registry.json"

STOCK_AGENTS: list[dict] = [
    {
        "id": "stock_radar",
        "name": "시세젬마",
        "emoji": "📡",
        "role": "국내·미국 시세 수집",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 30,
        "interval_label": "30분",
        "job": "stock_watch_sync",
        "skills": [
            {
                "id": "kr-us-quotes",
                "title": "KOSPI·나스닥 스냅샷",
                "summary": "지수·관심종목 시세를 snapshots.json에 저장.",
            }
        ],
    },
    {
        "id": "stock_chart",
        "name": "차트젬마",
        "emoji": "📊",
        "role": "추세·등락 신호",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "stock_chart_pulse",
        "skills": [
            {
                "id": "trend-signal",
                "title": "당일·스냅샷 추세",
                "summary": "지수·종목 등락률로 강세·약세·횡보 신호를 정리.",
            }
        ],
    },
    {
        "id": "stock_rl",
        "name": "RL예측젬마",
        "emoji": "🎯",
        "role": "상승·하락·횡보 예측 (강화학습)",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 45,
        "interval_label": "45분",
        "job": "stock_rl_predict",
        "skills": [
            {
                "id": "rl-bandit",
                "title": "컨텍스트 밴딧 Q",
                "summary": "시세·차트·뉴스·애널 특징으로 방향 예측, 적중 시 가중치 학습.",
            }
        ],
    },
    {
        "id": "stock_analyst",
        "name": "애널리스트젬마",
        "emoji": "📈",
        "role": "리포트·목표가·투자의견",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 90,
        "interval_label": "90분",
        "job": "stock_analyst_pulse",
        "skills": [
            {
                "id": "analyst-report",
                "title": "증권사 리포트",
                "summary": "관심종목 애널리스트 리포트·목표가·컨센서스 웹 조사.",
            }
        ],
    },
    {
        "id": "stock_finance",
        "name": "제무젬마",
        "emoji": "📑",
        "role": "실적·PER·ROE 조사",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 120,
        "interval_label": "2시간",
        "job": "stock_finance_pulse",
        "skills": [
            {
                "id": "fundamental-web",
                "title": "재무 웹 팩트",
                "summary": "변동 큰 종목 위주 실적·밸류에이션 검색.",
            }
        ],
    },
    {
        "id": "stock_listener",
        "name": "댓글검증젬마",
        "emoji": "💬",
        "role": "종목 댓글·루머 교차 검증",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 25,
        "interval_label": "25분",
        "job": "stock_comment_verify",
        "skills": [
            {
                "id": "comment-fact-cross",
                "title": "댓글≠팩트",
                "summary": "증시 댓글을 웹 2회·당일 시세와 대조. 과장·불일치 시 주의 표시.",
            }
        ],
    },
    {
        "id": "stock_macro",
        "name": "금리·달러젬마",
        "emoji": "💱",
        "role": "금리·환율→증시 영향",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 75,
        "interval_label": "75분",
        "job": "stock_rates_dollar_pulse",
        "skills": [
            {
                "id": "rates-fx-impact",
                "title": "기준금리·USD/KRW",
                "summary": "한·미 금리·원달러와 코스피·미국 지수를 교차 해석.",
            }
        ],
    },
    {
        "id": "stock_bond",
        "name": "채권젬마",
        "emoji": "📊",
        "role": "국채·금리→증시",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 70,
        "interval_label": "70분",
        "job": "stock_bonds_pulse",
        "skills": [
            {
                "id": "bond-yield-curve",
                "title": "국채 수익률·곡선",
                "summary": "한·미 10년물·단기금리·채권 ETF와 코스피 교차 해석.",
            }
        ],
    },
    {
        "id": "stock_oil_war",
        "name": "원유·전쟁젬마",
        "emoji": "⚔️",
        "role": "유가·지정학→증시",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 65,
        "interval_label": "65분",
        "job": "stock_oil_war_pulse",
        "skills": [
            {
                "id": "oil-geopolitics",
                "title": "원유·분쟁 뉴스",
                "summary": "WTI·브렌트·중동·우크라 등 지정학과 코스피·업종 교차.",
            }
        ],
    },
    {
        "id": "stock_commodity",
        "name": "원자재젬마",
        "emoji": "🛢️",
        "role": "유가·금속·곡물 동향",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 80,
        "interval_label": "80분",
        "job": "stock_commodities_pulse",
        "skills": [
            {
                "id": "commodity-trend",
                "title": "원자재→섹터",
                "summary": "WTI·브렌트·금·구리·가스 시세와 코스피·업종 영향 교차.",
            }
        ],
    },
    {
        "id": "stock_disclosure",
        "name": "공시젬마",
        "emoji": "📋",
        "role": "DART·SEC 전자공시",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 90,
        "interval_label": "90분",
        "job": "stock_disclosure_pulse",
        "skills": [
            {
                "id": "dart-sec",
                "title": "전자공시·8-K",
                "summary": "DART·KRX·SEC 공시 검색, DART_API_KEY 시 API 보강.",
            }
        ],
    },
    {
        "id": "stock_government",
        "name": "정부발표젬마",
        "emoji": "🏛️",
        "role": "금융위·한은·연준 보도",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "stock_government_pulse",
        "skills": [
            {
                "id": "gov-press",
                "title": "정책·보도자료",
                "summary": "금융위·기재부·한은·연준·재무부 공식 보도 검색.",
            }
        ],
    },
    {
        "id": "stock_youtube",
        "name": "유튜브젬마",
        "emoji": "▶️",
        "role": "유튜브 증시·CEO 영상",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "stock_youtube_pulse",
        "skills": [
            {
                "id": "youtube-market",
                "title": "영상 브리핑",
                "summary": "코스피·미국·매크로·종목·CEO 관련 유튜브 영상 수집.",
            }
        ],
    },
    {
        "id": "stock_ceo",
        "name": "CEO멘트젬마",
        "emoji": "👔",
        "role": "CEO·경영진 발언",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 55,
        "interval_label": "55분",
        "job": "stock_ceo_remarks_pulse",
        "skills": [
            {
                "id": "ceo-remarks-cross",
                "title": "경영진 코멘트",
                "summary": "관심종목·대형주 CEO 발언을 웹·당일 시세와 교차.",
            }
        ],
    },
    {
        "id": "stock_press",
        "name": "기사젬마",
        "emoji": "📰",
        "role": "주요 언론 기사",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 50,
        "interval_label": "50분",
        "job": "stock_press_pulse",
        "skills": [
            {
                "id": "major-press",
                "title": "통신·경제지",
                "summary": "연합·한경·매경·로이터·CNBC 등 기사 수집.",
            }
        ],
    },
    {
        "id": "stock_news",
        "name": "최신정보젬마",
        "emoji": "📰",
        "role": "속보·시장 뉴스",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 45,
        "interval_label": "45분",
        "job": "stock_news_pulse",
        "skills": [
            {
                "id": "market-news",
                "title": "국내·미국·글로벌 뉴스",
                "summary": "코스피·나스닥·연준 이슈 웹 검색.",
            }
        ],
    },
    {
        "id": "stock_kr",
        "name": "국내시황젬마",
        "emoji": "🇰🇷",
        "role": "코스피·코스닥·대형주",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "stock_kr_brief",
        "skills": [
            {
                "id": "kr-macro",
                "title": "국내 지수 브리핑",
                "summary": "스냅샷 기준 국내 지수·종목 요약.",
            }
        ],
    },
    {
        "id": "stock_us",
        "name": "해외시황젬마",
        "emoji": "🇺🇸",
        "role": "S&P·나스닥·빅테크",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "stock_us_brief",
        "skills": [
            {
                "id": "us-macro",
                "title": "미국 지수 브리핑",
                "summary": "S&P·나스닥·관심 종목 등락 요약.",
            }
        ],
    },
    {
        "id": "stock_risk",
        "name": "리스크젬마",
        "emoji": "⚠️",
        "role": "변동성·알림 점검",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 30,
        "interval_label": "30분",
        "job": "stock_risk_scan",
        "skills": [
            {
                "id": "volatility-scan",
                "title": "급등락·알림",
                "summary": "임계치 이상 등락 종목·알림 건수 점검.",
            }
        ],
    },
    {
        "id": "stock_writer",
        "name": "글감젬마",
        "emoji": "✍️",
        "role": "블로그 글감 연계",
        "division": "stock-watch",
        "mode_on": True,
        "interval_minutes": 180,
        "interval_label": "3시간",
        "job": "stock_blog_hints",
        "skills": [
            {
                "id": "market-blog-topic",
                "title": "시황→글감",
                "summary": "당일 시황·뉴스에서 금융 블로그 주제 후보 제안.",
            }
        ],
    },
]


def _upsert_agent(agents: list, row: dict) -> str:
    aid = row["id"]
    for i, a in enumerate(agents):
        if isinstance(a, dict) and (a.get("id") or "").strip() == aid:
            merged = dict(a)
            merged.update(row)
            agents[i] = merged
            return "updated"
    agents.append(row)
    return "added"


def main() -> int:
    if not REGISTRY_PATH.is_file():
        print("registry missing:", REGISTRY_PATH)
        return 1
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    agents = data.get("agents") or []
    counts = {"added": 0, "updated": 0}
    for row in STOCK_AGENTS:
        action = _upsert_agent(agents, row)
        counts[action] = counts.get(action, 0) + 1
    data["agents"] = agents
    REGISTRY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"stock-watch agents: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
