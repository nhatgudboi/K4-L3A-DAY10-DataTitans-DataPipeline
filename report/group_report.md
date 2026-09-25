# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | **DataTitans** |
| Repository | `https://github.com/nhatgudboi/K4-L3A-Day10-Data-Pipeline-Data-Observability` |
| Ngày hoàn thành | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | **Nguyễn Phi Nhật (Trưởng nhóm)** | `2A202602658` | Data Engineer & Pipeline Lead (Phụ trách 2 phần) | `src/core/config.py`, `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/pipelines/auto_healing.py`, `docs/TEAM.md`, `report/group_report.md`, `report/2A202602658_NguyenPhiNhat.md` |
| 2 | **Trần Chí Vĩ** | `2A202602968` | Retrieval & Evaluation Specialist | `src/retrieval/index.py`, `src/retrieval/llm.py`, `src/evaluation/testset.py`, `data/eval/test_set.json`, `data/chroma/`, `data/embeddings/`, `data/results/*_answers.json`, `data/results/*_metrics.json`, `report/2A202602968_TranChiVi.md` |
| 3 | **Hoàng Minh Tuấn** | `2A202602758` | Observability, CI/CD & Reporting Specialist | `src/observability/quality.py`, `src/observability/reporting.py`, `src/observability/dashboard.py`, `script/run_dashboard.py`, `tests/test_pipeline.py`, `.github/workflows/ci.yml`, `data/quality/`, `data/reports/`, `report/2A202602758_HoangMinhTuan.md` |

---

## 2. Tóm tắt kết quả

Nhóm **DataTitans** đã hoàn thành 100% yêu cầu bài lab Day 10 và triển khai trọn vẹn cả 2 tính năng thưởng nâng cao (Bonus B1: HTML Observability Dashboard và Bonus B2: Automated Self-Healing Pipeline). 

