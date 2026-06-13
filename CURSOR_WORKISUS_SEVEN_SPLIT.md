# 원키스US — 세븐 스플릿(Seven Split) 매매법 (정본)

> stock.coupax.co.kr/workisus · wonkisus/shared/매직스플릿 · `auto_bot.py` US 경로  
> 학습 pack: `board/data/workisus_learning/workisus_knowledge_pack.json`

## 3대 철학

1. **무손실** — 손실 구간 시장가 매도 없음. 분할·시간으로 평단 회복.
2. **슬롯 독립** — 증권 잔고 1계좌, 봇 DB에서 차수별 매수가·익절% 분리.
3. **ATR 연동(무손실 맞춤)** — sell 1.5~4%(ATR×1.2), buy_gap×1.15, 1차 999%, fee_buffer 0.12%p.

## 프로세스

| 단계 | 내용 |
|------|------|
| 1차 | HTS 수동 매수 → 슬롯1 register · sell_pcts 999% (앵커, 안 팖) |
| 2차 | 1차 후 **15초** 무조건 2차 매수 → 익절 시 2차만 매도 → max_slot=1이면 **15초 후 2차 재진입** (횡보 복리) |
| 3~N차 | 하락 시 buy_gaps(-5% 등)마다 추가 매수 · ATR·목표금액÷현재가로 수량 |
| 익절 | 슬롯별 sell_pcts 독립 매도 |
| 방어 | `get_account_avg_profit` 합산 ≤0% → 개별 익절 **보류** |

## 모드 스위치

- **세븐 스플릿 ON:** `no_slot_trading=false`, `enabled_us=true`
- **대기/리밸런스:** `no_slot_trading=true` → 격자 OFF, `us_rebalance` 또는 일괄 익절

## Agent Office

- division: `workisus-chasu`
- 카탈로그 시드: `wonkisus_seven_split_*`
- 젬마: 주문(1차)·자동(2차/N차)·규칙(buy_gaps)·리스크(합산방어)·오류젬마
