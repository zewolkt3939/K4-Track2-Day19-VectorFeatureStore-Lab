FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
COPY source.tar /tmp/source.tar
RUN tar -xf /tmp/source.tar -C /lab && rm /tmp/source.tar
ENV QDRANT_MODE=memory EMBEDDING_BACKEND=fastembed FASTEMBED_CACHE_PATH=/lab/data/model_cache HF_HOME=/lab/data/hf_cache HF_HUB_DISABLE_XET=1 PYTHONUNBUFFERED=1
CMD ["bash", "-c", "set -euo pipefail; bash setup-lite.sh 2>&1 | tee /evidence/setup-lite.txt; make benchmark 2>&1 | tee /evidence/benchmark.txt; make test 2>&1 | tee /evidence/test.txt; make verify-lite 2>&1 | tee /evidence/verify-lite.txt; .venv/bin/python -m pip freeze > /evidence/requirements-linux-py312.lock.txt; echo PASS > /evidence/status.txt"]
