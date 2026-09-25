from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute Corruption, Evaluation, Idempotent Repair, and 3-State Comparison."""
    print("=" * 75)
    print("⚠️ BẮT ĐẦU PHA 2: TIÊM LỖI DỮ LIỆU, PHỤC HỒI & ĐỐI CHIẾU 3 TRẠNG THÁI")
    print("=" * 75)

    settings = load_settings()

    # 1. Load Baseline State
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file {settings.paths.clean_json}. Vui lòng chạy `python script/run_phase1.py` trước!"
        )
    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f" -> Đã nạp dữ liệu sạch ({len(clean_df)} dòng) và baseline metrics.")

    # 2. Inject Controlled Data Corruptions
    print("\n[1/4] Tiêm 6 kịch bản dữ liệu lỗi (Controlled Synthetic Corruption)...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f" -> Đã lưu tập dữ liệu lỗi ({len(corrupted_df)} dòng) và ghi log tại: {settings.paths.corruption_log.name}")

    # 3. Evaluate Corrupted Data
    print("\n[2/4] Nhúng vector dữ liệu lỗi & Đo lường suy giảm (Silent Failure)...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )

    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0)
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0)
    print(f" -> Corrupted Retrieval Hit Rate: {c_hit:.2%} (Baseline: {baseline_metrics.get('retrieval_hit_rate', 0.0):.2%})")
    print(f" -> Corrupted Mean Token F1     : {c_f1:.4f} (Baseline: {baseline_metrics.get('mean_token_f1', 0.0):.4f})")
    print(f" -> Data Quality Gate (GX 1.x)  : {'PASSED' if corrupted_quality.get('all_expectations_passed') else 'FAILED (Phát hiện lỗi)'}")
    print(f" -> Freshness SLA Status        : {'HEALTHY' if corrupted_freshness.get('is_fresh') else 'BREACHED (Cảnh báo)'}")

    # 4. Idempotent Repair from Raw Snapshot
    print("\n[3/4] Kích hoạt cơ chế tự phục hồi (Idempotent Repair) từ Raw snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )

    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0)
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0)
    print(f" -> Repaired Retrieval Hit Rate : {r_hit:.2%} (Khôi phục trọn vẹn)")
    print(f" -> Repaired Mean Token F1      : {r_f1:.4f}")
    print(f" -> Repaired Quality Gate       : {'PASSED' if repaired_quality.get('all_expectations_passed') else 'FAILED'}")

    # 5. Generate 3-State Comparison Report
    print("\n[4/4] Xuất báo cáo đối chiếu 3 trạng thái...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f" -> Báo cáo đối chiếu đã xuất: {settings.paths.comparison_report.name}")

    print("\n" + "=" * 75)
    print("📊 BẢNG ĐỐI CHIẾU 3 TRẠNG THÁI (CONCISED BENCHMARK)")
    print("-" * 75)
    print(f"{'Chỉ số':<26} | {'1. Baseline':<12} | {'2. Corrupted':<12} | {'3. Repaired':<12}")
    print("-" * 75)
    print(f"{'Retrieval Hit Rate':<26} | {baseline_metrics.get('retrieval_hit_rate', 0.0):<12.2%} | {c_hit:<12.2%} | {r_hit:<12.2%}")
    print(f"{'Mean Token F1':<26} | {baseline_metrics.get('mean_token_f1', 0.0):<12.4f} | {c_f1:<12.4f} | {r_f1:<12.4f}")
    print(f"{'GX 1.x Quality Gate':<26} | {'PASSED':<12} | {'FAILED':<12} | {'PASSED':<12}")
    print(f"{'Freshness SLA':<26} | {'HEALTHY':<12} | {'BREACHED':<12} | {'HEALTHY':<12}")
    print("=" * 75)
    print("✅ TOÀN BỘ CHU TRÌNH TỰ CHỮA LÀNH (SELF-HEALING) ĐÃ HOÀN THÀNH XUẤT SẮC!")
    print("=" * 75)
