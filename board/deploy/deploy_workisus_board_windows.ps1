#Requires -Version 5.1
<#
  원키스US 젬마·Wiki 정본 board 배포 (zip + 서버 후처리).

  .\deploy_workisus_board_windows.ps1 -Server 168.107.31.153 -User opc
  .\deploy_workisus_board_windows.ps1 -Server 168.107.31.153 -User opc -SshKey ".\local-ssh\oci_instance_key.pem"
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
    $env:SCP_SSH_KEY = $keyPath
}

Write-Host "=== 1) publish zip ==="
& (Join-Path $DeployDir "publish_windows.ps1")

Write-Host "=== 2) scp + unzip + restart ==="
if ($SshKey -and (Test-Path $SshKey)) {
    $BoardRoot = (Resolve-Path (Join-Path $DeployDir "..")).Path
    $ZipLocal = Join-Path $BoardRoot "coupax-board-deploy.zip"
    $RemoteZip = if ($User -eq "opc") { "/home/opc/coupax-board-deploy.zip" } else { "/home/$User/coupax-board-deploy.zip" }
    $remote = "$User@$Server"
    scp @sshArgs $ZipLocal "${remote}:$RemoteZip"
    if ($LASTEXITCODE -ne 0) { throw "scp failed" }
    $unzip = "cd $BoardDirOnServer && unzip -o `"$RemoteZip`"; sudo systemctl restart board; sudo systemctl is-active board"
    ssh @sshArgs $remote $unzip
    if ($LASTEXITCODE -ne 0) { Write-Warning "ssh exit $LASTEXITCODE (unzip warning은 무시 가능)" }
} else {
    & (Join-Path $DeployDir "deploy_board_zip_windows.ps1") -Server $Server -User $User -BoardDirOnServer $BoardDirOnServer
}

$wikiPath = "$BoardDirOnServer/data/workisus_canonical/wonkisus-grid-trading-rules.md"
$remote = "$User@$Server"
$post = @"
set -e
cd $BoardDirOnServer
touch .env
for kv in WORKISUS_CARD_PRODUCTION=0 WONKISUS_WIKI_RULES_PATH=$wikiPath; do
  key=`$(echo `$kv | cut -d= -f1)
  if grep -q "^`${key}=" .env 2>/dev/null; then
    sed -i "s|^`${key}=.*|`$kv|" .env
  else
    echo "`$kv" >> .env
  fi
done
PYTHONPATH=scripts .venv/bin/python scripts/merge_workisus_agents_registry.py
PYTHONPATH=scripts .venv/bin/python scripts/purge_workisus_learning_cards.py || true
PYTHONPATH=scripts AGENT_OFFICE_WORKISUS_ONLY=1 .venv/bin/python scripts/activate_workisus_agents.py --interval 0
PYTHONPATH=scripts .venv/bin/python -c "import workisus_wiki_rules as w, json; print(json.dumps(w.wiki_status(), ensure_ascii=False))"
"@

Write-Host "=== 3) server post-install ==="
ssh @sshArgs $remote $post
if ($LASTEXITCODE -ne 0) { throw "ssh post-install failed ($LASTEXITCODE)" }
Write-Host "OK: https://coupax.co.kr/agents/office?unit=workisus-chasu"
