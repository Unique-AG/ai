"""Answering stage: an LLM answers each question from the fetched snippets
only — or from nothing, for the closed-book baseline arm. Answers feed the
grading stage, which scores them against gold answers.

LLM calls go through the Unique gateway via the toolkit's OpenAI client
(same architecture as the unique_benchmarking repo's LLM client).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel
from serp_records import BenchmarkConfig, EngineConfig, SerpResult, load_jsonl

CLOSED_BOOK_SLUG = "closedbook"


def search_engine_slug(engine: EngineConfig | None) -> str:
    """Answers come from a search engine's SERPs, or from no search at all
    (the closed-book baseline)."""
    return engine.slug if engine is not None else CLOSED_BOOK_SLUG


SERP_SYSTEM_PROMPT = """\
You answer questions using ONLY the provided web search results.
Give the shortest answer that fully answers the question (a name, date, \
number, or short phrase).
If the search results do not contain the information needed, reply exactly: \
I don't know.
Do not use your own knowledge; do not guess."""

CLOSED_BOOK_SYSTEM_PROMPT = """\
Answer the question from your own knowledge.
Give the shortest answer that fully answers the question (a name, date, \
number, or short phrase).
If you do not know the answer, reply exactly: I don't know."""


class AnswererConfig(BaseModel):
    """The answering model and how much of the SERP it sees."""

    model: str
    top_k: int  # results included in the prompt (ignored for closed-book)

    @property
    def slug(self) -> str:
        return f"{self.model.lower()}_top{self.top_k}"


class AnswerInput(BaseModel):
    """One question to answer; ``results=None`` means closed-book."""

    dataset: str
    item_id: str
    question: str
    gold_answer: str
    results: list[SerpResult] | None


class AnswerRecord(BaseModel):
    dataset: str
    item_id: str
    question: str
    gold_answer: str
    search_engine: str  # engine slug or "closedbook"
    model: str
    top_k: int
    answer: str
    answered_at: str
    latency_s: float
    error: str | None = None


def answers_path(
    results_dir: Path,
    search_engine: str,
    benchmark: BenchmarkConfig,
    answerer: AnswererConfig,
) -> Path:
    """Filename derives from search engine + benchmark + answerer, so changing
    any parameter starts a fresh file."""
    name = f"answers_{search_engine}_{benchmark.slug}_{answerer.slug}.jsonl"
    return results_dir / name


def build_user_prompt(
    question: str, results: list[SerpResult] | None, top_k: int
) -> str:
    if results is None:
        return f"Question: {question}"
    blocks = [
        f"[{rank}] {result.title}\n{result.snippet}"
        for rank, result in enumerate(results[:top_k], start=1)
    ]
    joined = "\n\n".join(blocks) if blocks else "(no results returned)"
    return f"Search results:\n\n{joined}\n\nQuestion: {question}"


async def answer_item(
    client: AsyncOpenAI,
    answerer: AnswererConfig,
    search_engine: str,
    item: AnswerInput,
) -> AnswerRecord:
    system_prompt = (
        CLOSED_BOOK_SYSTEM_PROMPT if item.results is None else SERP_SYSTEM_PROMPT
    )
    user_prompt = build_user_prompt(item.question, item.results, answerer.top_k)
    error: str | None = None
    answer = ""
    started = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=answerer.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = (response.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 — recorded, then retried on re-run
        error = f"{type(exc).__name__}: {exc}"
    return AnswerRecord(
        dataset=item.dataset,
        item_id=item.item_id,
        question=item.question,
        gold_answer=item.gold_answer,
        search_engine=search_engine,
        model=answerer.model,
        top_k=answerer.top_k,
        answer=answer,
        answered_at=datetime.now(UTC).isoformat(),
        latency_s=round(time.perf_counter() - started, 3),
        error=error,
    )


def answered_ids(path: Path) -> set[str]:
    """Item ids already answered successfully; errored items are retried."""
    return {r.item_id for r in load_jsonl(path, AnswerRecord) if r.error is None}


def check_answers_config(
    path: Path, search_engine: str, answerer: AnswererConfig
) -> None:
    """Refuse to resume onto answers produced under a different configuration."""
    for record in load_jsonl(path, AnswerRecord):
        found = (record.search_engine, record.model, record.top_k)
        expected = (search_engine, answerer.model, answerer.top_k)
        if found != expected:
            raise ValueError(
                f"{path.name} contains answers from a different config "
                f"(found {found}, expected {expected}); delete or rename it."
            )
