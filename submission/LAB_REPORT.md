# Báo cáo thực hành Lab 19 — Vector Store + Feature Store

**Ngày thực hiện:** 05/10/2026, múi giờ Asia/Bangkok.  
**Môi trường:** Windows, Python 3.12.6. Bản Lite: Qdrant local in-memory,
Feast SQLite online + Parquet offline, FastAPI; embedding
`BAAI/bge-small-en-v1.5`, 384 chiều, CPU. Không sử dụng API key hoặc GPU.

Đã triển khai thêm Docker: Qdrant server + PostgreSQL offline + Redis online,
Feast materialize/PIT thật, API hybrid P99 **48,6ms**, Redis lookup P99
**1,75ms**. NB2 đa ngữ MiniLM đạt hybrid **80,6%**, vector paraphrase **48%**.
NB2 BGE-M3 trên Qdrant server đạt semantic **95,2%**, hybrid **89,0%**;
semantic paraphrase **86,7%**. Model đã chạy thật với1024d/1000 tài liệu.
Chi tiết cấu hình, bằng chứng và giới hạn chấm điểm trong [DEPLOYMENT](DEPLOYMENT.md).

Code và tài liệu được thực hiện với hỗ trợ của Codex. Báo cáo dựa trên
output thực tế, không thay output bằng các con số dự kiến trong template.
Thông tin người nộp trong reflection: Nguyễn Trường Bảo, cohort4.
Đây là thực nghiệm trên dữ liệu tổng hợp, không phải pentest hệ
thống thật hoặc đánh giá khả năng phát hiện tấn công.

## 1. Deliverables và cách kiểm tra

- [8 notebook đã thực thi](../notebooks/) giữ output của **51 code cells**.
- [Trang minh chứng](evidence/index.html): mỗi notebook có HTML đầy đủ,
  HTML chỉ chứa output và log text tương ứng.
- [Ảnh chụp trình duyệt](screenshots/): output thực tế của các notebook.
- [Trạng thái thực thi](evidence/execution.json), [môi trường và hash dữ liệu](evidence/environment.json).
- [Test log](evidence/pytest-final.txt): **48 passed**, không có test bị bỏ qua;
  một cảnh báo deprecation từ Feast/NumPy.
- [Hướng dẫn hiểu bài](STUDY_GUIDE.md) và [reflection](REFLECTION.md).
- [Bonus architecture](../bonus/ARCHITECTURE.md), [agent](../bonus/agent.py),
  [demo](../bonus/demo.py): hybrid memory cho ghi chú học cybersecurity.

`PASS` trong execution.json nghĩa notebook chạy hết, không có cell error.
Các tiêu chí chất lượng và latency được đối chiếu riêng bên dưới. Không
quy đổi tự động thành điểm: giảng viên quyết định theo rubric.

## 2. Kết quả NB1–NB4

### NB1 — Embedding và indexing

Corpus có **1.000 tài liệu**, 10 topic; vector có **384 chiều**. Collection
`lab19` chứa đúng 1.000 point. Query chứa “cloud computing” có 4/5 kết quả
cloud; query diễn đạt lại “phương pháp tự động mở rộng hạ tầng theo lưu
lượng người dùng” có **5/5 cloud**.

Điều này xác nhận ingestion và truy vấn minh họa hoạt động. Nó chưa chứng
minh model giỏi toàn bộ tiếng Việt: slice paraphrase của NB2 cho kết quả
thấp hơn nhiều. Luôn đánh giá trên tập query thay vì một ví dụ đẹp.

### NB2 — Hybrid search bằng RRF

RRF sử dụng `1/(60 + rank)`, rank bắt đầu từ 1, lấy ứng viên sâu ít nhất
50 từ mỗi retriever trước khi trả top-10. Golden set có 50 query; nhãn
relevance là topic của tài liệu.

| Tập query | Số query | BM25 | Semantic | Hybrid |
|---|---:|---:|---:|---:|
| Toàn bộ | 50 | 77,8% | 73,2% | **78,6%** |
| Exact | 15 | **96,7%** | 88,7% | **96,7%** |
| Paraphrase | 15 | **33,3%** | 24,0% | 32,0% |
| Mixed | 20 | 97,0% | 98,5% | **100,0%** |

Hybrid thắng trung bình với mức tăng **0,8 điểm phần trăm** so với BM25
và **5,4 điểm** so với semantic. Nó không thắng ở mọi slice. Đặc biệt,
semantic không thắng paraphrase trong cấu hình này. Đây là hạn chế model
thiên về tiếng Anh và bộ dữ liệu, không phải bằng chứng cần thay công thức
RRF để làm đẹp bảng. Thí nghiệm MiniLM đa ngữ riêng cải thiện vector
paraphrase lên48%. BGE-M3 cũng đã chạy inference thật trên CPU, vector
1024d và Qdrant server (xem [kiểm chứng bổ sung](DEPLOYMENT.md)); e5 chưa chạy.

