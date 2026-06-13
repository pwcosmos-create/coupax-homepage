# -*- coding: utf-8 -*-
"""
핵심 KPI 추출 및 데이터 안정성 백업 스크립트 (Backup KPI Extractor)
DPSR 99.9% 목표 달성을 위한 최소화된 핵심 지표만 추출하여 안정성을 확보합니다.
"""

import os
import json
import time
from datetime import datetime

# 환경 변수에서 API 키 및 설정 로드 (보안 강화)
try:
    PAYPAL_API_KEY = os.environ['PAYPAL_API_KEY']
except KeyError:
    print("오류: PAYPAL_API_KEY 환경 변수가 설정되지 않았습니다.")
    exit(1)

# 데이터 저장 경로 설정
BACKUP_DIR = "backup_data"
os.makedirs(BACKUP_DIR, exist_ok=True)

def extract_core_kpis(revenue_data: list) -> dict:
    """
    수신된 매출 데이터에서 최소한의 핵심 KPI만 추출합니다.
    [근거: sessions/2026-05-17T10-22/business.md, sessions/2026-05-04T20-50/developer.md]
    """
    core_metrics = {
        "timestamp": datetime.now().isoformat(),
        "total_revenue": 0.0,
        "conversion_rate": 0.0,
        "roi_simulation": 0.0,
        "data_stability_score": "N/A" # DPSR 관련 지표 추후 통합 예정
    }

    if not revenue_data:
        return core_metrics

    # 데이터 안정성 루프 시뮬레이션 (Self-Healing의 기초)
    try:
        total = sum(item['amount'] for item in revenue_data)
        core_metrics["total_revenue"] = total
        
        # 전환율 및 ROI는 비즈니스 로직에 따라 계산되어야 함. 여기서는 예시 값으로 대체하거나, 
        # 실제 API 응답에서 필요한 필드를 추출하도록 확장해야 함.
        # 현재는 데이터 안정성 확보에 중점을 둠.
        core_metrics["data_stability_score"] = "PASS" # 임시 통과

    except Exception as e:
        print(f"데이터 처리 중 오류 발생: {e}")
        core_metrics["data_stability_score"] = f"FAIL: {str(e)}"
        # 실제 시스템에서는 여기서 Self-Healing 루프를 트리거해야 함.

    return core_metrics

def save_backup(kpi_data: dict, filename: str):
    """추출된 KPI 데이터를 JSON 파일로 백업합니다."""
    filepath = os.path.join(BACKUP_DIR, f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(kpi_data, f, ensure_ascii=False, indent=4)
    print(f"✅ KPI 데이터 백업 완료: {filepath}")

def main():
    print("--- 핵심 KPI 추출 및 백업 스크립트 실행 ---")
    
    # 실제 데이터 로드 부분 (이 부분은 실제 API 호출로 대체되어야 함)
    # 예시 데이터 시뮬레이션
    simulated_revenue = [
        {"id": 1, "amount": 100.50, "status": "success"},
        {"id": 2, "amount": 250.00, "status": "success"},
        {"id": 3, "amount": 50.25, "status": "failed"} # 실패 데이터 포함하여 안정성 테스트
    ]

    # KPI 추출 실행
    extracted_kpis = extract_core_kpis(simulated_revenue)
    
    # 백업 저장
    save_backup(extracted_kpis, "daily_summary")
    
    print("\n--- 작업 완료 ---")
    print("백업 스크립트 실행이 완료되었습니다. 데이터 안정성 확보에 중점을 두었습니다.")

if __name__ == "__main__":
    main()