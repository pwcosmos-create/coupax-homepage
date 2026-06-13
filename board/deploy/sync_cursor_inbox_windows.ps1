#Requires -Version 5.1
<#
  서버 사무실 인박스 → 로컬 CURSOR_OFFICE_INBOX.md 동기화

  cd board\deploy
  .\sync_cursor_inbox_windows.ps1
#>
$ErrorActionPreference = "Stop"
$Board = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Py = Join-Path $Board "scripts\sync_cursor_office_inbox.py"
if (-not (Test-Path $Py)) { throw "not found: $Py" }
python $Py pull
if ($LASTEXITCODE -ne 0) { throw "pull failed" }
Write-Host ""
Write-Host "Cursor에서 @CURSOR_OFFICE_INBOX.md 를 열거나 '사무실 지시 확인해' 라고 하세요."
