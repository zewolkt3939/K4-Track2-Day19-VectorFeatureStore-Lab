# Triển khai và đối chiếu rubric

Ba container Qdrant, Redis, PostgreSQL đã chạy trên Docker Desktop/WSL2.
Các cổng chỉ bind 127.0.0.1; volume lưu dữ liệu qua lần khởi động lại.
API chạy trong Python venv ở host theo kiến trúc gốc của lab.

## Chạy lại trên Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./setup-docker.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File ./start-api-docker.ps1
```

API: http://127.0.0.1:8000/docs. Qdrant: http://127.0.0.1:6333/dashboard.
Profile API Docker CPU dùng BGE-small 384 chiều, ONNX 2 threads.
BGE-M3 đã kiểm chứng riêng bằng Sentence Transformers/PyTorch CPU,
vector1024d và truy xuất thật qua Qdrant server; không trộn số đo hai model.
Feast Docker dùng repository riêng `app/feast_repo_docker`, PostgreSQL
schema `lab19` và Redis project `lab19_docker`, giữ riêng dữ liệu Lite.
`configure_docker.py` sinh definitions PostgreSQLSource và cấu hình thật;
NB4 nạp bảng PostgreSQL trước apply/materialization.

## Bằng chứng theo yêu cầu

### NB2 đầy đủ với BGE-M3 trên Qdrant server

Đã chạy xong trong494.27s, đủ6/6 code cells, index1000 tài liệu vào
`lab19_nb2_bge-m3` (1024d). [Notebook](evidence/docker/bge-m3/02_hybrid_search_rrf.ipynb),
[output](evidence/docker/bge-m3/02_hybrid_search_rrf.txt),
[trạng thái](evidence/docker/bge-m3/execution.json).

| Query | n | BM25 | BGE-M3 semantic | Hybrid RRF60 |
|---|---:|---:|---:|---:|
| Tất cả | 50 | 77.8% | **95.2%** | 89.0% |
| Exact | 15 | 96.7% | 98.0% | **100.0%** |
| Paraphrase | 15 | 33.3% | **86.7%** | 66.7% |
| Mixed | 20 | 97.0% | **99.5%** | 97.5% |

`PASS` nghĩa notebook thực thi hoàn chỉnh. Output vẫn có `WARN` vì hybrid
không thắng semantic trong cấu hình BGE-M3. RRF kết hợp thêm BM25 yếu trên
paraphrase nên có thể làm chất lượng thấp hơn vector mạnh; đây là diễn giải
phù hợp số đo, không phải chứng minh nguyên nhân trên mọi corpus.
Không sửa golden set hay công thức RRF để đạt điểm. API P99 dưới50ms bên
dưới thuộc BGE-small; không áp dụng số đo đó cho BGE-M3.

### Kiểm chứng bổ sung BGE-M3 và runtime

[Smoke BGE-M3](evidence/bge-m3/smoke.json) đạt: 3 tài liệu, 2 truy vấn
diễn đạt lại tiếng Việt, cả hai top1 đúng, vector hữu hạn/unit norm/1024d.
Cold load + batch đầu24.03s; hai lượt embed + Qdrant lần lượt239.43 và
198.25ms. Đây là smoke test ít mẫu, không phải P99 hay benchmark tải.
Trọng số2,271,145,830 bytes, revision `5617a9f61b028005a4858fdac845db406aefb181`,
SHA256 `b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38`
đã khớp metadata chính thức. [Log tải/hash](bge-weights-download.log).

Chạy lại kiểm chứng BGE-M3:

```powershell
.\.venv\Scripts\python.exe -m pip install 'sentence-transformers>=3.3,<4'
.\.venv\Scripts\python.exe scripts/download_bge_m3.py
.\.venv\Scripts\python.exe scripts/verify_bge_m3.py
.\.venv\Scripts\python.exe scripts/run_notebooks.py --profile docker --only 02 --backend bge-m3 --timeout 3600
```

`requirements-bge-win-py312.lock.txt` ghi dependency thực tế sau cài BGE-M3.
[48 tests sau cài model](evidence/pytest-post-bge.txt) vẫn đạt; `pip check`
không phát hiện xung đột. Collection NB2 của từng backend được tách riêng,
API mặc định vẫn dùng `lab19_corpus` với BGE-small.

Docker được chạy lại và đạt [smoke](evidence/docker/smoke-recheck.txt)
và [healthcheck](evidence/docker/compose-health-recheck.json).
[Trạng thái runtime](evidence/runtime-support.json): Podman CLI chưa cài,
chưa chạy Podman; Apple container không chạy trên Windows, cần
[Mac Apple silicon và macOS26](https://github.com/apple/container).
Đây là các runtime thay thế, không phải điều kiện để xác nhận stack Docker.

| Yêu cầu | Kết quả / bằng chứng |
|---|---|
| NB1 count1000, top5, paraphrase cloud | [Output NB1](evidence/01_embeddings_index.txt) |
| NB2 RRF 1-based, hybrid thắng trung bình | Lite .786 > .778/.732; đa ngữ .806 > .778/.758 |
| NB2 slices | Lite mixed hybrid1.00; đa ngữ paraphrase vector.48 > BM25.333; xem hai thí nghiệm bên dưới |
| NB3 API và percentiles | [Docker NB3](evidence/docker/03_search_api_benchmark.txt), [Lite NB3](evidence/03_search_api_benchmark.txt) |
| NB4 3 views, incremental, online, PIT | [Docker NB4](evidence/docker/04_feast_feature_store.txt): Redis P99 1.75ms, PIT u001170/security vs online187/cloud |
| NB5 filter cliff và overfetch | [NB5](evidence/05_filtered_search.txt) |
| NB6 ngân sách đúng16, recall/balance, Feast context | [NB6](evidence/06_agent_retrieval.txt): .526→.922 recall, balance .08→.92 |
| NB7 false hit, threshold, TTL, tenant isolation | [NB7](evidence/07_semantic_cache.txt) |
| NB8 leakage gap, PIT, ODFV | [NB8](evidence/08_feature_engineering.txt): target leakage gap.477 |
| Tests | [48 passed](evidence/pytest-final.txt) |
| Bonus | [Architecture](../bonus/ARCHITECTURE.md), [5 queries](evidence/bonus.txt) |
| Container health | [Compose health](evidence/docker/compose-health.json) |
| PostgreSQL/Redis serving thật | [Docker smoke](evidence/docker/smoke.txt) |

Thí nghiệm model đa ngữ dùng đúng 50 câu hỏi gốc, cùng BM25, RRF k60,
không sửa nhãn/golden set: [output](evidence/multilingual-small/02_hybrid_search_rrf.txt).
Hybrid đạt80.6%, exact98%, paraphrase44%, mixed95%; vector paraphrase48%.
BGE-small hybrid mixed100%, nhưng vector paraphrase24%.
Kết quả này là thử nghiệm MiniLM trước cấu hình MPNet/depth 200 bên dưới.

Lần đo API Docker đầu có hybrid P99 60.2ms khi ONNX để mặc định số luồng;
đã lưu trong `docker-notebooks.log` và ghi ở đây, không coi là đạt ngưỡng.
Sau giới hạn ONNX2 threads, hybrid P99 **48.6ms** (đạt <50ms), wall P99
51.8ms. Keyword/semantic P99 lần lượt6.2/42.1ms; 100 calls/mode, warm-up10.
Đây là đo tuần tự trên CPU, chưa phải load test đồng thời.

Rubric chấp nhận cả Lite và Docker. Hồ sơ có output thực tế NB1–NB8 và
bonus; không thể bảo đảm điểm tuyệt đối thay người chấm. Họ tên/cohort
trong REFLECTION đã điền Nguyễn Trường Bảo/cohort4.

API đã được để chạy sau kiểm thử; [health](evidence/docker/api-live-health.json)
cho ready=true/n_docs1000 và [response](evidence/docker/api-live-search.json)
cho hybrid top5 với latency_ms20.80. Các ảnh Lite ban đầu giữ kết quả của
lần chụp; dùng notebook/log cuối làm nguồn số liệu mới nhất khi có khác biệt.

Sau lần tạm dừng, đã mở lại stack và xác nhận
[smoke](evidence/docker/smoke-resumed.txt),
[container health](evidence/docker/compose-health-resumed.json),
[API ready/1000 docs](evidence/docker/api-resumed-health.json) và
[response hybrid top5](evidence/docker/api-resumed-search.json).
Collection BGE-M3 giữ nguyên1000 point/1024d sau khi mở lại Docker.


## Kiểm chứng bổ sung: Linux sạch và cấu hình NB2 cuối

Đã chạy trong container Python 3.12.15/Linux mới, không gắn venv/model cache
của Windows: `bash setup-lite.sh`, `make benchmark`, `make test`,
`make verify-lite` đều PASS. Test: 48 passed. Xem
[trạng thái](evidence/clean-linux/status.txt),
[setup](evidence/clean-linux/setup-lite.txt),
[benchmark](evidence/clean-linux/benchmark.txt),
[test](evidence/clean-linux/test.txt),
[verify](evidence/clean-linux/verify-lite.txt).
Benchmark Linux BGE-small hybrid P99 68,3ms trong lúc chạy các tác vụ CPU khác;
không dùng số này để tuyên bố đạt <50ms. Kết quả API Docker 48,6ms là phép đo riêng.

NB2 mặc định dùng MPNet đa ngữ 768d, RRF k=60, depth=200.
Depth được chọn trên 30 development queries riêng, không sửa corpus/golden.
[Quy trình chọn depth và toàn bộ thử nghiệm](evidence/rrf-depth-multilingual-mpnet.json).
Chạy lại: `.venv/Scripts/python.exe scripts/run_notebooks.py --only 02`
(Linux dùng `.venv/bin/python`). Lần đầu cần tải model khoảng 1,1GB.

| Precision@10 | BM25 | Vector | Hybrid |
|---|---:|---:|---:|
| Trung bình | 77,8% | 80,6% | **82,4%** |
| Exact | **96,7%** | 88,0% | 94,7% |
| Paraphrase | 33,3% | **55,3%** | 50,7% |
| Mixed | **97,0%** | 94,0% | **97,0%** |

Hybrid vượt cả hai mode về trung bình; vector thắng paraphrase và BM25 thắng
exact trong cùng một cấu hình. Mixed đồng hạng cao nhất với BM25: nếu rubric
yêu cầu hybrid *vượt tuyệt đối* BM25 ở mixed, phần đó vẫn chưa đạt.
Không ghép số đo của nhiều model để giả lập một cấu hình đạt đủ mọi điều kiện.
Notebook/log cuối là nguồn số liệu chính; ảnh Lite cũ là bằng chứng lịch sử.
API và benchmark mặc định vẫn dùng BGE-small để đánh giá latency riêng.
