# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | **Hoàng Minh Tuấn** |
| MSSV | `2A202602758` |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | DataTitans (Nhóm 3 thành viên: Nhật, Vĩ, Tuấn) |
| Vai trò chính | **Data Observability & Reporting Specialist** |
| Repository | `https://github.com/nhatgudboi/K4-L3A-Day10-Data-Pipeline-Data-Observability` |
| Ngày hoàn thành | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| **Data Quality Gate (GX 1.x)** | `src/observability/quality.py`<br>- `run_data_quality_checks` | DataFrame sạch hoặc DataFrame bị tiêm lỗi | `baseline_quality_report.json`<br>`corrupted_quality_report.json` | Hoàn thành |
| **Freshness SLA Monitoring** | `src/observability/quality.py`<br>- `build_freshness_report` | DataFrame và ngưỡng `freshness_threshold_days` (180 ngày) | `freshness_report.json`<br>`corrupted_freshness_report.json` | Hoàn thành |
| **Automated Reporting Suite** | `src/observability/reporting.py`<br>- `generate_phase1_report`<br>- `generate_corruption_report` | Metrics đánh giá và kết quả kiểm định chất lượng | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |
| **Bonus Features: Dashboard & Self-Healing** | `src/observability/dashboard.py`<br>`src/pipelines/auto_healing.py` | Artifacts chất lượng dữ liệu | `data/reports/observability_dashboard.html`<br>`data/results/self_healing_audit.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đồng bộ schema kiểm định | Nhật (`cleaning.py`) | Đảm bảo các cột `paper_id`, `title`, `text_for_embedding`, `summary` đúng kiểu dữ liệu trước khi kiểm tra |
| Tích hợp kết quả đo lường | Vĩ (`metrics.py`) | Tiếp nhận các chỉ số `retrieval_hit_rate` và `token_f1` để tự động điền vào bảng so sánh Markdown |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Triển khai GX 1.x Quality Gate | `src/observability/quality.py` | Kiểm tra 6 Expectation trên RAM (ephemeral) | Lệnh kiểm tra console in: `Quality check status = True` |
| Giám sát Freshness SLA | `data/quality/freshness_report.json` | Baseline: 0% Stale (Đạt)<br>Corrupted: 42.9% Stale (Cảnh báo vi phạm) | Kiểm tra thuộc tính `is_fresh` trong report |
| Xuất báo cáo Baseline | `data/reports/phase1_report.md` | Báo cáo chi tiết luồng dữ liệu sạch và kết quả GX | Tồn tại file Markdown đầy đủ tiêu chuẩn |
| Xuất báo cáo đối chiếu 3 trạng thái | `data/reports/corruption_report.md` | Bảng so sánh 3 cột: Baseline vs Corrupted vs Repaired | Tồn tại bảng so sánh định lượng trực quan |

**Output minh chứng cụ thể:**
- File `data/reports/corruption_report.md` có đầy đủ 3 cột so sánh chứng minh:
  - Baseline: GX PASSED, SLA HEALTHY
  - Corrupted: GX FAILED, SLA BREACHED
  - Repaired: GX PASSED, SLA HEALTHY

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong hệ thống RAG, lỗi dữ liệu thường diễn ra âm thầm (Silent Failure). Cần xây dựng một "chốt kiểm dịch dữ liệu" tự động bằng **Great Expectations 1.x** để chặn đứng dữ liệu bẩn trước khi kịp nhúng vào Vector Database, cùng hệ thống cảnh báo sớm khi dữ liệu bị lỗi thời (Stale Data).

### Cách triển khai
1. **Tuân thủ chuẩn Great Expectations 1.x mới nhất:**
   - Sử dụng cú pháp mới `gx.get_context(mode="ephemeral")` chạy trực tiếp trên RAM, không sinh file rác.
   - Kết nối dữ liệu qua `context.data_sources.add_pandas()` và `add_batch_definition_whole_dataframe()`.
2. **4 Nhóm Expectations nghiêm ngặt:**
   - `ExpectTableRowCountToBeBetween`: Số lượng bản ghi nằm trong khoảng [5, 5000].
   - `ExpectColumnValuesToNotBeNull`: Các cột trọng yếu `paper_id`, `title`, `text_for_embedding` không được phép null.
   - `ExpectColumnValuesToBeUnique`: Đảm bảo `paper_id` là duy nhất, không trùng lặp.
   - `ExpectColumnValueLengthsToBeBetween`: Trường `summary` có độ dài tối thiểu 30 ký tự để AI có đủ ngữ cảnh đọc hiểu.
3. **Giám sát độ tươi mới (Freshness SLA):**
   - Đặt ngưỡng SLA: Bài báo không cũ quá 180 ngày (tính theo `age_days`).
   - Cảnh báo vi phạm `is_fresh = False` khi tỷ lệ bài báo cũ vượt quá 25% tổng số lượng dữ liệu.
4. **Báo cáo đối chiếu tự động:**
   - Tự động tổng hợp số liệu từ các file JSON để xuất ra bảng so sánh Markdown trực quan, giúp các bên liên quan dễ dàng quan sát sự suy giảm và phục hồi của hệ thống.
