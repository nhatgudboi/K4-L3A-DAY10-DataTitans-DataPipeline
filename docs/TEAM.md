# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `DataTitans`
- **Mã Nhóm / Lớp:** `K4-L3A-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-Data-Pipeline-Data-Observability`
- **Nhánh thực hiện bài nộp:** `main` (100đ chuẩn + 10đ Bonus)

---

## 👥 Danh Sách Thành Viên (Nhóm 3 thành viên: Nhật, Vĩ, Tuấn)

> Theo thỏa thuận phân công nhóm 3 người: Trưởng nhóm (Nhật) phụ trách 2 phần việc (Ingestion, Cleaning, Corruption & Pipeline Orchestration), 2 thành viên còn lại (Vĩ & Tuấn) chia sẻ các phần Evaluation và Observability + Bonus.

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
| ---: | --- | --- | --- | --- | --- |
| 1 | **Nguyễn Phi Nhật (Trưởng nhóm)** | `2A202602658` | `nhatng0807@vinuni.edu.vn` | **Pipeline Orchestration & Data Foundation Lead (Phụ trách 2 phần)**: Ingestion `crossref.py`, Cleaning `cleaning.py`, Synthetic Corruption `corruption.py`, điều phối 2 flow `phase1.py` & `corruption_flow.py` | `report/2A202602658_NguyenPhiNhat.md` |
| 2 | **Trần Chí Vĩ** | `2A202602968` | `cuuvi985@gmail.com` | **Evaluation & Benchmark Specialist**: Sinh bộ đề thi 10 câu `testset.py`, kiểm thử mô hình nhúng và đo lường độ chính xác RAG Retrieval `index.py` | `report/2A202602968_TranChiVi.md` |
| 3 | **Hoàng Minh Tuấn** | `2A202602758` | `littlecloudinthevastsky@gmail.com` | **Data Observability & Reporting Specialist**: Data Quality Gate Great Expectations 1.x & Freshness SLA `quality.py`, Báo cáo đối chiếu `reporting.py`, Bonus B1 Dashboard & B2 Self-Healing | `report/2A202602758_HoangMinhTuan.md` |

---

## 📋 Chi Tiết Phân Công & Đóng Góp Cá Nhân

### 1. Nguyễn Phi Nhật — Pipeline Orchestration & Data Foundation Lead (2 Phần việc)

- **Vai trò:** Trưởng nhóm, phụ trách nền tảng dữ liệu (Data Foundation) và điều phối toàn tuyến (Pipeline Orchestration).
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module Ingestion `src/ingestion/crossref.py` với cơ chế Fallback snapshot offline tự động khi mất mạng hoặc dính `429 Too Many Requests`.
  - Triển khai Data Cleaning & Transformation trong `src/ingestion/cleaning.py`: chuẩn hóa văn bản, tính toán `age_days`, ghép nối ngữ cảnh `text_for_embedding`, khử trùng lặp bản ghi theo `paper_id`.
  - Thiết kế bộ tiêm 6 độc tố dữ liệu (Controlled Synthetic Corruption) trong `src/ingestion/corruption.py` và ghi nhận `corruption_log.json`.
  - Điều phối luồng thực thi toàn tuyến Baseline `src/pipelines/phase1.py` và luồng tự phục hồi an toàn (Idempotent Repair) `src/pipelines/corruption_flow.py`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc Pipeline 7 tầng, cơ chế bảo toàn dữ liệu gốc (Raw Preservation) và tính chất bất biến (Idempotent) của hệ thống dữ liệu phục vụ RAG.

### 2. Trần Chí Vĩ — Evaluation & Benchmark Specialist

- **Vai trò:** Phụ trách thiết kế bộ đề thi chuẩn hóa (Ground Truth Benchmark) và đo lường định lượng chất lượng RAG Retrieval.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module sinh bộ dữ liệu đánh giá `src/evaluation/testset.py` gồm 10 câu hỏi bao quát đầy đủ các nhóm nghiệp vụ: `summary`, `authors`, `date`, `categories`.
  - Xác lập ground truth và ánh xạ tài liệu gốc `ground_truth_doc_ids` phục vụ tính toán `retrieval_hit_rate` và `token_f1`.
  - Đo lường và kiểm chứng sự sụt giảm hiệu năng truy vấn của Agent khi chuyển từ dữ liệu sạch sang dữ liệu bị tiêm lỗi (Hit rate giảm từ 100% xuống 50%).
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ hiện tượng Silent Failure của RAG Agent: khi dữ liệu bị lỗi, code không hề quăng Exception đỏ nhưng câu trả lời của AI bị sai lệch hoàn toàn.

### 3. Hoàng Minh Tuấn — Data Observability & Reporting Specialist

- **Vai trò:** Phụ trách thiết lập chốt kiểm dịch dữ liệu tự động (Data Quality Gate), cơ chế báo cáo đối chiếu định lượng và các tính năng thưởng MLOps.
- **Công việc chi tiết đã hoàn thành:**
  - Triển khai trạm kiểm soát dữ liệu bằng **Great Expectations 1.x** (chế độ ephemeral) trong `src/observability/quality.py` với 6 Expectation bắt buộc (row count, non-null, unique, summary length).
  - Xây dựng cơ chế giám sát độ tươi mới **Freshness SLA** (ngưỡng 180 ngày, cảnh báo khi bài báo cũ vượt quá 25%).
  - Lập trình module xuất báo cáo Markdown chuyên nghiệp trong `src/observability/reporting.py`, bao gồm `phase1_report.md` và `corruption_report.md` với bảng đối chiếu 3 trạng thái rõ ràng.
  - Hỗ trợ triển khai **Bonus B1 (Interactive Observability Dashboard)** và **Bonus B2 (Automated Self-Healing Pipeline)**.
- **Điều học được / Đóng góp chính:**
  - Thành thạo cú pháp Great Expectations 1.x mới nhất và hiểu tầm quan trọng của Data Observability trong việc ngăn chặn dữ liệu bẩn lọt vào Vector Store.
