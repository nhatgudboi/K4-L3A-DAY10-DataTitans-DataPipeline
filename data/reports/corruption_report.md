# Báo Cáo Đối Chiếu 3 Trạng Thái — Data Quality, Corruption & Self-Healing

- **Thời gian lập báo cáo:** `2026-09-25 08:43:25 UTC`
- **Mục tiêu:** Chứng minh hiện tượng **Silent Failure** khi dữ liệu bị lỗi, năng lực phát hiện của **Data Observability Gate (GX 1.x)**, và khả năng tự phục hồi an toàn (**Idempotent Repair**).

---

## 1. Bảng Tổng Hợp Đối Chiếu 3 Trạng Thái (Benchmark Comparison)

| Hạng mục đánh giá | 1. Dữ liệu Sạch (Baseline) | 2. Dữ liệu Bị Lỗi (Corrupted) | 3. Sau Phục Hồi (Repaired) | Nhận xét xu hướng |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **100.00%** | **50.00%** | **100.00%** | Giảm sút mạnh do drop & corrupt dữ liệu; phục hồi 100% |
| **Mean Token F1** | **1.0000** | **0.6506** | **1.0000** | Câu trả lời bị sai lệch/nhiễu; lấy lại độ chính xác |
| **LLM Judge Accuracy** | **100.00%** | **60.00%** | **100.00%** | Độ tin cậy sụt giảm nghiêm trọng; phục hồi hoàn toàn |
| **Mean Judge Score** | **5.00 / 5.0** | **3.50 / 5.0** | **5.00 / 5.0** | Điểm chất lượng câu trả lời khôi phục trọn vẹn |
| **Great Expectations 1.x** | **PASSED** | **FAILED** | **PASSED** | Chốt kiểm soát phát hiện ngay dữ liệu xấu |
| **Freshness SLA (>25% Stale)** | **HEALTHY** | **BREACHED (Cảnh báo) (58.3%)** | **HEALTHY (Đạt SLA) (4.2%)** | Giám sát độ tươi phát hiện dữ liệu quá hạn |

---

## 2. Phân Tích Hiện Tượng "Thất Bại Thầm Lặng" (Silent Failure)

Khi tiêm 6 kịch bản dữ liệu lỗi (`drop_latest`, `blank_summary`, `inject_noise`, `truncate_title`, `stale_date`, `duplicate_rows`):
1. **Agent không hề báo lỗi Exception đỏ:** Hệ thống vẫn chạy bình thường, Agent vẫn tự tin trả lời câu hỏi của người dùng.
2. **Sai lệch thực tế:** Do bản ghi mới bị mất và tiêu đề/tóm tắt bị cắt ngắn hoặc chèn nhiễu, ChromaDB trả về sai tài liệu hoặc trả về ngữ cảnh rỗng, dẫn đến **Retrieval Hit Rate** giảm từ `100.00%` xuống `50.00%` và **Token F1** giảm từ `1.0000` xuống `0.6506`.
3. **Giá trị của Data Quality Gate (GX 1.x):** Nếu không có Great Expectations và Freshness SLA gióng chuông cảnh báo trước khi nạp vào Vector Database, dữ liệu bẩn này sẽ âm thầm lọt vào Production và gây ảo giác cho người dùng cuối.

---

## 3. Cơ Chế Phục Hồi Dữ Liệu An Toàn (Idempotent Repair)

Hệ thống áp dụng cơ chế tự phục hồi chuẩn kỹ nghệ dữ liệu:
- **Nguyên tắc Bảo toàn Dữ liệu Gốc (Raw Preservation):** Luôn giữ nguyên vẹn snapshot thô ban đầu tại `data/raw/crossref_records.json` (hoặc `crossref_response.json`).
- **Tính toán Bất biến (Idempotent):** Pipeline chạy lại từ dữ liệu thô, thực hiện các bước Cleaning chuẩn hóa, xóa bỏ hoàn toàn collection lỗi trong ChromaDB và lập chỉ mục mới. Chạy 1 lần hay 100 lần đều cho ra kết quả đồng nhất.
- **Minh chứng phục hồi:** Tất cả chỉ số sau khi Repair (`Retrieval Hit Rate: 100.00%`, `Token F1: 1.0000`) đều tương đương với Baseline sạch ban đầu, chứng minh hệ thống tự chữa lành thành công mà không cần can thiệp thủ công.