- **Baseline Pipeline:** Thu thập 24 bản ghi học thuật từ Crossref API (kèm cơ chế Fallback offline snapshot tự động), làm sạch và chuẩn hóa text, tính toán `age_days` và `text_for_embedding`, lưu trữ index vào ChromaDB. Trạm kiểm soát chất lượng Great Expectations 1.x và Freshness SLA đều đạt chuẩn tuyệt đối (**PASSED**, **0.0% Stale**). RAG Agent truy vấn đạt **100% Retrieval Hit Rate** và **Mean Token F1 = 1.0000** trên bộ 10 câu hỏi benchmark chuẩn hóa.
- **Tác động của Corruption:** Thử thách tiêm 6 độc tố dữ liệu có kiểm soát (bỏ 20% bản ghi mới nhất, xóa rỗng abstract, chèn chuỗi rác, cắt ngắn title, lùi ngày xuất bản 365 ngày, nhân bản dòng). Kết quả chứng minh thực nghiệm hiện tượng **Silent Failure**: Code hệ thống vẫn trả về `exit code 0` nhưng **Retrieval Hit Rate sụt giảm nghiêm trọng từ 100% xuống 50%**, và **Mean Token F1 rơi từ 1.0000 xuống 0.6506**. Chốt kiểm soát GX 1.x ngay lập tức báo động **FAILED** (vi phạm 3 Expectation) và Freshness SLA báo động **BREACHED (42.9% Stale)**.
- **Mức độ phục hồi sau Repair:** Quy trình tự phục hồi Idempotent Repair tái tạo toàn bộ không gian vector và bảng dữ liệu sạch trực tiếp từ Raw snapshot. Toàn bộ các chỉ số phục hồi 100% về trạng thái hoàn hảo ban đầu (**Hit Rate: 100%**, **F1: 1.0000**, GX 1.x **PASSED**).
- **Giới hạn quan trọng còn lại:** Pipeline hiện hoạt động theo mô hình Micro-batch định kỳ (24 records/batch) với ngưỡng Freshness tĩnh (180 ngày). Trong môi trường Streaming thực tế, hệ thống cần nâng cấp lên Dynamic Thresholding dựa trên phân phối sliding-window và CDC (Change Data Capture).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Nguồn Crossref API (hoặc Local Snapshot data/raw/crossref_response.json)
    ├── 1. Kéo dữ liệu & Bảo toàn bản gốc (Raw Preservation) -> data/raw/crossref_records.json
    ├── 2. Làm sạch & Chuẩn hóa (Transformation)            -> data/clean/papers_clean.csv
    ├── 3. Trạm kiểm soát chất lượng (Quality Gate)         -> Great Expectations 1.x & Freshness SLA
    ├── 4. Nhúng ngữ nghĩa & Lưu Vector (Index)             -> all-MiniLM-L6-v2 + ChromaDB
    ├── 5. Đánh giá chất lượng RAG (Benchmark)              -> 10 câu hỏi test_set.json (Hit Rate, F1)
    ├── 6. Thử thách tiêm độc tố dữ liệu (Corruption)       -> 6 lỗi dữ liệu thực tế (corruption_log.json)
    └── 7. Phục hồi an toàn & Đối chiếu (Repair)            -> Tái tạo từ Raw & Báo cáo đối chiếu 3 trạng thái
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| **Ingestion** | Crossref REST API / `crossref_response.json` | Fetch với retry backoff, bóc tách XML abstract, chuẩn hóa ngày tháng, lưu raw | `data/raw/crossref_records.json` | Nguyễn Phi Nhật |
| **Cleaning** | List `PaperRecord` | Chuẩn hóa text, tính `age_days`, ghép `text_for_embedding`, khử trùng `paper_id` | `data/clean/papers_clean.csv`, `papers_clean.json` | Nguyễn Phi Nhật |
| **Embedding/index** | Clean DataFrame | Nhúng `all-MiniLM-L6-v2`, lập chỉ mục ChromaDB PersistentClient | `data/chroma/`, `papers_embeddings.json` | Trần Chí Vĩ |
| **Evaluation** | Clean DataFrame & Chroma index | Sinh 10 câu hỏi thuộc 4 nhóm (`summary`, `authors`, `date`, `categories`), đo Hit Rate & F1 | `data/eval/test_set.json`, `baseline_metrics.json` | Trần Chí Vĩ |
| **Observability** | DataFrame | Chạy 6 Expectation ephemeral GX 1.x, tính tỷ lệ Stale quá 180 ngày | `baseline_quality_report.json`, `freshness_report.json` | Hoàng Minh Tuấn |
| **Corruption/repair** | Clean DataFrame & Raw records | Tiêm 6 kịch bản lỗi có kiểm soát; Re-run repair bất biến từ Raw snapshot | `corruption_log.json`, `corrupted/repaired_metrics.json` | Nguyễn Phi Nhật |
| **Orchestration** | Toàn bộ các module | Điều phối tuần tự `phase1.py`, `corruption_flow.py`, `auto_healing.py`, xuất báo cáo Markdown & HTML | `phase1_report.md`, `corruption_report.md`, `dashboard.html` | Nhật & Tuấn |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openai` (tương thích OpenRouter) hoặc `mock` |
| `LLM_MODEL` | `google/gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày (ngưỡng cảnh báo > 25% stale) |
| Random seed | 42 |

### Lệnh cài đặt môi trường

Sử dụng `uv`:
```bash
uv sync --extra dev
```

Hoặc kích hoạt virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### Lệnh chạy

1. **Chạy Baseline Pipeline (Pha 1):**
```bash
python script/run_phase1.py
```

2. **Chạy Corruption Flow, Repair & 3-State Comparison (Pha 2):**
```bash
python script/run_corruption_flow.py
```

3. **Chạy Bonus Dashboard & Self-Healing Pipeline:**
```bash
python script/run_dashboard.py
python script/run_auto_healing.py
```

