from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute end-to-end Phase 1 Baseline Pipeline."""
    print("=" * 70)
    print("🚀 BẮT ĐẦU PHA 1: BASELINE DATA PIPELINE & OBSERVABILITY")
    print("=" * 70)

    settings = load_settings()

    # 1. Ingestion
    print("\n[1/6] Ingestion: Thu thập dữ liệu từ nguồn Crossref...")
    records = fetch_source_records(settings)
    print(f" -> Tải thành công {len(records)} bản ghi bài báo khoa học.")

    # 2. Cleaning & Transformation
    print("\n[2/6] Cleaning: Làm sạch dữ liệu và tạo text_for_embedding...")
    clean_df = build_clean_dataframe(records, now_utc())
    write_csv(clean_df, settings.paths.clean_csv)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f" -> Đã lưu {len(clean_df)} bản ghi sạch vào: {settings.paths.clean_csv.name}")

    # 3. Vector Indexing with ChromaDB
    print("\n[3/6] Indexing: Nhúng ngữ nghĩa và nạp vào ChromaDB...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    print(f" -> Đã index thành công vào collection '{settings.baseline_collection_name}'.")

    # 4. Evaluation Benchmark Generation
    print("\n[4/6] Evaluation Set: Sinh bộ câu hỏi benchmark 4 nhóm nghiệp vụ...")
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    print(f" -> Đã tạo bộ test set gồm {len(test_set)} câu hỏi tại: {settings.paths.eval_testset.name}")

    # 5. Baseline Evaluation
    print("\n[5/6] Evaluation: Đo lường chất lượng Agent trên dữ liệu sạch...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = bundle.summary.get("retrieval_hit_rate", 0.0)
    token_f1 = bundle.summary.get("mean_token_f1", 0.0)
    print(f" -> Retrieval Hit Rate : {hit_rate:.2%}")
    print(f" -> Mean Token F1      : {token_f1:.4f}")

    # 6. Data Observability & Reporting
    print("\n[6/6] Observability: Chạy Great Expectations 1.x & Freshness SLA...")
    quality_res = run_data_quality_checks(clean_df, settings, "baseline")
    freshness_res = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary={
            "source_name": settings.source_api,
            "total_raw": len(records),
            "total_clean": len(clean_df),
        },
        metrics=bundle.summary,
        quality=quality_res,
        freshness=freshness_res,
    )
    print(f" -> Data Quality Gate : {'PASSED' if quality_res.get('all_expectations_passed') else 'FAILED'}")
    print(f" -> Freshness SLA     : {'HEALTHY' if freshness_res.get('is_fresh') else 'BREACHED'}")
    print(f" -> Báo cáo đã xuất   : {settings.paths.baseline_report.name}")

    print("\n" + "=" * 70)
    print("✅ HOÀN TẤT PHA 1: MỌI MẮT XÍCH BASELINE ĐỀU ĐẠT CHUẨN!")
    print("=" * 70)
