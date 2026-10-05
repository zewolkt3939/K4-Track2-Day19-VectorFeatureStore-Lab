# Hướng dẫn hiểu và bảo vệ bài Lab 19

## NB1: text biến thành vector như thế nào?

Model nhận `title + text`, trả vector 384 chiều. Các vector được so sánh
bằng cosine: hướng càng gần, nội dung càng được model coi là tương đồng.
Vector không chứa một đáp án đúng/sai và không thay thế việc đánh giá bằng
truy vấn thật. Index 1.000 vector chứng minh ingestion hoàn tất; tìm đúng
topic mới là bằng chứng chất lượng. Câu diễn đạt lại tiếng Việt là bài kiểm
tra hữu ích vì model mặc định thiên về tiếng Anh.

**Liên hệ security:** dùng embedding tìm ghi chú hoặc đoạn log có cùng ý
nghĩa; dùng từ khóa để giữ các giá trị chính xác như CVE, IOC và rule ID.
Hai loại tín hiệu có vai trò khác nhau.

## NB2: tại sao cộng thứ hạng?

BM25 và cosine có thang điểm khác nhau. Cộng trực tiếp hai score có thể làm
một nguồn chi phối. RRF dùng thứ hạng: tài liệu đứng đầu một danh sách đóng
góp `1/(60+1)`; đứng thứ hai đóng góp `1/(60+2)`. Có mặt trong cả hai danh
sách thì cộng hai đóng góp. Lấy sâu 50 ứng viên giúp hợp nhất có đủ tín hiệu
trước khi trả top-10. Không có bảo đảm toán học hybrid luôn thắng.

Precision@10 ở lab đo phần tài liệu thuộc đúng topic trong top-10. Đây là
nhãn topic trên dữ liệu tổng hợp, không đo khả năng trả lời một câu hỏi
chuyên môn. Trên hệ thống pentest, cần thêm đánh giá đúng phiên bản, nguồn,
điều kiện khai thác và phạm vi được phép. Golden set cố định không nên được
dùng để chỉnh tham số liên tục rồi coi kết quả là độ chính xác trên dữ liệu
mới.

## NB3: P99 nói gì và không nói gì?

P99 gần với trường hợp chậm nhất trong 100 lần gọi, nên nhạy với tác vụ
khác trên máy. Notebook warm-up trước khi đo, báo thời gian server và thời
gian HTTP riêng. Model/index startup không nằm trong `latency_ms` của route.
Đây là thử nghiệm tuần tự trên máy local, chưa phải đo concurrent load.
Không được kết luận đáp ứng hàng nghìn người dùng chỉ từ P99 dưới 50 ms.

## NB4: Feature Store khác Vector Store ở đâu?

Vector Store trả tài liệu gần query; Feature Store trả giá trị có tên theo
entity, ví dụ `u_001 → preferred_language=vi`. `apply` đăng ký schema và
registry; `materialize` đưa dữ liệu offline vào online store; online lookup
lấy giá trị phục vụ request. Materialization không tự chạy liên tục.

PIT join lấy dữ liệu đã tồn tại tại thời điểm sự kiện. User u_001 có hai
snapshot: cũ là 170/security, mới là 187/cloud. Event nằm giữa hai snapshot,
nên historical phải trả 170/security, còn online trả 187/cloud. Nếu không
có snapshot cũ, Feast file store ở lần chạy đầu loại dòng không khớp.
Lấy profile mới nhất cho sự kiện cũ có thể làm model thấy tương lai.
TTL thể hiện phạm vi thời gian tìm feature theo định nghĩa Feast; cần kiểm
tra timestamp và lịch cập nhật riêng để bảo đảm freshness khi serving.

## NB5: tại sao lọc sau làm mất recall?

Nếu chỉ 4% tài liệu được phép và lấy top-10 toàn bộ corpus trước, gần hết
ứng viên có thể bị loại. Danh sách còn lại không phải top-10 tốt nhất trong
phần được phép. Ground truth phải là cosine chính xác trên subset đã lọc.
Over-fetch có thể cứu recall nhưng tốn ứng viên; lọc ngay khi truy xuất giữ
phạm vi đúng. Trong Lite, Qdrant local quét vector và không có lợi ích HNSW
production; bảng không chứng minh tốc độ ANN trên corpus lớn.

