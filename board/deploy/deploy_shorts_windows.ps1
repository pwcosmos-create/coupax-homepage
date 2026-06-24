#Requires -Version 5.1
<#
  숏폼공장 board 배포 (zip + scp + restart)

  cd board\deploy
  .\deploy_shorts_windows.ps1 -Server 168.107.31.153 -User opc
  .\deploy_shorts_windows.ps1 -Server 168.107.31.153 -User opc -SshKey ".\local-ssh\oci_instance_key.pem"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Server,
    [string]$User = "opc",
    [string]$SshKey = "",
    [string]$BoardDirOnServer = ""
)

$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
if (-not $BoardDirOnServer) {
    $BoardDirOnServer = if ($User -eq "opc") { "/home/opc/coupax-homepage/board" } else { "/home/$User/coupax-homepage/board" }
}

$sshArgs = @("-o", "StrictHostKeyChecking=accept-new")
if ($SshKey -and (Test-Path $SshKey)) {
    $keyPath = (Resolve-Path $SshKey).Path
    $sshArgs += @("-i", $keyPath)
}

Write-Host "=== 1) publish zip ==="
& (Join-Path $DeployDir "publish_windows.ps1")

Write-Host "=== 2) scp + unzip + restart board ==="
$BoardRoot = (Resolve-Path (Join-Path $DeployDir "..")).Path
$ZipLocal = Join-Path $BoardRoot "coupax-board-deploy.zip"
$RemoteZip = if ($User -eq "opc") { "/home/opc/coupax-board-deploy.zip" } else { "/home/$User/coupax-board-deploy.zip" }
$remote = "$User@$Server"

scp @sshArgs $ZipLocal "${remote}:$RemoteZip"
if ($LASTEXITCODE -ne 0) { throw "scp failed ($LASTEXITCODE)" }

$unzip = "cd $BoardDirOnServer && unzip -o `"$RemoteZip`" && sudo systemctl restart board && sudo systemctl is-active board"
ssh @sshArgs $remote $unzip
if ($LASTEXITCODE -ne 0) { Write-Warning "ssh exit $LASTEXITCODE" }

Write-Host ""
Write-Host "OK: https://coupax.co.kr/shorts"
