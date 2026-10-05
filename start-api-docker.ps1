$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:QDRANT_MODE = 'server'
$env:QDRANT_URL = 'http://127.0.0.1:6333'
$env:EMBEDDING_BACKEND = 'fastembed'
$env:FASTEMBED_CACHE_PATH = Join-Path $PSScriptRoot 'data/model_cache'
$env:HF_HOME = Join-Path $PSScriptRoot 'data/hf_cache'
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
