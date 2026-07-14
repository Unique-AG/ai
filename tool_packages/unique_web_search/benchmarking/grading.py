"""Grading stage: scores answers CORRECT / INCORRECT / NOT_ATTEMPTED against
gold answers using the official SimpleQA grader protocol (prompt extracted
verbatim into ``simpleqa_grader_prompt.py``).

The grader sees only question, gold target, and predicted answer — never
which search engine produced the evidence, so it is blind by construction.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path

from answering import AnswererConfig, AnswerRecord
from openai import AsyncOpenAI
from pydantic import BaseModel
from serp_records import BenchmarkConfig, load_jsonl
from simpleqa_grader_prompt import GRADER_TEMPLATE

GRADE_BY_LETTER = {"A": "CORRECT", "B": "INCORRECT", "C": "NOT_ATTEMPTED"}


class GraderConfig(BaseModel):
    """The judge model, pinned per result set."""

    model: str

    @property
    def slug(self) -> str:
        return self.model.lower()


class GradeRecord(BaseModel):
    dataset: str
    item_id: str
    question: str
    gold_answer: str
    search_engine: str
    answer: str
    grade: str  # CORRECT | INCORRECT | NOT_ATTEMPTED ("" when errored)
    grader_model: str
    graded_at: str
    latency_s: float
    error: str | None = None


def grades_path(
    results_dir: Path,
    search_engine: str,
    benchmark: BenchmarkConfig,
    answerer: AnswererConfig,
    grader: GraderConfig,
) -> Path:
    """Filename derives from the full lineage: engine + benchmark + answerer
    + grader, so changing any parameter starts a fresh file."""
    name = (
        f"grades_{search_engine}_{benchmark.slug}_{answerer.slug}_{grader.slug}.jsonl"
    )
    return results_dir / name


async def grade_item(
    client: AsyncOpenAI, grader: GraderConfig, item: AnswerRecord
) -> GradeRecord:
    prompt = GRADER_TEMPLATE.format(
        question=item.question,
        target=item.gold_answer,
        predicted_answer=item.answer,
    )
    error: str | None = None
    grade = ""
    started = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=grader.model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (response.choices[0].message.content or "").strip()
        match = re.search(r"(A|B|C)", text)
        if match:
            grade = GRADE_BY_LETTER[match.group(1)]
        else:
            error = f"unparseable grader response: {text[:100]!r}"
    except Exception as exc:  # noqa: BLE001 — recorded, then retried on re-run
        error = f"{type(exc).__name__}: {exc}"
    return GradeRecord(
        dataset=item.dataset,
        item_id=item.item_id,
        question=item.question,
        gold_answer=item.gold_answer,
        search_engine=item.search_engine,
        answer=item.answer,
        grade=grade,
        grader_model=grader.model,
        graded_at=datetime.now(UTC).isoformat(),
        latency_s=round(time.perf_counter() - started, 3),
        error=error,
    )


def graded_ids(path: Path) -> set[str]:
    """Item ids already graded successfully; errored items are retried."""
    return {r.item_id for r in load_jsonl(path, GradeRecord) if r.error is None}


def check_grades_config(path: Path, search_engine: str, grader: GraderConfig) -> None:
    """Refuse to resume onto grades produced under a different configuration."""
    for record in load_jsonl(path, GradeRecord):
        found = (record.search_engine, record.grader_model)
        expected = (search_engine, grader.model)
        if found != expected:
            raise ValueError(
                f"{path.name} contains grades from a different config "
                f"(found {found}, expected {expected}); delete or rename it."
            )
