"""Run configs and JSONL persistence for benchmark runs.

One record per (config, question), appended as attempts complete. Files are
append-only: retries add rows rather than rewriting, and readers dedupe to the
latest attempt per item via :func:`latest_by_item`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def append_jsonl(path: Path, record: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")


def load_jsonl(path: Path, record_cls: type[T]) -> list[T]:
    """Every appended record, including superseded attempts."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [record_cls.model_validate_json(line) for line in f if line.strip()]


def latest_by_item(records: list[T]) -> list[T]:
    """One record per item — the last attempt wins (retries supersede errors).

    Records must carry an ``item_id`` field.
    """
    by_item = {record.item_id: record for record in records}  # type: ignore[attr-defined]
    return sorted(by_item.values(), key=lambda record: record.item_id)  # type: ignore[attr-defined]


class EngineConfig(BaseModel):
    """The engine under test and its parameters. ``params`` holds
    engine-specific request knobs (e.g. Brave's ``extra_snippets``,
    ``country``); they are passed through to the proxy request verbatim."""

    engine: str
    fetch_size: int
    params: dict[str, str | int | bool] = {}

    @property
    def slug(self) -> str:
        base = f"{self.engine}_k{self.fetch_size}"
        knobs = "_".join(
            f"{key}-{str(value).lower()}" for key, value in sorted(self.params.items())
        )
        return f"{base}_{knobs}" if knobs else base


class BenchmarkConfig(BaseModel):
    """The dataset and its sampling parameters."""

    dataset: str
    sample_n: int | None
    seed: int

    @property
    def slug(self) -> str:
        sample = f"n{self.sample_n}" if self.sample_n is not None else "full"
        return f"{self.dataset}_{sample}_seed{self.seed}"


def results_path(
    results_dir: Path, engine: EngineConfig, benchmark: BenchmarkConfig
) -> Path:
    """Filename derives from both configs, so changing any parameter starts a
    fresh file instead of silently resuming onto records fetched under a
    different configuration."""
    return results_dir / f"serp_{engine.slug}_{benchmark.slug}.jsonl"


class SerpResult(BaseModel):
    url: str
    title: str
    snippet: str


class SerpRecord(BaseModel):
    dataset: str
    item_id: str
    question: str
    gold_answer: str
    engine: str
    fetch_size: int
    params: dict[str, str | int | bool] = {}
    fetched_at: str
    latency_s: float
    error: str | None = None
    results: list[SerpResult] = []


def append_record(path: Path, record: SerpRecord) -> None:
    append_jsonl(path, record)


def load_records(path: Path) -> list[SerpRecord]:
    """Every appended SERP record. Prefer :func:`latest_records` for analysis."""
    return load_jsonl(path, SerpRecord)


def latest_records(path: Path) -> list[SerpRecord]:
    """One SERP record per item — the last attempt wins."""
    return latest_by_item(load_records(path))


def completed_ids(path: Path) -> set[str]:
    """Item ids already fetched successfully; errored items are retried."""
    return {r.item_id for r in load_records(path) if r.error is None}


def check_config(path: Path, engine: EngineConfig, benchmark: BenchmarkConfig) -> None:
    """Refuse to resume onto records fetched under a different configuration
    (only possible if files were renamed or edited by hand)."""
    for record in load_records(path):
        found = (record.dataset, record.engine, record.fetch_size, record.params)
        expected = (benchmark.dataset, engine.engine, engine.fetch_size, engine.params)
        if found != expected:
            raise ValueError(
                f"{path.name} contains records from a different run config "
                f"(found {found}, expected {expected}); delete or rename it."
            )
