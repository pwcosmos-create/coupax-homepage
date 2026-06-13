"""
매일 국내 월배당 ETF 목록·분배금을 갱신합니다.

1) 구글 시트 CSV(또는 kisstock CSV) → 종목 병합
2) (중단) search-etf.com 메타·분배금·YTD — SEARCH_ETF_CALLS_ALLOWED=1 일 때만
3) 총 수익률 내림차순 정렬 + JSON 스키마 검증

환경 변수(선택):
  KR_MONTHLY_DIVIDEND_SHEET_CSV_URL — 구글 시트 export URL
  KR_MONTHLY_DIVIDEND_CSV — 로컬 CSV 경로(기본: kisstock 경로 또는 /tmp)

서버 cron 예:
  15 6 * * * cd /home/ubuntu/coupax-homepage/board && .venv/bin/python scripts/sync_daily_monthly_etfs.py >> logs/sync_monthly_etfs.log 2>&1
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
SCRIPTS = BOARD / "scripts"
DEFAULT_SHEET_EXPORT = (
    "https://docs.google.com/spreadsheets/d/1fg4ZnSV888FjjFP6T4weyeLtogqU-pXHKrKTxxnlymk/"
    "export?format=csv&gid=2078661193"
)
KISSTOCK_CSV = Path("/home/ubuntu/kisstock/data/kr_monthly_dividend_etfs.csv")
LOCAL_CSV = BOARD / "data" / "kr_monthly_dividend_etfs.csv"


def _python() -> str:
    venv = BOARD / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _fetch_csv(dest: Path) -> bool:
    url = (os.getenv("KR_MONTHLY_DIVIDEND_SHEET_CSV_URL") or DEFAULT_SHEET_EXPORT).strip()
    kisstock_fetch = Path("/home/ubuntu/kisstock/fetch_monthly_dividend_sheet_csv.py")
    if kisstock_fetch.is_file():
        env = {**os.environ, "KR_MONTHLY_DIVIDEND_SHEET_CSV_URL": url}
        r = subprocess.run(
            [_python(), str(kisstock_fetch), "--out", str(dest)],
            cwd=kisstock_fetch.parent,
            env=env,
            capture_output=True,
            text=True,
        )
        print(r.stdout, end="")
        if r.stderr:
            print(r.stderr, file=sys.stderr, end="")
        if r.returncode == 0 and dest.is_file():
            return True
        print("[sync] kisstock fetch failed, try direct download", flush=True)

    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "coupax-sync-daily/1.0"})
    body = urllib.request.urlopen(req, timeout=90).read()
    if len(body) < 100:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return True


def _csv_path() -> Path:
    for p in (
        os.getenv("KR_MONTHLY_DIVIDEND_CSV", "").strip(),
        str(KISSTOCK_CSV),
        str(LOCAL_CSV),
    ):
        if p and Path(p).is_file():
            return Path(p)
    return LOCAL_CSV


def main() -> int:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import etf_ops_policy

    etf_ops_policy.exit_if_pipeline_disabled()
    py = _python()
    csv_path = _csv_path()

    if not csv_path.is_file():
        print(f"[sync] fetch CSV -> {csv_path}", flush=True)
        if not _fetch_csv(csv_path):
            print("[sync] CSV fetch failed", file=sys.stderr, flush=True)
            return 1

    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from search_etf_policy import search_etf_calls_allowed, block_message

    steps: list[list[str]] = [
        [py, str(SCRIPTS / "merge_kr_monthly_csv_symbols.py"), "--csv", str(csv_path), "--write"],
    ]
    if search_etf_calls_allowed():
        steps.extend(
            [
                [py, str(SCRIPTS / "discover_overseas_monthly_etfs.py"), "--write"],
                [py, str(SCRIPTS / "fill_etf_meta.py"), "--write"],
                [py, str(SCRIPTS / "fill_domestic_dividends.py"), "--write"],
                [py, str(SCRIPTS / "fill_etf_ytd_returns.py"), "--write"],
            ]
        )
    else:
        print(f"[sync] {block_message()}", flush=True)
    steps.append([py, str(SCRIPTS / "sync_dividend_sheet.py"), "--validate"])
    for cmd in steps:
        print("[sync] run", " ".join(cmd[-3:]), flush=True)
        r = subprocess.run(cmd, cwd=BOARD)
        if r.returncode != 0:
            return r.returncode
    print("[sync] OK", flush=True)
    try:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import agent_office_log

        agent_office_log.append_message(
            from_id="etf_sync",
            to_id="structurer",
            kind="conclusion",
            text="일일 월배당 ETF sync 완료(CSV 병합·검증). search-etf 호출은 중단 상태.",
        )
    except Exception as e:
        print(f"[sync] agent office log skip: {e}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
