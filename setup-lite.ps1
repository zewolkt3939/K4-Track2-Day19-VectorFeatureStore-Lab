param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$env:QDRANT_MODE = 'memory'
$env:EMBEDDING_BACKEND = 'fastembed'
$env:FASTEMBED_CACHE_PATH = Join-Path $PSScriptRoot 'data\model_cache'
$env:HF_HOME = Join-Path $PSScriptRoot 'data\hf_cache'
$env:IPYTHONDIR = Join-Path $PSScriptRoot '.runtime\ipython'
$env:JUPYTER_RUNTIME_DIR = Join-Path $PSScriptRoot '.runtime\jupyter'
New-Item -ItemType Directory -Force -Path $env:IPYTHONDIR, $env:JUPYTER_RUNTIME_DIR | Out-Null

function Invoke-LabPython {
    & $script:LabPython @args
    if ($LASTEXITCODE -ne 0) { throw "Python command failed: $args" }
}

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv' }
}
$script:LabPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not $SkipInstall) {
    Invoke-LabPython -m pip install --no-cache-dir -r requirements.txt
    $is314 = & $script:LabPython -c 'import sys; print(int(sys.version_info >= (3,14)))'
    if ($is314 -eq '1') { Invoke-LabPython -m pip install --no-cache-dir 'dill>=0.4,<1.0' }
}
$env:PATH = (Join-Path $PSScriptRoot '.venv\Scripts') + ';' + $env:PATH
# Keep the kernel registration in the project, rather than changing user settings.
Invoke-LabPython -m ipykernel install --prefix (Join-Path $PSScriptRoot '.venv') --name lab19 --display-name 'Lab 19 (.venv)'
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
Invoke-LabPython scripts/seed_corpus.py
Invoke-LabPython scripts/gen_agent_queries.py
Invoke-LabPython scripts/gen_spend.py
Invoke-LabPython scripts/verify_lite.py
Write-Host 'Setup complete. Execute: .\.venv\Scripts\python.exe scripts/run_notebooks.py'
