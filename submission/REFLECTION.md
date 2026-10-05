# Reflection — Lab 19

**Tên:** Nguyễn Trường Bảo
**Cohort:** 4
**Path đã chạy:** Lite và Docker (Qdrant/PostgreSQL/Redis) — Windows, Python 3.12.6, BGE-small; thêm MiniLM (384d) và kiểm chứng BGE-M3 (1024d) trên CPU/Qdrant server.

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên 50 golden queries, BGE-small có hybrid 78,6%, cao hơn BM25 77,8%
và semantic 73,2%. Exact: BM25/hybrid cùng 96,7%; mixed: hybrid 100%.
Paraphrase còn yếu: semantic 24%, BM25 33,3%. MiniLM đa ngữ nâng semantic
paraphrase lên 48%.

Khi chạy BGE-M3 thật trên Qdrant server, semantic đạt 95,2%, vượt hybrid
89%. Exact: hybrid thắng với 100%; paraphrase: semantic 86,7% so với
hybrid 66,7%; mixed: semantic 99,5% so với hybrid 97,5%. Kết quả cho thấy
hybrid không luôn tốt hơn: thêm thứ hạng BM25 yếu có thể kéo giảm kết quả
của vector mạnh.

Tôi chọn BM25 cho định danh chính xác như CVE, IOC hoặc mã lỗi khi muốn
giảm latency. Pure vector phù hợp khi diễn đạt lại là chủ yếu và model
đã được kiểm chứng trên ngôn ngữ mục tiêu. Hybrid cần được đo, không mặc
định luôn thắng. Golden set ở lab đánh giá topic trên dữ liệu tổng hợp,
chưa chứng minh chất lượng trả lời câu hỏi cybersecurity thật.

_Bản reflection được hỗ trợ soạn bởi Codex từ output thực tế; cần người
học đọc lại trước khi nộp._

---

## Điều ngạc nhiên nhất khi làm lab này

Đổi BGE-small sang BGE-M3 làm semantic paraphrase tăng từ24% lên86,7%,
nhưng hybrid lại thua pure vector. Cache hit cũng có thể là lỗi trả đáp
án sai hoặc rò dữ liệu của tenant khác.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`): POC hybrid memory cho ghi chú cybersecurity.
- [ ] Pair work với: _<tên đồng đội nếu có>_
