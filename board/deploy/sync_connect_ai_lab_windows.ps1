# Connect AI Lab ↔ Coupax 동기화 (Windows)

$ErrorActionPreference = "Stop"
$Board = Join-Path $PSScriptRoot "..\"
$Lab = if ($env:CONNECT_AI_LAB_PATH) { $env:CONNECT_AI_LAB_PATH } else { Join-Path $env:USERPROFILE "Desktop\connect ai lab" }

if (-not (Test-Path -LiteralPath $Lab)) {
    Write-Host "Connect AI Lab folder not found: $Lab"
    Write-Host "Set CONNECT_AI_LAB_PATH and retry."
    exit 1
}

$env:CONNECT_AI_LAB_PATH = $Lab
$env:PYTHONPATH = "scripts"
Set-Location $Board

Write-Host "Lab: $Lab"
Write-Host "Running sync_connect_ai_lab.py full ..."
python scripts/sync_connect_ai_lab.py --skip-swiki full
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. State: board\data\connect_ai_lab_sync_state.json"
