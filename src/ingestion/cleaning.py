from __future__ import annotations

from datetime import datetime
import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a standardized DataFrame ready for embedding and indexing."""
    rows: list[dict] = []
    current_date = run_date.date() if isinstance(run_date, datetime) else run_date

    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if normalize_whitespace(a)]
        authors_joined = ", ".join(authors) if authors else "Unknown Author"

        categories = [normalize_whitespace(c) for c in record.categories if normalize_whitespace(c)]
        categories_joined = ", ".join(categories) if categories else "General"
        primary_category = record.primary_category or (categories[0] if categories else "General")

        published_str = record.published.strip()
        try:
            pub_date = datetime.strptime(published_str, "%Y-%m-%d").date()
            age_days = (current_date - pub_date).days
        except Exception:
            age_days = 0

        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_str,
                "updated": record.updated.strip() or published_str,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"], keep="first")
        df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
