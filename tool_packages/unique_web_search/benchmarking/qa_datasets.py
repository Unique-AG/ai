"""Dataset loaders for the web-search benchmark.

Each loader returns a list of :class:`QAItem` with stable ``item_id``s so runs
are resumable and results from different engines can be paired per item.

Sampled subsets are pinned to ``cache/samples/`` on first use (see
:func:`_sample`) so the exact questions are inspectable and every stage of one
experiment reuses the same selection even if the underlying key changes.
"""

from __future__ import annotations

import csv
import random
import re
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

SIMPLEQA_URL = (
    "https://openaipublic.blob.core.windows.net/simple-evals/simple_qa_test_set.csv"
)
FRESHQA_README_URL = (
    "https://raw.githubusercontent.com/freshllms/freshqa/main/README.md"
)
CACHE_DIR = Path(__file__).parent / "cache"
SAMPLES_DIR = CACHE_DIR / "samples"


class QAItem(BaseModel):
    dataset: str
    item_id: str
    question: str
    gold_answer: str
    category: str | None = None  # dataset-defined slice, e.g. FreshQA fact_type


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        response = httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        dest.write_bytes(response.content)
    return dest


def _sample(
    items: list[QAItem], dataset: str, sample_n: int | None, seed: int
) -> list[QAItem]:
    """Return the full set, or a seeded subset pinned to ``cache/samples/``.

    Sampling only reduces the set when ``sample_n`` is smaller than the pool.
    The chosen subset is cached under a name that mirrors
    :attr:`BenchmarkConfig.slug` (``{dataset}_n{sample_n}_seed{seed}.jsonl``),
    so the exact questions are inspectable and reusable, and every stage of one
    experiment sees the same frozen selection — important for FreshQA, whose
    answer key (and thus the pool and gold answers) drifts over time. Delete the
    file to re-sample against the current pool.
    """
    if sample_n is None or sample_n >= len(items):
        return items
    cache_path = SAMPLES_DIR / f"{dataset}_n{sample_n}_seed{seed}.jsonl"
    if cache_path.exists():
        with cache_path.open(encoding="utf-8") as f:
            sampled = [QAItem.model_validate_json(line) for line in f if line.strip()]
        print(f"sample: reusing {cache_path.name} ({len(sampled)} items)")
        return sampled
    sampled = random.Random(seed).sample(items, sample_n)
    sampled.sort(key=lambda item: item.item_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as f:
        f.writelines(item.model_dump_json() + "\n" for item in sampled)
    print(f"sample: wrote {cache_path.name} ({len(sampled)} items)")
    return sampled


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
    return _sample(items, "simpleqa", sample_n, seed)


def _freshqa_latest_csv() -> Path:
    """Resolve the newest maintained answer key via the repo README (first
    spreadsheet link), cached by release date — the snapshot stays pinned
    until a newer key is released."""
    try:
        response = httpx.get(FRESHQA_README_URL, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        cached = sorted(CACHE_DIR.glob("freshqa_*.csv"))
        if cached:
            print(
                f"WARNING: FreshQA README unreachable ({exc}); using {cached[-1].name}"
            )
            return cached[-1]
        raise
    match = re.search(
        r"\[FreshQA ([A-Za-z]+ \d{1,2}, \d{4})\]"
        r"\(https://docs\.google\.com/spreadsheets/d/([\w-]+)",
        response.text,
    )
    if match is None:
        raise ValueError("no FreshQA spreadsheet link found in the repo README")
    released = datetime.strptime(match.group(1), "%B %d, %Y").date()
    export_url = (
        f"https://docs.google.com/spreadsheets/d/{match.group(2)}/export?format=csv"
    )
    return _download(export_url, CACHE_DIR / f"freshqa_{released:%Y%m%d}.csv")


def load_freshqa(
    sample_n: int | None = None,
    seed: int = 20260714,
    include_false_premise: bool = False,
) -> list[QAItem]:
    """Load FreshQA (freshllms/freshqa), TEST split, latest answer key.

    Gold answers change as the world does, so the loader pulls the newest
    released key (cached by release date; ``item_id`` uses the stable ``id``
    column, so pairing survives key updates). Multiple acceptable answers are
    folded into ``gold_answer`` for the grader. False-premise questions are
    excluded by default — their gold behaviour is rebutting the premise,
    which the SimpleQA grader protocol does not model. ``category`` carries
    the fact_type (never-/slow-/fast-changing).
    """
    path = _freshqa_latest_csv()
    print(f"FreshQA answer key: {path.name}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header_at = next(i for i, row in enumerate(rows) if row and row[0] == "id")
    header = rows[header_at]
    items = []
    for values in rows[header_at + 1 :]:
        record = dict(zip(header, values))
        if not record.get("id") or record["split"] != "TEST":
            continue
        if record["false_premise"].upper() == "TRUE" and not include_false_premise:
            continue
        answers = [
            value.strip()
            for key, value in record.items()
            if key.startswith("answer_") and value and value.strip()
        ]
        if not answers:
            continue
        gold = answers[0]
        if len(answers) > 1:
            gold += " (also acceptable: " + "; ".join(answers[1:]) + ")"
        items.append(
            QAItem(
                dataset="freshqa",
                item_id=f"freshqa-{int(record['id']):04d}",
                question=record["question"],
                gold_answer=gold,
                category=record["fact_type"],
            )
        )
    return _sample(items, "freshqa", sample_n, seed)


DATASET_LOADERS = {"simpleqa": load_simpleqa, "freshqa": load_freshqa}


def load_dataset(dataset: str, sample_n: int | None, seed: int) -> list[QAItem]:
    """Dispatch to the loader named by ``BenchmarkConfig.dataset``."""
    return DATASET_LOADERS[dataset](sample_n=sample_n, seed=seed)