4. **Chạy Unit Tests toàn diện:**
```bash
pytest tests/ -v
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| `python script/run_phase1.py` | Thành công 100% | 2026-09-25 15:18 | `data/reports/phase1_report.md`, `baseline_metrics.json` |
| `python script/run_corruption_flow.py` | Thành công 100% | 2026-09-25 15:20 | `data/reports/corruption_report.md`, `repaired_metrics.json` |
| `pytest tests/ -v` | 6/6 tests Passed | 2026-09-25 15:22 | `tests/test_pipeline.py` (Ingestion, Cleaning, Quality, Index) |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API: `https://api.crossref.org/works` |
| Query/filter | `query=machine+learning`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25 (Kèm offline snapshot fallback tại `data/raw/crossref_records.json`) |
| Số record nhận được | 24 records |
| Cơ chế retry/backoff | 3 lần thử lại, hệ số backoff số mũ (`backoff_factor=1.5`), tự động chuyển sang snapshot nếu API trả mã 429 hoặc timeout |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | `str` | Có | Định danh duy nhất (DOI hoặc hash) | Bắt buộc sinh từ DOI hoặc hash MD5 |
| `title` | `str` | Có | Tiêu đề bài báo khoa học | Strip khoảng trắng, loại bỏ bản ghi nếu rỗng |
| `abstract` | `str` | Có | Tóm tắt nội dung bài báo | Bóc tách XML/HTML tags (`<jats:p>`), chuẩn hóa khoảng trắng |
| `authors` | `list[str]` | Có | Danh sách tên tác giả | Format `"Given Family"`, fallback `["Unknown"]` nếu thiếu |
| `published_date` | `str` | Có | Ngày xuất bản chuẩn ISO 8601 (`YYYY-MM-DD`) | Bóc tách từ `published-online` hoặc `published-print` |
| `categories` | `list[str]` | Có | Lĩnh vực nghiên cứu/subject | Chuẩn hóa chữ thường, fallback `["general"]` |
| `age_days` | `int` | Có | Số ngày tuổi tính từ ngày xuất bản đến hiện tại | Tính toán tự động: `(today - published_date).days` |
| `text_for_embedding` | `str` | Có | Chuỗi ngữ cảnh kết hợp dùng để tạo vector nhúng | Kết hợp Tiêu đề, Tác giả, Ngày, Lĩnh vực và Abstract |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại bỏ XML/HTML tags trong abstract | Validity / Accuracy | 24 | Regex strip `<.*?>`, kiểm tra không còn ký tự HTML |
| Chuẩn hóa ngày tháng ISO 8601 | Consistency / Conformity | 24 | Format `YYYY-MM-DD`, reject các chuỗi ngày dị thường |
| Tính toán `age_days` không âm | Validity | 24 | `age_days = max(0, (now - pub_date).days)` |
| Ghép nối định dạng `text_for_embedding` | Completeness / Usability | 24 | Cấu trúc hóa đầy đủ metadata và nội dung tóm tắt |
| Khử trùng lặp theo `paper_id` | Uniqueness | 24 | `df.drop_duplicates(subset=['paper_id'])` |

**Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:**
- **`paper_id` (Document ID):** Trích xuất trực tiếp từ mã DOI của bài báo (ví dụ: `10.1145/3696410.3714574`). Nếu thiếu DOI, hệ thống băm chuỗi tiêu đề bằng thuật toán MD5 để đảm bảo tính duy nhất và khả năng truy hồi bất biến (Idempotent).
- **`text_for_embedding`:** Được cấu trúc chặt chẽ theo mẫu template giàu ngữ cảnh:  
  `"Title: {title} | Authors: {authors} | Date: {published_date} | Categories: {categories} | Abstract: {abstract}"`  
  Điều này giúp mô hình nhúng (`all-MiniLM-L6-v2`) nắm bắt cả thông tin chuyên đề, tác giả lẫn nội dung học thuật.
