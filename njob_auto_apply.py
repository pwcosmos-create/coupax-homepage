import asyncio
import glob
import os
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright


def seId_to_category_code(seId):
    """
    seId '0706020000' -> 카테고리 코드 '07_06_02_00_00'
    njobapp categoryVal 형식 (언더스코어 구분 2자리씩)
    """
    s = str(seId).strip().zfill(10)
    pairs = [s[i:i+2] for i in range(0, 10, 2)]
    return '_'.join(pairs)


async def apply_one(page, item_no, seId):
    """상품 1개에 카테고리 적용 후 저장. (success, message) 반환"""
    cat_code = seId_to_category_code(seId)

    # ── 편집 페이지 로드 ───────────────────────────────────────────────────
    try:
        await page.goto(
            f"https://www.njobapp.com/mybox/getEditView?itemNo={item_no}",
            wait_until="networkidle",
            timeout=25000,
        )
    except Exception as e:
        return False, f"페이지 로드 실패: {e}"

    # ── categoryVal 현재값 확인 ────────────────────────────────────────────
    current_val = await page.evaluate(
        "document.getElementById('categoryVal')?.value || ''"
    )

    if current_val == cat_code:
        return True, f"이미 동일 카테고리 ({cat_code}) - 스킵"

    # ── categoryVal 직접 설정 ─────────────────────────────────────────────
    set_ok = await page.evaluate(
        f"""
        (() => {{
            const el = document.getElementById('categoryVal');
            if (!el) return false;
            el.value = '{cat_code}';
            return true;
        }})()
        """
    )

    if not set_ok:
        return False, "categoryVal 요소 없음"

    # ── sort 드롭다운도 일치시키기 (UI 정합성) ────────────────────────────
    # sort1: '07_00_00_00_00', sort2: '07_06_00_00_00', ...
    pairs = [cat_code.split('_')[i] for i in range(5)]
    sort_codes = [
        f"{pairs[0]}_00_00_00_00",
        f"{pairs[0]}_{pairs[1]}_00_00_00",
        f"{pairs[0]}_{pairs[1]}_{pairs[2]}_00_00",
        f"{pairs[0]}_{pairs[1]}_{pairs[2]}_{pairs[3]}_00",
        '_'.join(pairs),
    ]

    for level in range(1, 6):
        sel_name = f"sort{level}"
        val = sort_codes[level - 1]
        try:
            exists = await page.evaluate(
                f"!!document.querySelector('select[name=\"{sel_name}\"]')"
            )
            if exists:
                await page.select_option(f'select[name="{sel_name}"]', val)
                await page.wait_for_timeout(600)
        except Exception:
            pass  # 없는 레벨 무시

    # ── saveChanges() 호출 후 네비게이션 대기 ────────────────────────────
    try:
        async with page.expect_navigation(timeout=10000):
            await page.evaluate("saveChanges()")
    except Exception:
        # 네비게이션 없이 팝업으로 처리될 수도 있음 → 그냥 대기
        await page.wait_for_timeout(2000)

    return True, f"{current_val} -> {cat_code}"


async def run_auto_apply():
    # ── 최신 결과 파일 탐색 ────────────────────────────────────────────────
    files = sorted(glob.glob("njob_category_result_*.xlsx"), reverse=True)
    if not files:
        print("[오류] njob_category_result_*.xlsx 파일 없음. njob_fetch_and_map.py 먼저 실행하세요.")
        return
    result_file = files[0]
    print(f"[파일] {result_file} 로드 중...")

    df = pd.read_excel(result_file, dtype=str).fillna('')
    targets = df[df['seId'].str.strip().str.len() > 0].copy()
    print(f"[대상] 전체 {len(df)}행 중 seId 있는 {len(targets)}행 처리")

    if len(targets) == 0:
        print("[완료] 처리할 상품 없음")
        return

    # ── 세션 확인 ─────────────────────────────────────────────────────────
    if not os.path.exists("njob_session.json"):
        print("[오류] njob_session.json 없음. njob_login.py 먼저 실행하세요.")
        return

    results = []
    ok_count = 0
    fail_count = 0
    skip_count = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state="njob_session.json")

        for i, row in enumerate(targets.itertuples(), 1):
            item_no = str(row.상품번호).strip()
            seId = str(row.seId).strip()
            name = str(row.상품명).strip()[:28]
            cat_path = str(row.카테고리경로).strip()

            if not item_no or not seId:
                continue

            print(f"  [{i:>2}/{len(targets)}] {item_no} | {name:<28} | {seId}", end=" -> ")

            # 각 상품마다 새 페이지 사용 (saveChanges 후 네비게이션 충돌 방지)
            page = await context.new_page()
            try:
                success, msg = await apply_one(page, item_no, seId)
            finally:
                await page.close()

            if success:
                if "스킵" in msg:
                    skip_count += 1
                    print(f"[SKIP] {msg}")
                else:
                    ok_count += 1
                    print(f"[OK]  {msg}")
            else:
                fail_count += 1
                print(f"[ERR] {msg}")

            results.append({
                "상품번호": item_no,
                "상품명": name,
                "카테고리경로": cat_path,
                "seId": seId,
                "categoryCode": seId_to_category_code(seId),
                "결과": "성공" if success else "실패",
                "메시지": msg,
            })

            await asyncio.sleep(0.5)

        await browser.close()

    # ── 결과 저장 ─────────────────────────────────────────────────────────
    out_df = pd.DataFrame(results)
    out_file = f"njob_apply_result_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    out_df.to_excel(out_file, index=False)

    print(f"\n[완료] 성공 {ok_count}건 / 스킵 {skip_count}건 / 실패 {fail_count}건")
    print(f"[저장] {out_file}")


if __name__ == "__main__":
    asyncio.run(run_auto_apply())
