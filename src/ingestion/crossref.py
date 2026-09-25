from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any
import requests

from core.config import Settings
from core.utils import ensure_parent, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", cleaned).strip()


def _format_date(date_data: Any, fallback: str = "2026-01-01") -> str:
    if isinstance(date_data, dict):
        date_parts = date_data.get("date-parts", [])
        if date_parts and isinstance(date_parts[0], list):
            parts = date_parts[0]
            year = parts[0] if len(parts) > 0 else 2026
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        if "date-time" in date_data:
            dt_str = str(date_data["date-time"])
            return dt_str.split("T")[0]
    elif isinstance(date_data, str) and date_data.strip():
        return date_data.split("T")[0].strip()
    return fallback


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into list of PaperRecord objects."""
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = str(item.get("DOI", "")).strip()
        if not paper_id:
            continue

        raw_title = item.get("title", [])
        if isinstance(raw_title, list):
            title = " ".join(str(t).strip() for t in raw_title if str(t).strip())
        else:
            title = str(raw_title).strip()
        title = re.sub(r"\s+", " ", title).strip()

        raw_abstract = item.get("abstract") or item.get("summary") or ""
        summary = _clean_abstract(str(raw_abstract))

        raw_authors = item.get("author", [])
        authors: list[str] = []
        if isinstance(raw_authors, list):
            for auth in raw_authors:
                if isinstance(auth, dict):
                    given = auth.get("given", "").strip()
                    family = auth.get("family", "").strip()
                    full = f"{given} {family}".strip()
                    if full:
                        authors.append(full)
                    elif auth.get("name"):
                        authors.append(str(auth.get("name")).strip())
                elif isinstance(auth, str) and auth.strip():
                    authors.append(auth.strip())
        if not authors:
            authors = ["Unknown Author"]

        raw_subject = item.get("subject", [])
        categories: list[str] = []
        if isinstance(raw_subject, list):
            categories = [str(s).strip() for s in raw_subject if str(s).strip()]
        elif isinstance(raw_subject, str) and raw_subject.strip():
            categories = [raw_subject.strip()]
        if not categories:
            categories = ["Computer Science"]

        primary_category = categories[0]
        published = _format_date(item.get("published"), fallback="2026-01-01")
        updated = _format_date(item.get("updated") or item.get("created"), fallback=published)
        abs_url = str(item.get("URL") or f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch source API records with resilient fallback to local snapshots."""
    records: list[PaperRecord] = []
    payload: dict | None = None

    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "Day10-DataObservabilityLab/1.0 (mailto:student@university.edu)"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                records = parse_crossref_payload(payload)
                if records:
                    write_json(settings.paths.raw_api_response, payload)
        except Exception:
            records = []

    # Fallback to local raw response snapshot if refresh not requested or failed
    if not records and settings.paths.raw_api_response.exists():
        try:
            payload = read_json(settings.paths.raw_api_response)
            records = parse_crossref_payload(payload)
        except Exception:
            records = []

    # Secondary fallback to local raw records snapshot
    if not records and settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)

    # Persist raw records snapshot for idempotent recovery
    if records:
        dict_records = [asdict(r) for r in records]
        write_json(settings.paths.raw_records_json, dict_records)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map into list of `PaperRecord`."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item.get("primary_category", item["categories"][0] if item["categories"] else "General"),
                published=item["published"],
                updated=item.get("updated", item["published"]),
                abs_url=item.get("abs_url", f"https://doi.org/{item['paper_id']}"),
                pdf_url=item.get("pdf_url", f"https://doi.org/{item['paper_id']}"),
                comment=item.get("comment", f"Crossref record {item['paper_id']}"),
            )
        )
    return records
