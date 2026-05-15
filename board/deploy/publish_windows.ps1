#Requires -Version 5.1
<#
  board 폴더를 서버에 올리기 위한 배포 zip 생성.
  - .venv, __pycache__, .git 제외
  - .env, board.db 제외 (서버에서 별도 유지)

  사용:
    cd board\deploy
    .\publish_windows.ps1

  출력: board\coupax-board-deploy.zip
  이후 (예시, 호스트만 바꿔서 실행):
    scp ..\coupax-board-deploy.zip opc@서버공인IP:/home/opc/
    ssh opc@서버공인IP "cd /home/opc/coupax-homepage/board && unzip -o ~/coupax-board-deploy.zip && sudo systemctl restart board"
#>
$ErrorActionPreference = "Stop"
$BoardRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ZipPath = Join-Path $BoardRoot "coupax-board-deploy.zip"
$Staging = Join-Path $env:TEMP ("coupax-board-staging-" + [Guid]::NewGuid().ToString("N"))

try {
    New-Item -ItemType Directory -Path $Staging | Out-Null
    robocopy $BoardRoot $Staging /E /XD .venv __pycache__ .git /XF .env board.db coupax-board-deploy.zip /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE)" }
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipPath -Force
    Write-Host "OK: $ZipPath"
    Write-Host ""
    Write-Host "다음을 서버(Oracle 등)에서 실행하세요(호스트·경로는 환경에 맞게 수정):"
    Write-Host "  scp `"$ZipPath`" opc@YOUR_SERVER:/home/opc/"
    Write-Host "  ssh opc@YOUR_SERVER `"cd /home/opc/coupax-homepage/board && unzip -o ~/coupax-board-deploy.zip && sudo systemctl restart board`""
}
finally {
    if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
}
