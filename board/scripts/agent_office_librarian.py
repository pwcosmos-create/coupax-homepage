"""사서 젬마: 오래되거나 중복된 지식을 아카이브로 옮겨 메인 DB를 최적화합니다."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data"

def archive_old_cards(domain: str, days_old: int = 30) -> int:
    """특정 도메인의 cards.json 파일에서 오래된 카드를 archive.json으로 옮깁니다."""
    domain_dir = DATA_DIR / domain
    if not domain_dir.exists():
        return 0
        
    cards_path = domain_dir / "cards.json"
    archive_path = domain_dir / "archive.json"
    
    if not cards_path.exists():
        return 0
        
    try:
        with open(cards_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0
        
    cards = data.get("cards", [])
    if not cards:
        return 0
        
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    active_cards = []
    archived_cards = []
    
    for c in cards:
        # timestamp 형식: "2026-06-08 11:45"
        ts_str = c.get("ts") or c.get("time") or ""
        try:
            card_date = datetime.strptime(ts_str[:10], "%Y-%m-%d")
            if card_date < cutoff_date:
                archived_cards.append(c)
            else:
                active_cards.append(c)
        except ValueError:
            # 날짜 파싱 실패 시 일단 유지
            active_cards.append(c)
            
    if not archived_cards:
        return 0
        
    # 기존 아카이브 로드
    archive_data = {"cards": []}
    if archive_path.exists():
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                archive_data = json.load(f)
        except Exception:
            pass
            
    archive_data["cards"].extend(archived_cards)
    data["cards"] = active_cards
    
    # 파일 저장
    with open(cards_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)
        
    return len(archived_cards)

def run_librarian() -> dict:
    domains = [
        "chief_dev_learning",
        "homepage_design_learning",
        "workisus_learning",
        "kiwoom_learning"
    ]
    
    total_archived = 0
    for d in domains:
        # 시연을 위해 days_old=30으로 설정 (실제로는 더 긴 기간)
        archived = archive_old_cards(d, days_old=30)
        total_archived += archived
        
    if total_archived > 0:
        import alert_notifier
        alert_notifier.send_telegram_alert(
            "사서 젬마 아카이빙 완료",
            f"총 {total_archived}개의 노후 지식 카드가 archive.json으로 안전하게 격리되었습니다. (DB 최적화 완료)",
            "🧹 청소"
        )
        
    return {"ok": True, "archived": total_archived}

if __name__ == "__main__":
    result = run_librarian()
    print(json.dumps(result, ensure_ascii=False))