**BGE-M3, cùng50 queries/RRF60:** semantic/hybrid toàn tập95,2%/89,0%;
exact98%/100%; paraphrase86,7%/66,7%; mixed99,5%/97,5%. BM25 giữ nguyên.
Với model mạnh này, pure vector thắng trung bình và paraphrase/mixed.
Hybrid chỉ thắng exact. `WARN` ở notebook BGE-M3 là tiêu chí chất lượng
chưa đạt, dù cả6 code cells đều thực thi thành công. Bằng chứng và bảng
đầy đủ: [NB2 Docker BGE-M3](evidence/docker/bge-m3/02_hybrid_search_rrf.txt).

### NB3 — API và độ trễ

API báo `ready=True`, `n_docs=1000`. `/search` trả doc_id, title, text,
score và latency_ms. Benchmark thực hiện 10 warm-up query mỗi mode, sau
đó 50 golden query × 2 lần = **100 request/mode**, tuần tự qua HTTP local.

| Mode | P50 server | P95 server | P99 server | P99 HTTP |
|---|---:|---:|---:|---:|
| Keyword | 2,3 ms | 4,1 ms | 4,9 ms | 22,2 ms |
| Semantic | 9,7 ms | 20,4 ms | 32,6 ms | 35,9 ms |
| Hybrid | 15,3 ms | 20,7 ms | **24,7 ms** | 27,8 ms |

Hybrid đạt mục tiêu **P99 server < 50 ms**. Thời gian load model/index nằm
ngoài route timing; HTTP timing bao gồm transport. Kết quả không phải
benchmark tải đồng thời. P99 là thống kê riêng cho mỗi tập request, nên
không diễn giải việc semantic P99 cao hơn hybrid như quan hệ tốc độ cố định.

### NB4 — Feast, materialization và PIT

Đăng ký đúng 3 feature view: `user_profile_features`,
`item_popularity_features`, `query_velocity_features`. Sinh 3 nguồn
Parquet và materialize một khoảng UTC xác định vào SQLite. Bounded
materialization giúp chạy lại nguồn vừa sinh mà không bị watermark của
lần chạy trước bỏ qua dữ liệu. Item lookup `item_0001` trả click count 13.

Online u_001 trả `187/vi/cloud`, query count 11 và 4 topic. Đo 100 lookup:
**P50 0,36 ms, P95 0,53 ms, P99 0,82 ms**, đạt mốc P99 < 10 ms. Lookup
đơn lẻ được báo riêng trong notebook.

PIT trả **3 dòng × 4 cột**. u_001 có snapshot cũ 170/security tại NOW−3h,
snapshot mới 187/cloud tại NOW−1h; event tại NOW−2h. Historical trả
170/security, online trả 187/cloud. Các assertion kiểm tra cả hai giá trị.

Ở lần đầu, template chỉ có snapshot sau event của u_001. Feast file store
loại dòng không có history, khiến bảng chỉ còn 2 dòng. Đã lưu [log chẩn
đoán](evidence/diagnostics/04_initial_missing_history.txt), thêm snapshot
cũ và chạy lại thành công. Việc thêm dữ liệu minh họa giúp kiểm tra ranh
giới thời gian rõ ràng; không thay đổi ngữ nghĩa PIT.

## 3. Kết quả NB5–NB8

### NB5 — Recall dưới filter chọn lọc

Ground truth là cosine chính xác trên subset khớp filter. Với
`tenant=acme AND published≥2026`, subset chiếm **3,8%** corpus:
post-filter lấy 10 ứng viên toàn corpus có recall **0,00**, truy xuất có
filter đạt **1,00**. Trên ba query của over-fetch ladder, recall tăng
0,03 → 0,27 → 0,80 → 1,00 khi fetch_k tăng 10 → 50 → 200 → 500.

Phải lấy tới **50% corpus** mới khôi phục đầy đủ recall ở phép đo này.
Cột “1%” của filtered retrieval chỉ là số kết quả yêu cầu trên tổng corpus,
không phải chứng minh engine chỉ kiểm tra 10 vector. Qdrant Lite không
dùng HNSW/payload index như server; không suy rộng latency sang production.

### NB6 — Tách câu hỏi và reflection

12 câu ghép được đánh giá với cùng giới hạn tối đa 16 document slots.
Ground truth là top vector chính xác của từng vế, chưa phải nhãn chuyên
môn do người đọc tài liệu gán.

| Chiến lược | Recall | Balance | Call trung bình | Slot yêu cầu trung bình |
|---|---:|---:|---:|---:|
| Single-shot | 0,526 | 0,08 | 1,0 | 16,0 |
| Agentic không filter | **0,922** | **0,92** | 2,3 | 16,0 |
| Agentic có filter | 0,839 | 0,75 | 2,3 | 16,0 |

Cả ba chiến lược yêu cầu đúng 16 slot trong phép đo, gồm cả retry.
Planner phân phối phần dư sau phép chia để không bỏ phí slot; số doc độc
nhất có thể thấp hơn do trùng kết quả. Filter topic suy đoán làm giảm recall vì loại các kết quả liên
quan thuộc topic lân cận. Demo starvation dùng năm 2027 cho 0 kết quả;
reflection bỏ topic/year filter và lấy lại 8 doc trong call thứ hai.