**Liên hệ security:** tenant/user filter phải đến từ danh tính và policy
đã kiểm chứng. Không nới filter quyền truy cập khi thiếu kết quả. Reflection
ở NB6 chỉ nới topic/year trong demo, không được dùng để nới authorization.

## NB6: agent khác single-shot ở đâu?

Planner dùng luật, tách câu hỏi nhiều ý rồi chia ngân sách truy xuất. Agent
kiểm tra số kết quả và thử lại nếu filter topic/year quá chặt. Nó trả bằng
chứng, chưa tạo câu trả lời bằng LLM. Bảng cần kiểm tra recall, balance,
số call, latency và tổng `top_k` thực tế kể cả retry. Nếu retry vượt ngân
sách, phải báo điều đó trước khi tuyên bố so sánh công bằng.

Ground truth của bài này là top vector của từng vế câu hỏi, nên phép đo ưu
tiên chiến lược tách câu. Nó minh họa retrieval strategy, chưa xác nhận tính
đúng đắn chuyên môn hoặc hiệu quả trên câu hỏi người dùng thật.

## NB7: cache hit chưa chắc là thành công

Ba lỗi cần phân biệt: false hit trả đáp án cho câu khác; stale hit trả
thông tin hết hạn; cross-tenant hit trả dữ liệu của người khác. Ngưỡng cần
đánh giá cả tiết kiệm và hit sai. Demo so sánh đúng nguồn câu hỏi, chặt hơn
so sánh topic, nhưng một số câu khác nguồn có thể cùng nghĩa; cần nhãn thủ
công khi áp dụng thực tế. Kết quả sweep chỉ áp dụng cho probe này.

TTL dùng đồng hồ ảo để test mà không chờ 30 phút; đó không phải thời gian
thực của dịch vụ. Tách tenant là bắt buộc cho cả cache và retrieval. Đổi
model phải index lại vì vector khác không gian. Quyền đọc cũng có thể đổi,
nên cache hit phải kiểm tra policy hiện tại, không chỉ tenant.

## NB8: phát hiện model “học thuộc đáp án”

Target encoding biến category thành trung bình nhãn. Category rất nhỏ như
session_id làm feature của dòng chứa chính nhãn của nó. Train AUC tăng
nhưng holdout không tăng tương ứng. Chia dữ liệu trước, fit encoder trên
train, dùng out-of-fold cho train giúp giảm kiểu leakage này. Với dữ liệu
security theo thời gian, random split và random folds vẫn chưa đủ: nên
dùng time split, group theo host/user và kiểm tra dịch chuyển phân phối.

Latest join có thể đưa feature tương lai vào sự kiện cũ; PIT join sửa ranh
giới thời gian. Feature `amount / avg_amount_7d` kết hợp giá trị đã lưu với
số tiền của request. Cùng user, hai giao dịch phải cho ratio khác nhau.
`is_spike` chỉ là rule minh họa, chưa phải kết luận gian lận.

## Tự kiểm tra trước khi nộp

Model làm thay đổi lựa chọn retriever. Trên cùng50 câu hỏi, BGE-small có
hybrid78,6% và semantic73,2%; BGE-M3 trên Qdrant server có semantic95,2%
và hybrid89%. Đừng suy ra RRF luôn thắng: BM25 yếu trên paraphrase có thể
làm thứ hạng kết hợp kém hơn vector mạnh. Xem bảng theo từng loại query
trong [báo cáo triển khai](DEPLOYMENT.md). P99 API48,6ms thuộc BGE-small,
không phải BGE-M3. Docker đã kiểm chứng; Podman/Apple là runtime khác.

1. Mở từng `.ipynb`, đọc output và giải thích cảnh báo bằng số đo.
2. Đổi một query sang nội dung security mình hiểu; kiểm tra từng kết quả.
3. Thử thêm user vào bonus và xác nhận hai retriever giữ đúng phạm vi.
4. Giải thích vì sao historical khác online và tại sao dòng thiếu history có thể bị loại.
5. Điền tên/cohort thực; đọc lại reflection được hỗ trợ soạn bởi AI.
6. Nộp notebook có output và ảnh minh chứng cùng repo public theo yêu cầu lớp.
