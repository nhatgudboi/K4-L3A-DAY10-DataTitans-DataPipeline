from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any
import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Great Expectations 1.x checks and Freshness SLA checks on the dataframe."""
    results_detail: list[dict[str, Any]] = []
    gx_success = True

    try:
        context = gx.get_context(mode="ephemeral")
        source_name = f"papers_source_{report_name}_{int(time.time() * 1000)}"
        data_source = context.data_sources.add_pandas(name=source_name)
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})

        expectations = [
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
            gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
            gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
        ]

        for exp in expectations:
            val_res = batch.validate(exp)
            success = bool(val_res.success)
            if not success:
                gx_success = False
            results_detail.append(
                {
                    "expectation_type": exp.__class__.__name__,
                    "success": success,
                    "kwargs": exp.model_dump() if hasattr(exp, "model_dump") else str(exp),
                }
            )
    except Exception as exc:
        # Fallback pure-python verification if GX ephemeral context fails
        row_count_ok = 5 <= len(df) <= 5000
        paper_id_not_null = bool(df["paper_id"].notna().all() if "paper_id" in df else False)
        title_not_null = bool(df["title"].notna().all() if "title" in df else False)
        embed_not_null = bool(df["text_for_embedding"].notna().all() if "text_for_embedding" in df else False)
        paper_id_unique = bool(df["paper_id"].is_unique if "paper_id" in df else False)
        summary_len_ok = bool((df["summary"].astype(str).str.len() >= 30).all() if "summary" in df else False)

        gx_success = all([row_count_ok, paper_id_not_null, title_not_null, embed_not_null, paper_id_unique, summary_len_ok])
        results_detail = [
            {"expectation_type": "ExpectTableRowCountToBeBetween", "success": row_count_ok},
            {"expectation_type": "ExpectColumnValuesToNotBeNull_paper_id", "success": paper_id_not_null},
            {"expectation_type": "ExpectColumnValuesToNotBeNull_title", "success": title_not_null},
            {"expectation_type": "ExpectColumnValuesToNotBeNull_text_for_embedding", "success": embed_not_null},
            {"expectation_type": "ExpectColumnValuesToBeUnique_paper_id", "success": paper_id_unique},
            {"expectation_type": "ExpectColumnValueLengthsToBeBetween_summary", "success": summary_len_ok},
            {"error_note": f"GX engine warning: {exc}"},
        ]

    # Freshness evaluation
    freshness = build_freshness_report(
        df=df,
        settings=settings,
        report_path=settings.paths.quality_dir / f"{report_name}_freshness_report.json",
    )

    report_payload = {
        "report_name": report_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(df),
        "all_expectations_passed": gx_success,
        "is_fresh": freshness["is_fresh"],
        "success": gx_success and freshness["is_fresh"],
        "stale_ratio": freshness["stale_ratio"],
        "results": results_detail,
        "freshness": freshness,
    }

    out_path = (
        settings.paths.baseline_quality_report
        if report_name == "baseline"
        else settings.paths.corrupted_quality_report
        if report_name == "corrupted"
        else settings.paths.quality_dir / f"{report_name}_quality_report.json"
    )
    write_json(out_path, report_payload)

    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Calculate freshness statistics and verify against SLA threshold."""
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
        }
        write_json(report_path, report)
        return report

    latest_published = str(df["published"].max()) if "published" in df else "N/A"
    oldest_published = str(df["published"].min()) if "published" in df else "N/A"

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df else 0
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    # Freshness SLA: alert if stale ratio exceeds 25% (0.25)
    is_fresh = stale_ratio <= 0.25

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }

    write_json(report_path, report)
    return report
