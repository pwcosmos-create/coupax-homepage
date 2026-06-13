#Requires -Version 5.1
<#
  로컬 cards.json의 **신규 카드만** 서버에 병합합니다.
  서버에 있는 위원회 검증(council_*) 필드는 절대 초기화하지 않습니다.

  사용:
    cd board\deploy
    .\merge_saju_cards_to_server.ps1

  주의: cards.json 전체 scp 덮어쓰기 금지 — 이 스크립트만 사용.
#>
$ErrorActionPreference = "Stop"
$BoardRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Key = Join-Path $PSScriptRoot "local-ssh\shinserver.key"
$sshTarget = "ubuntu@168.107.31.153"
$Remote = "/home/ubuntu/coupax-homepage/board"
$LocalCards = Join-Path $BoardRoot "data\saju_learning\cards.json"
$RemoteCards = "$Remote/data/saju_learning/cards.json"
$TmpRemote = "/tmp/cards_merge_incoming.json"

if (-not (Test-Path $LocalCards)) {
    throw "로컬 cards.json 없음: $LocalCards"
}
if (-not (Test-Path $Key)) {
    throw "SSH 키 없음: $Key"
}

Write-Host "1) 로컬 cards.json -> 서버 임시 업로드"
scp -i $Key -o StrictHostKeyChecking=no $LocalCards "${sshTarget}:${TmpRemote}"

Write-Host "2) 서버에서 import-merge (검증 유지, 신규만 추가)"
ssh -i $Key -o StrictHostKeyChecking=no $sshTarget @"
cd $Remote && .venv/bin/python scripts/agent_office_saju_learn.py import-merge $TmpRemote --add-new-only && .venv/bin/python scripts/agent_office_saju_learn.py export && .venv/bin/python scripts/sync_saju_wiki_council.py && .venv/bin/python scripts/agent_office_saju_card_council.py status
"@

Write-Host "OK: 병합 완료 (위원회 PASS 유지)"