`build_context()` trả feature Feast thật của u_001 và doc_ids theo affinity
cloud. Planner là rule-based, chưa dùng LLM. Reflection này chỉ áp dụng
filter nội dung; không được nới tenant/user authorization khi thiếu kết quả.

### NB7 — Cache threshold, TTL và tenant isolation

Cache có 25 câu, đánh giá 75 positive và 75 negative probe.

| Ngưỡng | Positive hit đúng | Negative bị nhận sai |
|---|---:|---:|
| 0,75 | 100% | **36%** |
| 0,80 | 100% | 5% |
| 0,85 | 100% | **0%** |
| 0,90 | 96% | 0% |
| 0,95 | 53% | 0% |

Chọn **0,85 cho bộ probe này**, vì giữ toàn bộ positive hit đúng và không
nhận sai negative đã đo. 0% trên 75 probe không bảo đảm 0% trong hệ thật;
ground truth đang dựa nguồn query, cần đánh giá semantic equivalence bằng
nhãn thủ công trước khi triển khai.

TTL 1.800 giây: HIT tại t=0 và 600, MISS tại t=4.200, stale eviction=1.
Đây là đồng hồ ảo để kiểm thử. `namespaced=False` cho GLOBEX đọc câu trả
lời của ACME; `True` trả MISS. Assertion và test xác nhận tenant isolation.

### NB8 — Feature engineering và leakage

Sinh **9.019 event, 200 user, 8.141 session**. Các feature cửa sổ, tỷ lệ,
lag/delta và recency được tính từ quá khứ. So sánh target encoding trên
session_id:

| Encoding | Train AUC | Test AUC | Gap |
|---|---:|---:|---:|
| Frequency | 0,521 | 0,516 | 0,005 |
| Target naive | **0,999** | 0,522 | **0,477** |
| Target in-fold | 0,519 | 0,522 | −0,003 |

Naive encoding vượt mốc gap 0,30 vì gần như chứa nhãn của chính dòng.
Latest join kéo feature tương lai vào **98,2%** của 3.535 training rows:
AUC latest **0,715**, PIT **0,595**, chênh **0,120**. Đây là lift do dùng
tương lai trong thực nghiệm, không phải hiệu năng model đã được train.

On-demand feature lấy cùng avg7d=3.566.076 cho u_000: amount=100.000
cho ratio **0,03**, spike=0; amount=15.000.000 cho ratio **4,21**, spike=1.
Assertion xác nhận request thay đổi feature. Rule spike là minh họa,
không phải quyết định gian lận.

## 4. Bonus hybrid memory

POC lưu ghi chú theo đoạn, truy xuất BM25 + vector với RRF, ghép hồ sơ
Feast và bộ đếm truy vấn thật trong phiên. Cả hai retriever đều giữ phạm
vi user. Năm query minh họa Kubernetes, recommendation context, hoạt
động, paraphrase và cloud security. Demo kiểm tra ghi chú user khác không
lọt vào context; bộ test kiểm tra thêm scope của cả hai danh sách thứ hạng.

Không gọi LLM; recommendation hiện chỉ là context đầu vào. Dữ liệu Feast
là snapshot tổng hợp; bộ đếm trong phiên không phải streaming Feast.
Memory nằm trong RAM. Chưa có authentication hoặc persistence, nên
user_id do caller truyền vào chưa là danh tính đáng tin của sản phẩm thật.
Chi tiết tradeoff và giới hạn nằm trong ARCHITECTURE.md.

## 5. Chạy lại và nộp bài

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-lite.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/run_notebooks.py
.\.venv\Scripts\python.exe scripts/verify_submission.py
.\.venv\Scripts\python.exe scripts/build_evidence.py
```

`requirements-win-py312.lock.txt` ghi phiên bản toàn bộ dependency của
lần chạy này, dành cho Windows/Python 3.12. Requirements chung vẫn dành
cho các nền tảng khác. Model được tải từ Hugging Face khi setup lần đầu.
Nguồn corpus/golden set được sinh lại với seed=42; timestamp trong nguồn
Feast và latency có thể thay đổi giữa các lần chạy.

Kết quả benchmark đầy đủ **5.000 call/mode** nằm trong
[benchmark.json](evidence/benchmark.json), log ở [benchmark.txt](evidence/benchmark.txt).
Đo trực tiếp searcher sau warm-up cho P99 keyword **3,3 ms**, semantic
**16,4 ms**, hybrid **19,8 ms**; đây là phép đo khác với HTTP ở NB3.
[checks.json](evidence/checks.json) ghi exit code smoke, benchmark và bonus.

Trước khi nộp, điền tên/cohort, đọc lại reflection và notebook, thử một số
query riêng để hiểu bài. Repo chưa được push lên GitHub hoặc gửi LMS trong
phiên này. Rubric dùng repo public có notebook output và ảnh minh chứng;
việc đăng công khai/nộp bài do người học thực hiện.
