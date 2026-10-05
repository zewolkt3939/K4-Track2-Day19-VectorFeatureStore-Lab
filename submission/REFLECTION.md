# Reflection — Lab 19

**Tên:** Nguyễn Trường Bảo
**Cohort:** 4
**Path đã chạy:** Lite và Docker (Qdrant/PostgreSQL/Redis) — Windows, Python 3.12.6, BGE-small; thêm MiniLM (384d) và kiểm chứng BGE-M3 (1024d) trên CPU/Qdrant server.

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên 50 golden queries, cấu hình MPNet đa ngữ với RRF k=60, depth=200
cho hybrid 82,4%, vượt BM25 77,8% và vector 80,6%. Exact: BM25 thắng
96,7%; paraphrase: vector thắng 55,3%; mixed: hybrid đồng hạng BM25 97%,
cao hơn vector 94%. Depth được chọn trên 30 development queries riêng,
không sửa corpus hoặc nhãn golden. Tập phát triển nhỏ nên chưa chứng minh
khả năng tổng quát hóa.

BGE-M3 trên Qdrant server lại cho vector 95,2%, cao hơn hybrid 89%.
Thêm thứ hạng BM25 yếu có thể kéo giảm vector mạnh; hybrid không luôn thắng.

Tôi chọn BM25 cho CVE, IOC hoặc mã lỗi chính xác khi cần giảm latency.
Pure vector phù hợp với diễn đạt lại và model đã được kiểm chứng trên ngôn
ngữ mục tiêu. Hybrid hữu ích khi câu hỏi có cả từ khóa và ý nghĩa, nhưng
phải đo trên dữ liệu thực tế. Golden set chỉ đánh giá topic trên dữ liệu
tổng hợp, chưa chứng minh chất lượng trả lời câu hỏi cybersecurity thật.


---

## Điều ngạc nhiên nhất khi làm lab này

Đổi BGE-small sang BGE-M3 làm semantic paraphrase tăng từ24% lên86,7%,
nhưng hybrid lại thua pure vector. Cache hit cũng có thể là lỗi trả đáp
án sai hoặc rò dữ liệu của tenant khác.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`): POC hybrid memory cho ghi chú cybersecurity.
- [ ] Pair work với: _<tên đồng đội nếu có>_
