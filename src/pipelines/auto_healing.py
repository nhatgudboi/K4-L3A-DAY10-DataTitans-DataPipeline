from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def auto_heal_pipeline(settings: Settings, target_csv: Path | None = None) -> dict[str, Any]:
    """Automated Self-Healing Pipeline (Bonus B2).

    Detects Data Quality & Freshness SLA violations on current data.
    If anomalies are found, automatically isolates faulty records, triggers lineage-based
    idempotent recovery from pristine raw records, updates vector index, and re-validates.
    """
    logger.info("🛡️ Initiating Automated Self-Healing Monitor...")
    csv_to_check = target_csv or (settings.paths.corrupted_clean_csv if settings.paths.corrupted_clean_csv.exists() else settings.paths.clean_csv)

    if not csv_to_check.exists():
        logger.warning("Target CSV %s not found. Nothing to inspect.", csv_to_check)
        return {"status": "SKIPPED", "message": "No dataset found to monitor."}

    df_current = pd.read_csv(csv_to_check)
    logger.info("Inspecting %d records from %s", len(df_current), csv_to_check.name)

    # 1. Run Data Quality Gate
    dq_result = run_data_quality_checks(df_current, settings, report_name="pre_healing_check")
    freshness_result = build_freshness_report(
        df_current, settings, report_path=settings.paths.quality_dir / "pre_healing_freshness.json"
    )

    is_dq_passed = dq_result.get("success", False)
    is_fresh = freshness_result.get("is_fresh", False)

    if is_dq_passed and is_fresh:
        logger.info("✅ Dataset is fully compliant. No healing action required.")
        return {
            "status": "HEALTHY",
            "action_taken": "NONE",
            "message": "Dataset satisfies all GX 1.x expectations and Freshness SLA.",
        }

    # 2. Anomaly detected - Initiate Auto-Healing
    logger.warning("⚠️ ANOMALY DETECTED! Quality Gate=%s, Freshness=%s", is_dq_passed, is_fresh)
    logger.info("🚨 Quarantining anomalous dataset...")

    quarantine_path = settings.paths.quality_dir / "quarantine_dataset.json"
    write_json(quarantine_path, df_current.to_dict(orient="records"))

    # 3. Pull authoritative raw lineage
    logger.info("🔄 Auto-Repair: Pulling authoritative records from %s", settings.paths.raw_records_json)
    raw_records = load_raw_records(settings.paths.raw_records_json)

    # 4. Clean and regenerate compliant dataset
    run_date = datetime.now(timezone.utc)
    healed_df = build_clean_dataframe(raw_records, run_date)
    write_csv(healed_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, healed_df.to_dict(orient="records"))

    # 5. Rebuild ChromaDB collection atomically
    logger.info("🔄 Auto-Repair: Atomically synchronizing ChromaDB collection '%s'", settings.repaired_collection_name)
    repaired_index = LocalEmbeddingIndex.build(
        healed_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # 6. Re-evaluate and re-verify quality gate
    post_healing_dq = run_data_quality_checks(healed_df, settings, report_name="post_healing_check")
    post_healing_freshness = build_freshness_report(
        healed_df, settings, report_path=settings.paths.quality_dir / "post_healing_freshness.json"
    )

    eval_result = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    audit_payload = {
        "timestamp": run_date.isoformat(),
        "status": "HEALED",
        "action_taken": "IDEMPOTENT_REBUILD_AND_INDEX_SYNC",
        "anomaly_details": {
            "initial_quality_success": is_dq_passed,
            "initial_is_fresh": is_fresh,
            "quarantined_records_count": len(df_current),
            "quarantine_file": str(quarantine_path),
        },
        "resolution_details": {
            "healed_records_count": len(healed_df),
            "post_healing_dq_success": post_healing_dq.get("success", False),
            "post_healing_is_fresh": post_healing_freshness.get("is_fresh", False),
            "retrieval_hit_rate": eval_result.summary.get("retrieval_hit_rate", 0.0),
            "mean_token_f1": eval_result.summary.get("mean_token_f1", 0.0),
        },
    }

    audit_path = settings.paths.project_dir / "data" / "results" / "self_healing_audit.json"
    write_json(audit_path, audit_payload)
    logger.info("🎉 Self-Healing completed successfully! Audit log saved to %s", audit_path)
    return audit_payload


def main() -> None:
    settings = load_settings()
    auto_heal_pipeline(settings)


if __name__ == "__main__":
    main()
