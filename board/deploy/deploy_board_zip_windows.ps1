#Requires -Version 5.1
<#
  publish_windows.ps1 로 만든 zip을 서버로 올리고 압축 해제·board 재시작.

  사용 예 (Oracle / opc):
    cd board\deploy
    .\publish_windows.ps1
    .\deploy_board_zip_windows.ps1 -Server "YOUR_PUBLIC_IP" -User opc

  사용 예 (ubuntu 홈 경로):
    .\deploy_board_zip_windows.ps1 -Server "YOUR_PUBLIC_IP" -User ubuntu `
      -RemoteZipPath "/home/ubuntu/coupax-board-deploy.zip" `
      -BoardDirOnServer "/home/ubuntu/coupax-homepage/board"

  SSH 키는 에이전트(ssh-add) 또는 기본 ~/.ssh/id_* 가 서버에 등록돼 있어야 합니다.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Server,
    [string]$User = "opc",
    [string]$RemoteZipPath = "",
    [string]$BoardDirOnServer = ""
)

$ErrorActionPreference = "Stop"
$BoardRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ZipLocal = Join-Path $BoardRoot "coupax-board-deploy.zip"
if (-not (Test-Path $ZipLocal)) {
    throw "Zip not found: $ZipLocal — run .\publish_windows.ps1 first."
}

if (-not $RemoteZipPath) {
    $RemoteZipPath = if ($User -eq "opc") { "/home/opc/coupax-board-deploy.zip" } else { "/home/$User/coupax-board-deploy.zip" }
}
if (-not $BoardDirOnServer) {
    $BoardDirOnServer = if ($User -eq "opc") { "/home/opc/coupax-homepage/board" } else { "/home/$User/coupax-homepage/board" }
}

$remote = "$User@$Server"
Write-Host "SCP: $ZipLocal -> ${remote}:$RemoteZipPath"
& scp -o StrictHostKeyChecking=accept-new $ZipLocal "${remote}:$RemoteZipPath"
if ($LASTEXITCODE -ne 0) { throw "scp failed ($LASTEXITCODE)" }

$unzip = "cd $BoardDirOnServer && unzip -o `"$RemoteZipPath`" && sudo systemctl restart board && sudo systemctl is-active board"
Write-Host "SSH: $unzip"
ssh -o StrictHostKeyChecking=accept-new $remote $unzip
if ($LASTEXITCODE -ne 0) { throw "ssh failed ($LASTEXITCODE)" }
Write-Host "OK: board restarted on $remote"
