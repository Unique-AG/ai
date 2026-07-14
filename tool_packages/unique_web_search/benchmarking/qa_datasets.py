"""Dataset loaders for the web-search benchmark.

Each loader returns a list of :class:`QAItem` with stable ``item_id``s so runs
are resumable and results from different engines can be paired per item.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

import httpx
from pydantic import BaseModel

SIMPLEQA_URL = (
    "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"
)
CACHE_DIR = Path(__file__).parent / "cache"


class QAItem(BaseModel):
    dataset: str
    item_id: str
    question: str
    gold_answer: str


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        response = httpx.get(url, timeout=60.0)
        response.raise_for_status()
        dest.write_bytes(response.content)
    return dest


def load_simpleqa(sample_n: int | None = None, seed: int = 20260714) -> list[QAItem]:
    """Load SimpleQA (openai/simple-evals), optionally a seeded subset.

    ``item_id`` is the row index in the original CSV, so the same id always
    refers to the same question regardless of sampling.
    """
    path = _download(SIMPLEQA_URL, CACHE_DIR / "simple_qa_test_set.csv")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    items = [
        QAItem(
            dataset="simpleqa",
            item_id=f"simpleqa-{index:04d}",
            question=row["problem"],
            gold_answer=row["answer"],
        )
        for index, row in enumerate(rows)
    ]
    if sample_n is not None and sample_n < len(items):
        items = random.Random(seed).sample(items, sample_n)
        items.sort(key=lambda item: item.item_id)
    return items