- **`age_days`:** Tính bằng hiệu số ngày giữa thời điểm thực thi và `published_date`. Giá trị này là căn cứ định lượng để kiểm tra Freshness SLA (ngưỡng 180 ngày).

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 câu hỏi benchmark chuẩn hóa |
| Các `question_type` | `summary` (4 câu), `authors` (2 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | Ánh xạ trực tiếp từ `paper_id` của tài liệu gốc trong clean dataset |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (chiều vector: 384) |
| Vector store/collection | ChromaDB PersistentClient (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k` | 4 chunks/documents phù hợp nhất |
| LLM provider/model | `google/gemini-2.5-flash` via OpenRouter (hoặc `mock` deterministic) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (10 samples, hash ID cố định) |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Để tuân thủ nguyên lý thực nghiệm khoa học: **Chỉ thay đổi một biến số duy nhất (Data Quality)**. Bằng cách cố định 100% bộ đề thi (`test_set.json`), mô hình nhúng và prompt đánh giá, mọi sự biến thiên về `retrieval_hit_rate` hay `token_f1` hoàn toàn phản ánh trung thực chất lượng của dữ liệu, không bị nhiễu bởi các câu hỏi khác nhau.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/crossref_records.json` | Có | 24 bản ghi thô chuẩn Crossref |
| Cleaned dataset | `data/clean/papers_clean.csv`, `.json` | Có | 24 bản ghi sạch đã biến đổi chuẩn hóa |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Vector store ChromaDB bền vững |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi chuẩn hóa đủ 4 nhóm |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Kết quả đo lường định lượng Baseline |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có | Báo cáo kiểm dịch GX 1.x & Freshness SLA |
| Baseline report | `data/reports/phase1_report.md` | Có | Báo cáo chi tiết nghiệm thu Pha 1 |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | **100.00%** (1.0) | Cả 10/10 câu hỏi truy vấn đều lấy đúng tài liệu ground-truth trong Top 4 |
| `mean_token_f1` | **1.0000** | Độ trùng khớp ngữ nghĩa và từ khóa giữa câu trả lời và ground truth đạt mức tuyệt đối |
| `judge_accuracy` | **100.00%** (1.0) | LLM Judge đánh giá 10/10 câu trả lời chính xác và thỏa mãn thông tin |
| `mean_judge_score` | **5.00 / 5.0** | Điểm số tuyệt đối do giám khảo đánh giá |
| Ragas, nếu có | N/A | Không tích hợp do hệ thống sử dụng framework đánh giá nội bộ theo chuẩn bài lab |

---

## 8. Data quality và freshness

### Quality checks (Great Expectations 1.x)

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `expect_table_row_count_to_be_between` | Completeness | [20, 30] | **PASS** (24 rows) | `baseline_quality_report.json` |
| `expect_column_values_to_not_be_null` (`paper_id`) | Completeness | 0% null | **PASS** (0 null) | `baseline_quality_report.json` |
| `expect_column_values_to_not_be_null` (`title`) | Completeness | 0% null | **PASS** (0 null) | `baseline_quality_report.json` |
| `expect_column_values_to_be_unique` (`paper_id`) | Uniqueness | 100% unique | **PASS** (100% unique) | `baseline_quality_report.json` |
| `expect_column_value_lengths_to_be_between` (`title`) | Validity | min_value=8 | **PASS** (100% valid) | `baseline_quality_report.json` |
| `expect_column_value_lengths_to_be_between` (`abstract`) | Validity | min_value=20 | **PASS** (100% valid) | `baseline_quality_report.json` |

### Freshness SLA

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | `data/clean/papers_clean.csv` |
| Timestamp mới nhất | `2026-03-20` (Ngày xuất bản mới nhất trong batch) |
| Ngưỡng freshness SLA | 180 ngày (Cảnh báo khi tỷ lệ bài báo cũ quá 180 ngày vượt quá 25%) |
| Trạng thái baseline | **HEALTHY** |
| Lý do | Tỷ lệ bản ghi stale (> 180 ngày) là **0.0%** (0/24 bản ghi), hoàn toàn nằm trong giới hạn an toàn SLA (< 25%). |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| **1. Drop Latest** | Bỏ 20% bản ghi mới nhất (indices 20-23) | 4 | Row count giảm còn 20 | Mất tài liệu mới nhất khỏi Vector Index | Đọc lại bản ghi đầy đủ từ `crossref_records.json` |
| **2. Blank Abstract** | Xóa rỗng trường abstract (indices 10-12) | 3 | Vi phạm độ dài abstract min=20 | RAG Agent không tìm thấy ngữ cảnh để tóm tắt | Phục hồi trường abstract gốc từ raw snapshot |
| **3. Inject Noise** | Chèn chuỗi rác lặp vô nghĩa vào abstract | 3 | Vi phạm tính hợp lệ văn bản | Làm loãng embedding, vector bị phân tán | Strip chuỗi rác, nạp lại văn bản gốc |
| **4. Truncate Title** | Cắt ngắn tiêu đề bài báo xuống dưới 8 ký tự | 3 | Vi phạm độ dài title min=8 | Mất từ khóa quan trọng khi tìm kiếm title | Khôi phục tiêu đề nguyên vẹn từ raw snapshot |
| **5. Stale Date** | Lùi ngày xuất bản về quá khứ 365 ngày | 5 | Freshness SLA bị vi phạm (> 25% stale) | Dữ liệu bị đánh dấu "mốc meo/lỗi thời" | Cập nhật lại ngày xuất bản chuẩn từ nguồn Crossref |
| **6. Duplicate Rows** | Nhân bản ngẫu nhiên các dòng để bù đủ 24 bản ghi | 4 | Vi phạm tính duy nhất `paper_id` | Lãng phí bộ nhớ vector, trả về kết quả trùng | Chạy quy tắc khử trùng `drop_duplicates(subset=['paper_id'])` |

**Corruption log:**
- **Đường dẫn:** `data/results/corruption_log.json`
- **Trạng thái:** Có đầy đủ.
- **Nhận xét:** Log ghi nhận chi tiết 100% các kịch bản tiêm lỗi, bao gồm kiểu lỗi, danh sách `affected_indices`, số lượng bản ghi và thông số thực nghiệm.

**Giải thích cách repair đảm bảo tính Idempotent:**
Cơ chế tự phục hồi (Repair) của nhóm không dùng các hàm vá lỗi chắp vá trên file bẩn, mà thực hiện **Idempotent Pipeline Reconstruction**:
1. Đọc lại nguồn chân lý duy nhất (Single Source of Truth) là snapshot gốc được bảo toàn tại `data/raw/crossref_records.json`.
2. Tái thực thi toàn bộ pipeline biến đổi chuẩn mực (`build_clean_dataframe`).
3. Khử trùng lặp và xác thực lại toàn bộ bằng Great Expectations 1.x.
4. Tái tạo bộ vector index sạch trên ChromaDB. Điều này đảm bảo dù chạy bao nhiêu lần, kết quả thu được vẫn luôn hoàn hảo và nhất quán.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | **100.00%** | **50.00%** | **100.00%** | **-50.00%** | **100.00%** | Tác động nghiêm trọng do tài liệu bị drop & abstract rỗng; phục hồi hoàn hảo |
| `mean_token_f1` | **1.0000** | **0.6506** | **1.0000** | **-0.3494** | **100.00%** | Câu trả lời bị nhiễu và thiếu hụt thông tin; lấy lại độ chuẩn xác ban đầu |
| `judge_accuracy` | **100.00%** | **60.00%** | **100.00%** | **-40.00%** | **100.00%** | RAG Agent trả lời sai 4/10 câu hỏi; khôi phục hoàn toàn sau sửa chữa |
| `mean_judge_score` | **5.00** | **3.50** | **5.00** | **-1.50** | **100.00%** | Điểm số chất lượng suy giảm mạnh khi dữ liệu bị thoái hóa |
| Quality checks pass/fail | **PASSED** (6/6) | **FAILED** (3/6) | **PASSED** (6/6) | **-3 checks** | **100.00%** | GX 1.x phát hiện ngay vi phạm null, duplicate và độ dài văn bản |
| Freshness status | **HEALTHY** (0.0% Stale) | **BREACHED** (42.9% Stale) | **HEALTHY** (0.0% Stale) | **+42.9% Stale** | **100.00%** | Hệ thống cảnh báo chính xác khi dữ liệu bị làm cũ nhân tạo |

### Hai kết luận nhân quả được hỗ trợ bởi bằng chứng thực nghiệm:

1. **[Tiêm độc tố dữ liệu] → [Quality Gate báo FAILED] → [RAG Agent suy giảm hiệu năng - Silent Failure]:**
   - *Bằng chứng:* Khi xóa rỗng abstract và cắt ngắn title, Great Expectations ghi nhận vi phạm độ dài tối thiểu (`baseline_quality_report.json` vs `corrupted_quality_report.json`). Đồng thời, không gian vector nhúng bị sai lệch dẫn đến ChromaDB truy vấn sai văn bản, khiến `retrieval_hit_rate` giảm một nửa (từ 100% xuống 50%) và `mean_token_f1` giảm xuống 0.6506 (`corrupted_metrics.json`). Điều này chứng minh rằng dữ liệu xấu trực tiếp làm tê liệt năng lực suy luận của AI dù hệ thống không hề quăng exception code.
2. **[Idempotent Repair từ Raw Snapshot] → [Khôi phục Quality & Freshness] → [Phục hồi 100% năng lực Agent]:**
   - *Bằng chứng:* Khi kích hoạt luồng sửa chữa, hệ thống tái tạo lại dataset từ `data/raw/crossref_records.json`. Kết quả là 6/6 Expectation của GX 1.x vượt qua thành công, Freshness SLA trở lại mức 0.0% Stale (`repaired_quality_report.json`). Trên không gian vector được đánh chỉ mục lại, Agent đạt điểm số tuyệt đối 10/10 câu hỏi chuẩn xác, Hit Rate đạt lại 100% và Token F1 đạt lại 1.0000 (`repaired_metrics.json`).

---

## 11. Vấn đề tích hợp quan trọng

Mô tả sự cố thực tế phát sinh khi kết nối các module trong pipeline và giải pháp xử lý của nhóm:

- **Triệu chứng:** Khi chạy module đánh giá tự động bằng LLM Judge qua cổng OpenRouter (`google/gemini-2.5-flash`), hệ thống liên tục ném ngoại lệ `openai.RateLimitError / APIError: 402 Payment Required: Your account does not have enough credits to generate tokens` mặc dù số dư tài khoản vẫn còn hạn mức khả dụng.
- **Nguyên nhân (Root cause):** Thư viện `langchain_openai.ChatOpenAI` mặc định yêu cầu một lượng "Buffer Credits" tỷ lệ thuận với số token tối đa có thể sinh ra. Khi tham số `max_tokens` không được giới hạn cụ thể, gateway OpenRouter yêu cầu mức ký quỹ credit quá lớn dẫn đến mã lỗi 402.
- **Cách xử lý:** Nhóm đã cấu hình bổ sung tường minh tham số `max_tokens=1000` và `timeout=30.0` ngay trong hàm khởi tạo LLM tại [src/retrieval/llm.py](file:///d:/K4-L3A-Day10-Data-Pipeline-Data-Observability/src/retrieval/llm.py). Đồng thời nhóm bổ sung chế độ `mock` fallback deterministic để pipeline luôn kiểm thử được ngay cả khi ngoại tuyến hoàn toàn.
- **Cách xác minh:** Chạy lại toàn tuyến `python script/run_corruption_flow.py`. Cả 3 trạng thái đánh giá đều chạy mượt mà 10/10 câu hỏi, ghi nhận đầy đủ câu trả lời trong `data/results/baseline_answers.json`, `corrupted_answers.json` và `repaired_answers.json`.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Kích thước batch nhỏ (24 records) | Chưa kiểm chứng được hiệu năng chịu tải khi xử lý hàng triệu bản ghi học thuật | Mở rộng ingestion đa luồng (AsyncIO/Celery) và phân vùng parquet theo tháng/năm |
| Ngưỡng Freshness SLA cố định (180 ngày) | Có thể phát sinh cảnh báo giả (False Positive) với các chuyên ngành có chu kỳ nghiên cứu dài | Áp dụng Dynamic Freshness Thresholding theo từng Category bài báo dựa trên moving median |
| Cơ chế tiêm lỗi dạng Synthetic Batch | Các kịch bản lỗi diễn ra đồng thời thay vì phân tán theo thời gian thực | Thiết kế Chaos Engineering Engine tích hợp hàng đợi Kafka để mô phỏng Data Drift ngẫu nhiên |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`https://github.com/nhatgudboi/K4-L3A-Day10-Data-Pipeline-Data-Observability`).
- [x] Phân công khớp với module, artifact và kết quả thực tế trong `docs/TEAM.md`.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (`python script/run_phase1.py` và `run_corruption_flow.py`).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (`report/2A202602658_NguyenPhiNhat.md`, `TranChiVi.md`, `HoangMinhTuan.md`).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
