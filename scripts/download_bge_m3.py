"""Resume public BGE-M3 weights in bounded HTTP ranges and verify HF SHA256."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import hashlib
import os
import time

import requests
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
cache = ROOT / "data/hf_cache/hub/models--BAAI--bge-m3"
parts = ROOT / "data/hf_cache/bge_download_parts"
parts.mkdir(parents=True, exist_ok=True)
info = HfApi().model_info("BAAI/bge-m3", files_metadata=True)
file = next(s for s in info.siblings if s.rfilename == "pytorch_model.bin")
size, expected_hash = file.lfs.size, file.lfs.sha256
url = f"https://huggingface.co/BAAI/bge-m3/resolve/{info.sha}/pytorch_model.bin"
chunk = 16 * 1024 * 1024
count = (size + chunk - 1) // chunk
print(f"revision={info.sha} bytes={size} chunks={count}", flush=True)

def download(i):
    start, end = i * chunk, min((i + 1) * chunk, size) - 1
    path = parts / f"{i:04d}.part"
    if path.exists() and path.stat().st_size == end - start + 1:
        return i
    for attempt in range(4):
        try:
            with requests.get(url, headers={"Range": f"bytes={start}-{end}"}, stream=True, timeout=(20, 60)) as r:
                r.raise_for_status()
                assert r.status_code == 206, r.status_code
                assert r.headers["Content-Range"] == f"bytes {start}-{end}/{size}", r.headers["Content-Range"]
                with path.open("wb") as f:
                    for block in r.iter_content(1024 * 1024):
                        f.write(block)
            assert path.stat().st_size == end - start + 1
            return i
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

with ThreadPoolExecutor(max_workers=4) as pool:
    done = 0
    for future in as_completed([pool.submit(download, i) for i in range(count)]):
        future.result()
        done += 1
        if done % 5 == 0 or done == count:
            print(f"downloaded {done}/{count} chunks", flush=True)

blob = cache / "blobs" / expected_hash
blob.parent.mkdir(parents=True, exist_ok=True)
temp = blob.with_suffix(".verified-download")
digest = hashlib.sha256()
with temp.open("wb") as f:
    for i in range(count):
        with (parts / f"{i:04d}.part").open("rb") as part:
            while block := part.read(1024 * 1024):
                f.write(block)
                digest.update(block)
assert digest.hexdigest() == expected_hash, "Weight SHA256 mismatch"
assert temp.stat().st_size == size
temp.replace(blob)
target = cache / "snapshots" / info.sha / "pytorch_model.bin"
target.parent.mkdir(parents=True, exist_ok=True)
if not target.exists():
    os.link(blob, target)
print(f"PASS SHA256={expected_hash}; weights={target}", flush=True)
