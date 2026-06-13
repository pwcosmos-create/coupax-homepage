#Requires -Version 5.1
# %USERPROFILE%\.ssh 에서 배포용으로 자주 쓰는 키를 local-ssh 로 복사합니다.
$ErrorActionPreference = "Stop"
$src = Join-Path $env:USERPROFILE ".ssh"
$dest = Join-Path $PSScriptRoot "local-ssh"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$files = @(
    "shinserver.key",
    "oci_a1_flex.pem",
    "oci_instance_key.pem",
    "oci_instance_key.pub",
    "oci_instance_key_public.pem",
    "styleshimy-new-key",
    "styleshimy-new-key.pub"
)
foreach ($f in $files) {
    $p = Join-Path $src $f
    if (Test-Path $p) {
        Copy-Item -Force $p (Join-Path $dest $f)
        Write-Host "OK $f"
    }
}
$cfg = Join-Path $src "config"
if (Test-Path $cfg) {
    Copy-Item -Force $cfg (Join-Path $dest "ssh_config_copy")
    Write-Host "OK ssh_config_copy (from config)"
}
Write-Host "Done -> $dest (this folder is gitignored)"
