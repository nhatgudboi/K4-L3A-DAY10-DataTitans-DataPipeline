# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | **Nguyễn Phi Nhật** |
| MSSV | `2A202602658` |
| Khóa/Lớp | K4-L3A |
| Tên nhóm | DataTitans (Nhóm 3 thành viên: Nhật, Vĩ, Tuấn) |
| Vai trò chính | **Pipeline Orchestration & Data Foundation Lead (Phụ trách 2 phần việc)** |
| Repository | `https://github.com/nhatgudboi/K4-L3A-Day10-Data-Pipeline-Data-Observability` |
| Ngày hoàn thành | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| **Ingestion & Raw Preservation** | `src/ingestion/crossref.py`<br>- `parse_crossref_payload`<br>- `fetch_source_records`<br>- `load_raw_records` | Crossref REST API hoặc snapshot `data/raw/crossref_response.json` | `data/raw/crossref_records.json` (24 bài báo) | Hoàn thành |
| **Cleaning & Data Modeling** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe` | Danh sách `PaperRecord` từ raw records | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` (24 dòng sạch) | Hoàn thành |
| **Synthetic Corruption Suite** | `src/ingestion/corruption.py`<br>- `corrupt_clean_dataframe` | DataFrame sạch | `data/clean/papers_clean_corrupted.csv`<br>`data/results/corruption_log.json` | Hoàn thành |
| **Pipeline Orchestration** | `src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py`<br>`script/run_phase1.py`<br>`script/run_corruption_flow.py` | Toàn bộ các module thành phần | Hai luồng chạy end-to-end không lỗi, sinh đầy đủ artifacts | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp luồng đánh giá | Hỗ trợ Vĩ (`testset.py`) | Đảm bảo cấu trúc câu hỏi khớp với logic trích xuất của `qa.py` và `metrics.py` |
| Tích hợp trạm kiểm định | Hỗ trợ Tuấn (`quality.py`) | Kết nối báo cáo Great Expectations 1.x và Freshness SLA vào `phase1.py` và `corruption_flow.py` |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Kéo và lưu trữ dữ liệu thô | `src/ingestion/crossref.py` | 24 bản ghi chuẩn trong `data/raw/` | Lệnh kiểm tra console in: `Đã nạp 24 bài báo` |
| Làm sạch và tạo text nhúng | `src/ingestion/cleaning.py` | File `papers_clean.csv` có đầy đủ `text_for_embedding`, `age_days` | Lệnh kiểm tra console in: `Clean thành công 24 dòng` |
| Tiêm 6 dạng độc tố dữ liệu | `src/ingestion/corruption.py` | `corruption_log.json` ghi lại 6 kịch bản lỗi | Lệnh kiểm tra console in: `Corrupted 24 dòng` |
| Điều phối 2 luồng end-to-end | `run_phase1.py`<br>`run_corruption_flow.py` | Toàn bộ artifacts và bảng so sánh 3 trạng thái | Chạy thành công Exit code 0 cho cả 2 scripts |

**Output minh chứng cụ thể:**
- Bảng đối chiếu 3 trạng thái tại `data/reports/corruption_report.md` thể hiện rõ:
  - Baseline Hit Rate: 100%
  - Corrupted Hit Rate: 50%
  - Repaired Hit Rate: 100%

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng một Data Pipeline chuẩn mực cho hệ thống RAG: dữ liệu thô từ bên ngoài thường không đồng nhất, chứa mã XML rác, có thể trùng lặp hoặc mất mạng khi cào. Cần đảm bảo hệ thống có cơ chế Fallback snapshot offline và tính chất bất biến (Idempotent) để tự phục hồi khi dữ liệu bị lỗi.

### Cách triển khai
1. **Raw Preservation:** Tải từ Crossref API với cơ chế retry; nếu gặp lỗi mạng hoặc `429 Too Many Requests`, tự động fallback sang `crossref_response.json` có sẵn. Bảo toàn nguyên vẹn snapshot thô trước khi biến đổi.
2. **Data Cleaning:** Bóc tách XML tags, tính toán `age_days = (run_date - published).days`, ghép nối trường ngữ cảnh `text_for_embedding`, và khử trùng lặp bản ghi theo `paper_id`.
3. **Controlled Synthetic Corruption:** Chủ động tiêm 6 kịch bản lỗi: bỏ rơi 20% bản ghi mới nhất, xóa rỗng abstract, chèn chuỗi ký tự rác, cắt ngắn tiêu đề dưới 8 ký tự, lùi ngày xuất bản về quá khứ 365 ngày, và nhân bản dòng để vi phạm khóa unique.
4. **Idempotent Repair:** Tự động đọc lại từ bản lưu trữ thô ban đầu, xóa bỏ collection lỗi trong ChromaDB và nhúng lại từ đầu. Chạy nhiều lần vẫn cho kết quả chuẩn sạch đồng nhất.
