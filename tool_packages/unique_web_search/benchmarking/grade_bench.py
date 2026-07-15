# %% [markdown]
# # Benchmark — grading stage
#
# Scores every answer produced by `answer_bench.py` as CORRECT / INCORRECT /
# NOT_ATTEMPTED against the gold answer, using the official SimpleQA grader
# protocol with a pinned judge model. The final cell prints the per-arm
# accuracy table — the headline result.
#
# Prerequisite — Unique gateway credentials (same as the answering stage).
#
# Run cell-by-cell in the interactive window (uses top-level `await`).

# %%
import asyncio
import math
from pathlib import Path

from answering import AnswererConfig, AnswerRecord, answers_path, search_engine_slug
from grading import (
    GraderConfig,
    GradeRecord,
    check_grades_config,
    grade_item,
    graded_ids,
    grades_path,
)
from openai import AsyncOpenAI
from serp_records import (
    BenchmarkConfig,
    EngineConfig,
    append_jsonl,
    latest_by_item,
    load_jsonl,
)
from unique_toolkit.framework_utilities.openai.client import get_async_openai_client

# %% Parameters — must match the answering run being graded
SEARCH_ENGINES: list[EngineConfig | None] = [
    EngineConfig(engine="google", fetch_size=10),
    EngineConfig(engine="brave", fetch_size=10),
    EngineConfig(engine="brave", fetch_size=10, params={"extra_snippets": False}),
    EngineConfig(engine="perplexity", fetch_size=10),
    None,  # no search — closed-book baseline
]
BENCHMARK_CONFIGS = [
    BenchmarkConfig(dataset="simpleqa", sample_n=300, seed=20260714),
    BenchmarkConfig(dataset="freshqa", sample_n=None, seed=20260714),
]
ANSWERER_CONFIGS = [
    AnswererConfig(model="AZURE_GPT_54_2026_0305", top_k=10),
    # AnswererConfig(model="AZURE_GPT_41_2025_0414", top_k=10),
]
# Judge pinned to the strongest available model (currently GPT 5.5) for every
# run — never varied per experiment, so grades stay comparable across runs.
GRADER_CONFIG = GraderConfig(model="AZURE_GPT_54_2026_0305")
CONCURRENCY = 4
RESULTS_DIR = Path(__file__).parent / "results"


# %% Input loading: successfully answered items per arm
def load_answers(
    engine: EngineConfig | None, benchmark: BenchmarkConfig, answerer: AnswererConfig
) -> list[AnswerRecord]:
    slug = search_engine_slug(engine)
    path = answers_path(RESULTS_DIR, slug, benchmark, answerer)
    answers = latest_by_item(load_jsonl(path, AnswerRecord))
    if not answers:
        print(f"WARNING: {slug}: no answers — run answer_bench.py first")
    errors = [a for a in answers if a.error is not None]
    if errors:
        print(
            f"WARNING: {slug}: skipping {len(errors)} items whose answering "
            "errored — finish the answering stage for a complete run"
        )
    return [a for a in answers if a.error is None]


# %% LLM client (Unique gateway; settings resolved from unique.env)
grade_client = get_async_openai_client().with_options(max_retries=5)

# %% Grade loop — resumable: already-graded items are skipped on re-run
semaphore = asyncio.Semaphore(CONCURRENCY)


async def grade_and_store(
    client: AsyncOpenAI, grader: GraderConfig, item: AnswerRecord, path: Path
) -> None:
    async with semaphore:
        record = await grade_item(client, grader, item)
    append_jsonl(path, record)


async def grade_all(
    client: AsyncOpenAI,
    search_engines: list[EngineConfig | None],
    benchmark_configs: list[BenchmarkConfig],
    answerers: list[AnswererConfig],
    grader: GraderConfig,
) -> None:
    tasks = []
    for benchmark in benchmark_configs:
        for answerer in answerers:
            print(f"{benchmark.slug} × {answerer.slug}")
            for engine in search_engines:
                slug = search_engine_slug(engine)
                path = grades_path(RESULTS_DIR, slug, benchmark, answerer, grader)
                check_grades_config(path, slug, grader)
                done = graded_ids(path)
                todo = [
                    item
                    for item in load_answers(engine, benchmark, answerer)
                    if item.item_id not in done
                ]
                print(f"  {slug}: {len(todo)} to grade ({len(done)} already done)")
                tasks += [grade_and_store(client, grader, item, path) for item in todo]
    await asyncio.gather(*tasks)


# %% Run
await grade_all(  # noqa: F704 — cellscript, run in the interactive window
    grade_client, SEARCH_ENGINES, BENCHMARK_CONFIGS, ANSWERER_CONFIGS, GRADER_CONFIG
)

# %% Accuracy table — the headline result
for benchmark in BENCHMARK_CONFIGS:
    for answerer in ANSWERER_CONFIGS:
        print(f"\n{benchmark.slug} × {answerer.slug}")
        print(
            f"{'arm':<32} {'n':>4} {'correct':>8} {'incorrect':>10} "
            f"{'not_attempted':>14} {'accuracy':>12}"
        )
        for engine in SEARCH_ENGINES:
            slug = search_engine_slug(engine)
            path = grades_path(RESULTS_DIR, slug, benchmark, answerer, GRADER_CONFIG)
            grades = [
                g
                for g in latest_by_item(load_jsonl(path, GradeRecord))
                if g.error is None
            ]
            n = len(grades)
            if n == 0:
                print(f"{slug:<32} {'-':>4}  (no grades)")
                continue
            correct = sum(g.grade == "CORRECT" for g in grades)
            incorrect = sum(g.grade == "INCORRECT" for g in grades)
            not_attempted = sum(g.grade == "NOT_ATTEMPTED" for g in grades)
            accuracy = correct / n
            # normal-approximation 95% CI, in percentage points
            half_width = 1.96 * math.sqrt(accuracy * (1 - accuracy) / n) * 100
            print(
                f"{slug:<32} {n:>4} {correct:>8} {incorrect:>10} "
                f"{not_attempted:>14} {accuracy:>7.1%} ±{half_width:.1f}pp"
            )

# %% Drill-down: a few disagreements worth eyeballing (INCORRECT answers)
for benchmark in BENCHMARK_CONFIGS:
    for answerer in ANSWERER_CONFIGS:
        for engine in SEARCH_ENGINES:
            slug = search_engine_slug(engine)
            path = grades_path(RESULTS_DIR, slug, benchmark, answerer, GRADER_CONFIG)
            grades = latest_by_item(load_jsonl(path, GradeRecord))
            wrong = [g for g in grades if g.grade == "INCORRECT"][:3]
            if wrong:
                print(f"\n{benchmark.slug} × {answerer.slug} × {slug} — INCORRECT:")
            for g in wrong:
                print(f"  Q: {g.question[:70]!r}")
                print(f"  answered: {g.answer[:60]!r} | gold: {g.gold_answer[:40]!r}")
