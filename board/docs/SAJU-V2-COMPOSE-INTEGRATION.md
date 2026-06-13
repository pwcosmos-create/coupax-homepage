# saju-v2 ↔ board `/api/saju/reading/compose` 연동

## board가 해주는 것 (api_version 2)

| 필드 | 용도 |
|------|------|
| `text` / `text_chat` | 채팅 버블 (짧음, 상한 ~2200자) |
| `text_full` | 심층·10절 화면 |
| `display.body` | `text_chat`과 동일 |
| `sections[].excerpt` | 절별 짧은 본문 (아코디언 UI) |
| `intent` | 추론된 `reading_kind`, `topic` |

`user_query` / `question` / `surface: chat` 만내도 서버가 `reading_kind` 추론.

## saju-v2에서 반드시 할 일 (미해결 → 앱 작업)

1. **질문당 compose 1회** — 카드 제목마다 버블 쌓지 않기.
2. 채팅 UI = **`display.body` 또는 `text_chat`** 만 표시 (일운 키워드만 X).
3. 심층 메뉴 = **`text_full`**.
4. 요청 예시:

```json
{
  "surface": "chat",
  "user_query": "나의 운세",
  "context": {
    "tags": ["용신", "토"],
    "summary": "병화 일주 …"
  }
}
```

5. `llm_required: true` 이면 Gemini 보조 호출 (키워드만 노출 금지).

## 서버 데이터 (미해결 → 운영)

- 기존 카드 6절 본문: `python scripts/refresh_variable_cards_slim.py` (서버 `nohup`)
- 이후 `dedupe_saju_cards.py` 주기 실행

## 환경 변수

- `SAJU_READING_API_ENABLED=1`
- `SAJU_READING_CHAT_TOTAL_CHARS=2200` (채팅 전체 상한)
