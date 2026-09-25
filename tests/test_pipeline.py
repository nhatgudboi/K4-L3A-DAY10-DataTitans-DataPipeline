from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from core.config import load_settings
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord, parse_crossref_payload
from observability.quality import build_freshness_report, run_data_quality_checks
from pipelines.auto_healing import auto_heal_pipeline


@pytest.fixture
def sample_payload():
    return {
        "status": "ok",
        "message": {
            "total-results": 1,
            "items": [
                {
                    "DOI": "10.1145/3637528.3671801",
                    "title": ["Agentic RAG Test Paper"],
                    "abstract": "<jats:p>This is a valid research abstract exceeding thirty characters in total length.</jats:p>",
                    "author": [{"given": "Alice", "family": "Smith"}],
                    "subject": ["Computer Science"],
                    "published": {"date-parts": [[2026, 5, 20]]},
                    "URL": "https://doi.org/10.1145/3637528.3671801",
                }
            ],
        },
    }


def test_parse_crossref_payload(sample_payload):
    records = parse_crossref_payload(sample_payload)
    assert len(records) == 1
    rec = records[0]
    assert rec.paper_id == "10.1145/3637528.3671801"
    assert rec.title == "Agentic RAG Test Paper"
    assert "jats" not in rec.summary
    assert rec.authors == ["Alice Smith"]
    assert rec.published == "2026-05-20"


def test_build_clean_dataframe(sample_payload):
    records = parse_crossref_payload(sample_payload)
    run_date = datetime(2026, 9, 25, tzinfo=timezone.utc)
    df = build_clean_dataframe(records, run_date)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["paper_id"] == "10.1145/3637528.3671801"
    assert row["age_days"] == 128
    assert "Title: Agentic RAG Test Paper" in row["text_for_embedding"]
    assert "Authors: Alice Smith" in row["text_for_embedding"]


def test_great_expectations_gate():
    settings = load_settings()
    # Create valid synthetic df with 10 rows
    valid_rows = [
        {
            "paper_id": f"10.1234/test_{i}",
            "title": f"Paper Title {i}",
            "summary": "This is a sufficiently long research summary that easily exceeds thirty characters.",
            "text_for_embedding": f"Embed text {i}",
            "age_days": 30,
            "published": "2026-08-01",
        }
        for i in range(10)
    ]
    df_clean = pd.DataFrame(valid_rows)
    clean_res = run_data_quality_checks(df_clean, settings, report_name="test_clean")
    assert clean_res["success"] is True

    # Test failure: inject null paper_id and duplicate
    df_dirty = df_clean.copy()
    df_dirty.loc[0, "summary"] = "Short"
    df_dirty = pd.concat([df_dirty, df_dirty.iloc[[1]]], ignore_index=True)
    dirty_res = run_data_quality_checks(df_dirty, settings, report_name="test_dirty")
    assert dirty_res["success"] is False


def test_freshness_sla():
    settings = load_settings()
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / "freshness.json"
        # 10 rows all fresh (age 30 days)
        df_fresh = pd.DataFrame([{"age_days": 30, "published": "2026-08-01"} for _ in range(10)])
        res_fresh = build_freshness_report(df_fresh, settings, report_path)
        assert res_fresh["is_fresh"] is True
        assert res_fresh["stale_ratio"] == 0.0

        # 10 rows with 8 stale (> 180 days)
        df_stale = pd.DataFrame([{"age_days": 300, "published": "2024-01-01"} for _ in range(10)])
        res_stale = build_freshness_report(df_stale, settings, report_path)
        assert res_stale["is_fresh"] is False
        assert res_stale["stale_ratio"] == 1.0


def test_testset_generation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_path = Path(tmp_dir) / "test_set.json"
        df = pd.DataFrame(
            [
                {
                    "paper_id": f"10.1000/{i}",
                    "title": f"Paper {i}",
                    "summary": f"Summary sentence for paper {i}. More details follow.",
                    "authors_joined": f"Author {i}",
                    "published": "2026-05-01",
                    "categories_joined": "Computer Science",
                }
                for i in range(12)
            ]
        )
        testset = build_test_set(df, test_path)
        assert len(testset) == 10
        types = {t["question_type"] for t in testset}
        assert types == {"summary", "authors", "date", "categories"}
        assert test_path.exists()


def test_corruption_suite():
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_path = Path(tmp_dir) / "corruption_log.json"
        df = pd.DataFrame(
            [
                {
                    "paper_id": f"10.2000/{i}",
                    "title": f"Scientific Paper Number {i} On Autonomous Reasoning",
                    "summary": f"A comprehensive investigation into scholarly AI {i} with long description text.",
                    "authors_joined": f"Author {i}",
                    "categories_joined": "AI",
                    "published": "2026-06-01",
                    "age_days": 50,
                    "text_for_embedding": f"Text {i}",
                }
                for i in range(20)
            ]
        )
        corrupted = corrupt_clean_dataframe(df, log_path)
        assert log_path.exists()
        assert len(corrupted) > 0
        # Check that corruptions altered fields
        assert (corrupted["summary"].str.len() < 30).any() or (corrupted["title"].str.len() < 8).any()
