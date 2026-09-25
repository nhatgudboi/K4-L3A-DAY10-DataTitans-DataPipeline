# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability

- **Thời gian thực thi:** `2026-09-25 08:42:15 UTC`
- **Nguồn dữ liệu:** `Crossref REST API`
- **Số lượng bản ghi gốc:** `24`
- **Số lượng bản ghi sau Clean:** `24`

---

## 1. Kết Quả Kiểm Tra Chất Lượng Dữ Liệu (Data Quality Gate)

Hệ thống sử dụng **Great Expectations 1.x** (chế độ ephemeral) kết hợp giám sát **Freshness SLA**:

| Chỉ số kiểm tra | Tiêu chuẩn | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Row Count Range** | 5 <= N <= 5000 | 24 dòng | [OK] |
| **Non-Null Primary Keys** | `paper_id`, `title`, `text` not null | 100% Not Null | [OK] |
| **Unique Identification** | `paper_id` unique | 100% Unique | [OK] |
| **Summary Length** | `summary` >= 30 ký tự | Đạt chuẩn | [OK] |
| **Overall Quality Gate** | All expectations passed | **PASSED** | PASSED |

### Giám sát độ tươi mới (Freshness SLA):
- **Ngưỡng SLA quy định:** Bài báo không cũ quá `180` ngày.
- **Tỷ lệ bài báo quá hạn:** `4.2%` (Ngưỡng cảnh báo: `> 25%`).
- **Trạng thái Freshness:** **HEALTHY (Fresh)**.

---

## 2. Đo Lường Chỉ Số Nền Tảng RAG Agent (Baseline Benchmark)

Đánh giá được thực hiện trên bộ dữ liệu chuẩn 10 câu hỏi bao quát 4 dạng nghiệp vụ: `summary`, `authors`, `date`, `categories`.

| Chỉ số đánh giá | Giá trị Baseline | Đánh giá |
| :--- | :--- | :--- |
| **Số lượng câu hỏi đánh giá** | `10` câu | Đầy đủ 4 nhóm nghiệp vụ |
| **Retrieval Hit Rate** | **`100.00%`** | Độ phủ tài liệu liên quan tuyệt đối |
| **Mean Token F1** | **`1.0000`** | Khả năng trích xuất thông tin chính xác |
| **LLM Judge Accuracy** | **`100.00%`** | Phán quyết mức độ chính xác câu trả lời |
| **Mean Judge Score** | **`5.00 / 5.0`** | Điểm số chất lượng câu trả lời |

---

## 3. Kết Luận Pha 1
Dữ liệu sạch đã vượt qua toàn bộ các bài kiểm tra của Data Quality Gate và Freshness SLA. Mô hình nhúng `all-MiniLM-L6-v2` và ChromaDB hoạt động ổn định, đạt hiệu suất tối ưu làm mốc tham chiếu cho các pha kiểm thử sự cố tiếp theo.
