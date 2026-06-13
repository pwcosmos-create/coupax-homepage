import os
import sys

from pathlib import Path

# board/scripts 하위에 존재한다고 가정
BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_registry

def _build_chief_dev_agents() -> list[dict]:
    return [
        {
            "id": "chief-arch",
            "name": "수석 아키텍트 젬마",
            "emoji": "🏗️",
            "role": "아키텍처 설계 / 코드 리뷰",
            "division": agent_registry.DIVISION_CHIEF_DEV,
            "mode_on": False,
            "interval_minutes": 1,
            "interval_label": "항상",
            "job": "chief_arch_review",
            "skills": [
                {
                    "id": "코드 아키텍처 리뷰",
                    "summary": "Flask 백엔드 및 전체 워크플로우 효율성을 점검합니다."
                },
                {
                    "id": "보안 및 에러 감지",
                    "summary": "백그라운드에서 로그를 분석하여 보안 취약점과 에러를 찾습니다."
                }
            ]
        },
        {
            "id": "chief-rag",
            "name": "문서 수집기 젬마",
            "emoji": "📚",
            "role": "개발 문서 크롤링 / RAG",
            "division": agent_registry.DIVISION_CHIEF_DEV,
            "mode_on": False,
            "interval_minutes": 1,
            "interval_label": "항상",
            "job": "chief_rag_crawler",
            "skills": [
                {
                    "id": "공식 문서 크롤링",
                    "summary": "최신 개발 문서를 수집하여 Vector DB에 저장합니다."
                },
                {
                    "id": "지식 카드 정제",
                    "summary": "수석 개발자가 주입한 URL과 텍스트를 최적화된 형식으로 정제합니다."
                }
            ]
        },
        {
            "id": "chief-ops",
            "name": "DevOps 관리 젬마",
            "emoji": "⚙️",
            "role": "배포 / CI·CD 모니터링",
            "division": agent_registry.DIVISION_CHIEF_DEV,
            "mode_on": False,
            "interval_minutes": 1,
            "interval_label": "항상",
            "job": "chief_devops_monitor",
            "skills": [
                {
                    "id": "서버 모니터링",
                    "summary": "Oracle Cloud 서버 리소스 및 Flask 서비스 상태를 모니터링합니다."
                },
                {
                    "id": "자동화 배포 점검",
                    "summary": "CI/CD 스크립트 실행 결과를 추적합니다."
                }
            ]
        },
        {
            "id": "chief-web-search",
            "name": "웹 서치 젬마",
            "emoji": "🌐",
            "role": "최신 기술 동향 및 문서 웹 검색",
            "division": agent_registry.DIVISION_CHIEF_DEV,
            "mode_on": False,
            "interval_minutes": 1,
            "interval_label": "항상",
            "job": "chief_web_search",
            "skills": [
                {
                    "id": "Tech Radar 탐색",
                    "summary": "GitHub Trending 및 해외 블로그의 최신 기술 트렌드를 수집합니다."
                },
                {
                    "id": "기술 문서 검색",
                    "summary": "특정 에러나 프레임워크 문서의 최신 버전을 웹에서 검색하여 전달합니다."
                }
            ]
        }
    ]

def main() -> int:
    registry = agent_registry.load_registry()
    agents = registry.setdefault("agents", [])
    
    chief_dev_agents = _build_chief_dev_agents()
    chief_dev_ids = {a["id"] for a in chief_dev_agents}
    
    # Remove existing chief-dev agents
    agents = [a for a in agents if not (isinstance(a, dict) and a.get("division") == agent_registry.DIVISION_CHIEF_DEV)]
    
    # Append new agents
    agents.extend(chief_dev_agents)
    registry["agents"] = agents
    
    agent_registry.save_registry(registry)
    print(f"OK: merged {len(chief_dev_agents)} chief-dev agents.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
