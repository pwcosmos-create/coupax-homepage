#Requires -Version 5.1
<#
  댓글 봇 스크립트·cron 설치 셸만 빠르게 업로드 (전체 zip 없이).

  예:
    cd board\deploy
    .\deploy_comment_bot_only_windows.ps1 -Server "168.107.31.153" -User opc
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Server,
    [string]$User = "opc",
    [string]$BoardDirOnServer = ""
)

$ErrorActionPreference = "Stop"
$BoardRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $BoardDirOnServer) {
    $BoardDirOnServer = if ($User -eq "opc") { "/home/opc/coupax-homepage/board" } else { "/home/$User/coupax-homepage/board" }
}
$remote = "$User@$Server"
$py = Join-Path $BoardRoot "scripts\comment_reply_bot.py"
$sh = Join-Path $BoardRoot "deploy\install_comment_bot_cron.sh"
if (-not (Test-Path $py)) { throw "Missing $py" }
if (-not (Test-Path $sh)) { throw "Missing $sh" }

Write-Host "SCP -> ${remote}:$BoardDirOnServer/scripts/ and .../deploy/"
scp -o StrictHostKeyChecking=accept-new $py "${remote}:${BoardDirOnServer}/scripts/comment_reply_bot.py"
scp -o StrictHostKeyChecking=accept-new $sh "${remote}:${BoardDirOnServer}/deploy/install_comment_bot_cron.sh"
if ($LASTEXITCODE -ne 0) { throw "scp failed ($LASTEXITCODE)" }
Write-Host "OK. On server: chmod +x $BoardDirOnServer/deploy/install_comment_bot_cron.sh (optional), edit .env.comment_bot, then bash deploy/install_comment_bot_cron.sh"
