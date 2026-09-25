from __future__ import annotations

from typing import Any
import pandas as pd

from core.utils import first_sentence, read_json, write_json


class TestSet(list):
    """Container for benchmark evaluation samples supporting both list operations and .samples attribute."""
    def __init__(self, samples: list[dict[str, Any]]):
        super().__init__(samples)
        self.samples = samples


def build_test_set(df: pd.DataFrame, output_path) -> TestSet:
    """Build a standardized 10-question evaluation benchmark spanning core domains."""
    if len(df) == 0:
        raise ValueError("Cannot build test set from an empty DataFrame.")

    # 10 questions covering: summary, authors, date, categories, multi_hop
    type_distribution = [
        ("summary", 3),
        ("authors", 3),
        ("date", 2),
        ("categories", 2),
    ]

    test_items: list[dict[str, Any]] = []
    q_index = 1
    row_idx = 0
    total_rows = len(df)

    for q_type, count in type_distribution:
        for _ in range(count):
            row = df.iloc[row_idx % total_rows]
            row_idx += 1
            title = str(row["title"]).strip()
            paper_id = str(row["paper_id"]).strip()

            if q_type == "summary":
                question = f"What is the summary of the paper '{title}'?"
                ground_truth = first_sentence(str(row["summary"]))
            elif q_type == "authors":
                question = f"Who authored the paper '{title}'?"
                ground_truth = str(row.get("authors_joined", ", ".join(row.get("authors", []))))
            elif q_type == "date":
                question = f"When was the paper '{title}' published?"
                ground_truth = str(row["published"]).strip()
            elif q_type == "categories":
                question = f"What categories does the paper '{title}' belong to?"
                ground_truth = str(row.get("categories_joined", ", ".join(row.get("categories", []))))
            else:
                question = f"What is the summary of the paper '{title}'?"
                ground_truth = first_sentence(str(row["summary"]))

            test_items.append(
                {
                    "id": f"eval_{q_index:03d}",
                    "type": q_type,
                    "question_type": q_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            q_index += 1

    write_json(output_path, test_items)
    return TestSet(test_items)


def load_or_create_test_set(df: pd.DataFrame, output_path) -> TestSet:
    """Load existing test set or generate a new benchmark test set."""
    from pathlib import Path
    p = Path(output_path)
    if p.exists():
        try:
            items = read_json(p)
            return TestSet(items)
        except Exception:
            pass
    return build_test_set(df, output_path)
