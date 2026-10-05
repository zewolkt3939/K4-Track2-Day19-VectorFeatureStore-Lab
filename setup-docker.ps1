param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:DOCKER_CONFIG = Join-Path $PSScriptRoot '.runtime/docker'
New-Item -ItemType Directory -Force $env:DOCKER_CONFIG | Out-Null
function CheckExit { if ($LASTEXITCODE -ne 0) { throw "Command failed: $LASTEXITCODE" } }
docker compose up -d --wait
CheckExit
if (-not (Test-Path '.venv/Scripts/python.exe')) { & ./setup-lite.ps1; CheckExit }
if (-not $SkipInstall) {
    & ./.venv/Scripts/python.exe -m pip install --no-cache-dir -r requirements.txt 'redis>=5,<6' 'psycopg[binary,pool]>=3.2,<4' 'sqlalchemy>=2,<3'
    CheckExit
}
$env:PYTHONIOENCODING = 'utf-8'
& ./.venv/Scripts/python.exe scripts/configure_docker.py
CheckExit
& ./.venv/Scripts/python.exe scripts/run_notebooks.py --profile docker --only 03 04
CheckExit
& ./.venv/Scripts/python.exe scripts/verify_docker.py
CheckExit
Write-Host 'Docker evidence: submission/evidence/docker. CPU profile: fastembed (384d).'
