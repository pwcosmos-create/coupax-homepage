#!/usr/bin/env python3
"""
무과금 사주 카드 무한 생성 공장 (Zero-Cost Continuous Factory)
- 하루 1500회, 분당 15회의 Google AI Studio 무료 API 제한을 철저히 준수합니다.
- 매 1시간마다 새로운 사주 뼈대를 5개씩 찾아서, 15초 간격으로 초고퀄리티 카드로 구워냅니다.
- 한 달 기준 약 3,600장의 프리미엄 사주 카드가 과금 0원으로 자동 생성됩니다.

실행법: python scripts/continuous_saju_factory.py
"""
import subprocess
import time
from datetime import datetime
from pathlib import Path
import sys

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

def run_factory():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- 무과금 사주 공장 1시간 주기 가동 시작 ---")
    
    # 1. 새로운 뼈대(초안) 생성 (최대 5개)
    print("  -> 1단계: 빈틈(Gap) 스캔 및 뼈대 생성 중...")
    try:
        subprocess.run(
            ["python", "scripts/saju_auto_add_cards.py", "--interpretive", "--max", "5"],
            cwd=str(BOARD),
            check=False
        )
    except Exception as e:
        print(f"  [오류] 1단계 오류: {e}")

    # 2. 15초 딜레이를 지키며 무료 API로 초고퀄리티 10,000자 살붙이기 (최대 5개)
    # --sleep 15 옵션이 과금 방지의 핵심입니다. (분당 4회 요청 제한 유지)
    print("  -> 2단계: Gemini API (무료 티어) 연결하여 10,000자 초고퀄리티 작성 중...")
    try:
        subprocess.run(
            ["python", "scripts/saju_card_llm_compose.py", "batch", "--count", "5", "--sleep", "15"],
            cwd=str(BOARD),
            check=False
        )
    except Exception as e:
        print(f"  [오류] 2단계 오류: {e}")
        
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 완료. 안전한 무료 한도 유지를 위해 1시간 동안 수면(Sleep)합니다.")

if __name__ == "__main__":
    print("==================================================")
    print("   젬마24 무과금 사주 자동화 공장 가동 준비 완료   ")
    print("==================================================")
    while True:
        try:
            run_factory()
            # 1시간(3600초) 대기 - 과금 방지를 위한 완벽한 방어막
            time.sleep(3600)
        except KeyboardInterrupt:
            print("\n공장 가동을 수동으로 중지합니다.")
            break
        except Exception as e:
            print(f"예기치 않은 오류 발생: {e}. 5분 후 재시도합니다.")
            time.sleep(300)
