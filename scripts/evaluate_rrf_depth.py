"""Measure candidate depth on independent development queries, then unchanged golden set.

Golden labels are never used to select depth. This is a small development
experiment, not evidence of generalisation to external production data.
"""
from pathlib import Path
import os
import sys
import json
import statistics
import argparse
import hashlib
import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(ROOT / "data/model_cache"))
from app.embeddings import Embedder

docs = [json.loads(line) for line in (ROOT / "data/corpus_vn.jsonl").read_text(encoding="utf-8").splitlines()]
bm = BM25Okapi([(d["title"] + " " + d["text"]).lower().split() for d in docs])
parser = argparse.ArgumentParser()
parser.add_argument("--backend", default="multilingual-small")
parser.add_argument("--tie-break", choices=["keyword", "semantic"], default="keyword")
args = parser.parse_args()
model = Embedder(args.backend)
print("Index", args.backend, flush=True)
fingerprint = hashlib.sha256((ROOT / "data/corpus_vn.jsonl").read_bytes() + (ROOT / "app/embeddings.py").read_bytes()).hexdigest()[:12]
cache = ROOT / ".runtime" / f"quality-vectors-{args.backend}-{fingerprint}.npy"
if cache.exists():
    vectors = np.load(cache)
else:
    vectors = np.asarray(list(model.embed([d["title"] + " " + d["text"] for d in docs])))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    cache.parent.mkdir(exist_ok=True)
    np.save(cache, vectors)
dev = [
    ("cloud", "AWS serverless", "điều chỉnh tài nguyên khi lượng truy cập thay đổi", "AWS serverless tiết kiệm tài nguyên khi ít người truy cập"),
    ("ai_ml", "embedding LLM", "biểu diễn câu thành dãy số để tìm nội dung tương tự", "LLM tìm ngữ cảnh bằng biểu diễn câu thành dãy số"),
    ("security", "OAuth JWT", "ngăn kẻ lạ sử dụng tài khoản người dùng", "OAuth kiểm tra quyền để ngăn người lạ sử dụng tài khoản"),
    ("database", "SQL index", "tăng tốc tìm bản ghi trong kho lưu trữ", "SQL index tăng tốc tìm bản ghi trong bảng lớn"),
    ("networking", "TCP DNS", "định tuyến gói tin và phân giải tên máy", "TCP DNS định tuyến gói tin giữa các máy"),
    ("devops", "CI/CD rollback", "đưa phiên bản mới lên hệ thống rồi quay lại bản cũ khi lỗi", "CI/CD rollback khi phiên bản mới gây lỗi"),
    ("mobile", "Android APK", "ứng dụng điện thoại vẫn dùng được khi không có kết nối", "Android APK hỗ trợ sử dụng khi mất kết nối"),
    ("frontend", "React CSS", "hiển thị trang nhanh hơn trên màn hình trình duyệt", "React CSS làm trang hiển thị nhanh trong trình duyệt"),
    ("backend", "API microservice", "xử lý yêu cầu trùng mà không thực hiện tác vụ hai lần", "API microservice ngăn tác vụ được thực hiện hai lần"),
    ("data_eng", "Kafka ETL", "xử lý dòng sự kiện và thay đổi cấu trúc dữ liệu", "Kafka ETL xử lý dòng sự kiện khi cấu trúc dữ liệu thay đổi"),
]
def rankings(query):
    q = np.asarray(next(model.embed([query])))
    q /= np.linalg.norm(q)
    return np.argsort(-bm.get_scores(query.lower().split()), kind="stable"), np.argsort(-(vectors @ q), kind="stable")
def score(ids, topic):
    return sum(docs[int(i)]["topic"] == topic for i in ids[:10]) / 10
def fused(kw, sem, depth):
    scores = {}
    for ids in (kw[:depth], sem[:depth]):
        for rank, i in enumerate(ids, 1):
            scores[int(i)] = scores.get(int(i), 0) + 1 / (60 + rank)
    if args.tie_break == "semantic":
        semantic_rank = {int(i): r for r, i in enumerate(sem)}
        return sorted(scores, key=lambda i: (-scores[i], semantic_rank[i], docs[i]["doc_id"]))[:10]
    return sorted(scores, key=lambda i: -scores[i])[:10]
depths = [20, 50, 100, 200, 1000]
dev_scores = {d: [] for d in depths}
for topic, *queries in dev:
    for query in queries:
        kw, sem = rankings(query)
        for depth in depths:
            dev_scores[depth].append(score(fused(kw, sem, depth), topic))
averages = {d: statistics.mean(v) for d, v in dev_scores.items()}
selected = max(depths, key=lambda d: (averages[d], -d))
print("Independent development scores:", averages, "selected:", selected, flush=True)
golden = [json.loads(line) for line in (ROOT / "data/golden_set.jsonl").read_text(encoding="utf-8").splitlines()]
rows = []
exploration = {depth: [] for depth in depths}
for item in golden:
    kw, sem = rankings(item["query"])
    rows.append({"type": item["mode_hint"], "keyword": score(kw, item["topic"]), "semantic": score(sem, item["topic"]), "hybrid": score(fused(kw, sem, selected), item["topic"])})
    for depth in depths:
        exploration[depth].append({"type": item["mode_hint"], "keyword": score(kw, item["topic"]), "semantic": score(sem, item["topic"]), "hybrid": score(fused(kw, sem, depth), item["topic"])})
def means(items):
    return {mode: statistics.mean(r[mode] for r in items) for mode in ("keyword", "semantic", "hybrid")}
result = {"model": model.model_name, "rrf_k": 60, "development_queries": dev, "development_count": 30,
          "development_scores": averages, "selected_depth": selected, "selection": "max development mean; ties prefer lower depth; selected before reading golden",
          "golden_mean": means(rows), "golden_slices": {kind: means([r for r in rows if r["type"] == kind]) for kind in ("exact", "paraphrase", "mixed")},
          "limitation": "Golden set has been inspected in previous lab work; this small dev set is not proof of out-of-domain generalisation."}
result["golden_depth_sensitivity_not_holdout"] = {depth: {"mean": means(items), "slices": {kind: means([r for r in items if r["type"] == kind]) for kind in ("exact", "paraphrase", "mixed")}} for depth, items in exploration.items()}
result["tie_break"] = args.tie_break
out = ROOT / f"submission/evidence/rrf-depth-{args.backend}-{args.tie_break}.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
