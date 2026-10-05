"""Real BGE-M3 inference and isolated Qdrant-server round trip; no production reindex."""
from pathlib import Path
import json
import os
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HOME", str(ROOT / "data/hf_cache"))
os.environ.setdefault("TORCH_NUM_THREADS", "2")
from app.embeddings import Embedder
import numpy as np
from qdrant_client import QdrantClient, models

out = ROOT / "submission/evidence/bge-m3"
out.mkdir(parents=True, exist_ok=True)
texts = [
    "Điện toán đám mây: tự động mở rộng hạ tầng theo lưu lượng người dùng.",
    "Bảo mật: xác thực đa yếu tố để ngăn chiếm đoạt tài khoản.",
    "Cơ sở dữ liệu: chỉ mục B-tree giúp tăng tốc truy vấn SQL.",
]
embedder = Embedder("bge-m3")
print("Loading real model:", embedder.model_name, flush=True)
start = time.perf_counter()
vectors = np.asarray(list(embedder.embed(texts)))
load_seconds = time.perf_counter() - start
assert vectors.shape == (3, 1024), vectors.shape
assert np.isfinite(vectors).all()
assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
print("PASS: shape, finite values, unit norm", vectors.shape, flush=True)
client = QdrantClient(url="http://127.0.0.1:6333", timeout=10)
collection = "lab19_bge_verify_" + uuid.uuid4().hex[:10]
latencies = []
try:
    client.create_collection(collection, vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE))
    client.upsert(collection, points=[models.PointStruct(id=i, vector=v.tolist(), payload={"text": texts[i]}) for i, v in enumerate(vectors)], wait=True)
    assert client.count(collection, exact=True).count == 3
    matches = []
    for query, expected in [("co giãn tài nguyên khi lượng truy cập tăng", 0), ("chống đăng nhập trái phép bằng nhiều bước xác minh", 1)]:
        t = time.perf_counter()
        vector = next(embedder.embed([query]))
        hits = client.query_points(collection, query=vector.tolist(), limit=3).points
        latencies.append((time.perf_counter() - t) * 1000)
        assert hits[0].id == expected, [(h.id, h.score) for h in hits]
        matches.append({"query": query, "expected_id": expected, "top_id": hits[0].id, "score": hits[0].score})
    result = {"status": "PASS", "model": embedder.model_name, "dimension": 1024,
              "provider": "sentence-transformers", "load_and_first_batch_seconds": load_seconds,
              "query_round_trip_ms": latencies, "matches": matches,
              "scope": "3 documents / 2 queries: real inference + Qdrant server; not a latency benchmark"}
    (out / "smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
finally:
    client.delete_collection(collection)
    client.close()
