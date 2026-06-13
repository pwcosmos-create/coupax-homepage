from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def _run_council(job_type: str) -> tuple[str, str, str]:
    try:
        import chief_dev_council
        tag, topic, context = chief_dev_council.get_random_topic(job_type)
        title, body = chief_dev_council.generate_debate_card(topic, context)
        return tag, title, body
    except Exception as e:
        return f"{job_type} 오류", "위원회 호출 실패", str(e)

def job_chief_arch_review(agent: dict) -> tuple[bool, str]:
    db_size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.is_file() else 0
    try:
        tag, title, body = _run_council("chief_arch_review")
        import agent_office_chief_dev_learn
        agent_office_chief_dev_learn.add_card(tag, title, body)
        msg = f"아키텍처 리뷰 ({_now()}): LLM 토론 생성 및 카드 저장 완료. DB 크기 {db_size_kb:.1f}KB."
    except Exception as e:
        msg = f"아키텍처 리뷰 오류: {e!s}"
    return True, msg

def job_chief_rag_crawler(agent: dict) -> tuple[bool, str]:
    try:
        tag, title, body = _run_council("chief_rag_crawler")
        import agent_office_chief_dev_learn
        agent_office_chief_dev_learn.add_card(tag, title, body)
        msg = f"RAG 상태 점검 ({_now()}): LLM 기반 RAG 최적화 논의 저장 완료."
    except Exception as e:
        msg = f"RAG 상태 점검 오류: {e!s}"
    return True, msg

def job_chief_devops_monitor(agent: dict) -> tuple[bool, str]:
    load_avg = "확인 불가"
    if os.path.exists("/proc/loadavg"):
        try:
            with open("/proc/loadavg", "r") as f:
                load_avg = f.read().split()[0]
                if float(load_avg) > 2.0:
                    import alert_notifier
                    alert_notifier.send_telegram_alert(
                        "서버 부하 경고",
                        f"현재 Oracle Server 1분 Load Average가 {load_avg}를 초과했습니다. 점검이 필요합니다.",
                        "🔥 위험"
                    )
        except Exception:
            pass
    try:
        tag, title, body = _run_council("chief_devops_monitor")
        body = f"(현재 서버 Load Avg: {load_avg})\n\n{body}"
        import agent_office_chief_dev_learn
        agent_office_chief_dev_learn.add_card(tag, title, body)
        msg = f"서버 리소스 점검 ({_now()}): 데브옵스 LLM 리뷰 완료. Load Avg {load_avg}."
    except Exception as e:
        msg = f"서버 점검 오류: {e!s}"
    return True, msg

def job_chief_web_search(agent: dict) -> tuple[bool, str]:
    try:
        tag, title, body = _run_council("chief_web_search")
        import agent_office_chief_dev_learn
        agent_office_chief_dev_learn.add_card(tag, title, body)
        msg = f"웹 서치/트렌드 스크랩 ({_now()}): Tech Radar 기반 LLM 분석 저장 완료."
    except Exception as e:
        msg = f"웹 서치 오류: {e!s}"
    return True, msg
