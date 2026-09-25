from __future__ import annotations

from typing import Any
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject 6 realistic data corruption anomalies into clean dataframe."""
    corrupted = df.copy()
    corruption_log: list[dict[str, Any]] = []

    total_rows = len(corrupted)
    if total_rows < 6:
        raise ValueError(f"DataFrame too small ({total_rows} rows) to inject 6 corruption types reliably.")

    # 1. Drop latest records: drop ~20% of records (e.g. 5 out of 24)
    num_to_drop = max(1, int(round(total_rows * 0.20)))
    dropped_records = corrupted.iloc[:num_to_drop][["paper_id", "title"]].to_dict(orient="records")
    corrupted = corrupted.iloc[num_to_drop:].reset_index(drop=True)
    corruption_log.append(
        {
            "scenario": "drop_latest_records",
            "description": f"Dropped {num_to_drop} newest records (~20%) to simulate ingestion lag/data loss.",
            "affected_count": num_to_drop,
            "details": dropped_records,
        }
    )

    # 2. Blank summary: clear summary on 2 rows
    blank_indices = [0, 1] if len(corrupted) > 2 else [0]
    blanked_details = []
    for idx in blank_indices:
        p_id = corrupted.at[idx, "paper_id"]
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0
        blanked_details.append(p_id)
    corruption_log.append(
        {
            "scenario": "blank_summary",
            "description": "Erased paper summary to simulate scraping failure or missing abstract payload.",
            "affected_count": len(blank_indices),
            "details": blanked_details,
        }
    )

    # 3. Inject noise: append corrupt characters to summary on 2 rows
    noise_indices = [2, 3] if len(corrupted) > 4 else [1]
    noise_details = []
    noise_str = " @@#$!&*^ CORRUPTED_GARBAGE_NOISE_INJECTION_FAIL %%% "
    for idx in noise_indices:
        p_id = corrupted.at[idx, "paper_id"]
        corrupted.at[idx, "summary"] = noise_str + str(corrupted.at[idx, "summary"])
        corrupted.at[idx, "summary_chars"] = len(corrupted.at[idx, "summary"])
        noise_details.append(p_id)
    corruption_log.append(
        {
            "scenario": "inject_noise",
            "description": "Injected random garbage noise into abstract to corrupt vector embeddings.",
            "affected_count": len(noise_indices),
            "details": noise_details,
        }
    )

    # 4. Truncate title: truncate title < 8 characters on 2 rows
    trunc_indices = [4, 5] if len(corrupted) > 6 else [2]
    trunc_details = []
    for idx in trunc_indices:
        p_id = corrupted.at[idx, "paper_id"]
        corrupted.at[idx, "title"] = str(corrupted.at[idx, "title"])[:5]
        trunc_details.append(p_id)
    corruption_log.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated paper title to under 8 characters to violate length constraints.",
            "affected_count": len(trunc_indices),
            "details": trunc_details,
        }
    )

    # 5. Stale date: push published date back by 365 days on 40% of rows to breach Freshness SLA (>25% stale)
    stale_count = max(3, int(round(len(corrupted) * 0.40)))
    stale_details = []
    for idx in range(stale_count):
        p_id = corrupted.at[idx, "paper_id"]
        corrupted.at[idx, "published"] = "2024-01-01"
        corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
        stale_details.append(p_id)
    corruption_log.append(
        {
            "scenario": "stale_date",
            "description": f"Aged {stale_count} papers backwards by 365 days to intentionally violate Freshness SLA (>25%).",
            "affected_count": stale_count,
            "details": stale_details,
        }
    )

    # 6. Duplicate rows: duplicate records to trigger uniqueness violation while maintaining row count
    dup_rows = corrupted.iloc[:num_to_drop].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    corruption_log.append(
        {
            "scenario": "duplicate_rows",
            "description": f"Duplicated {len(dup_rows)} records into dataset to breach ExpectColumnValuesToBeUnique constraint.",
            "affected_count": len(dup_rows),
            "details": dup_rows["paper_id"].tolist(),
        }
    )

    # Rebuild text_for_embedding reflecting corrupted fields
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda r: (
            f"Title: {r['title']}\n"
            f"Authors: {r['authors_joined']}\n"
            f"Published: {r['published']}\n"
            f"Categories: {r['categories_joined']}\n"
            f"Summary: {r['summary']}"
        ),
        axis=1,
    )

    write_json(output_log_path, corruption_log)
    return corrupted
