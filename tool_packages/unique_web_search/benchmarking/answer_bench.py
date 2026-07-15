# %% [markdown]
# # Benchmark — answering stage
#
# Produces one answer per question for every entry in `SEARCH_ENGINES`: each
# engine answers from its fetched SERP snippets only (run `serp_bench.py`
# first); `None` is the no-search / closed-book baseline — same answerer, no
# search results, measuring the model's parametric-knowledge floor.
#
# Prerequisite — Unique gateway credentials: a `unique.env` the toolkit can
# find (`ENVIRONMENT_FILE_PATH`, current directory, or user config dir).
# Without one it falls back to the local dev backend on localhost:8092.
#
# Run cell-by-cell in the interactive window (uses top-level `await`).

# %%
import asyncio
from pathlib import Path

from answering import (
    AnswererConfig,
    AnswerInput,
    AnswerRecord,
    answer_item,
    answered_ids,
    answers_path,
    check_answers_config,
    search_engine_slug,
)
from openai import AsyncOpenAI
from qa_datasets import load_dataset
from serp_records import (
    BenchmarkConfig,
    EngineConfig,
    append_jsonl,
    latest_by_item,
    latest_records,
    load_jsonl,
    results_path,
)
from unique_toolkit.framework_utilities.openai.client import get_async_openai_client

# %% Parameters
# Each search engine is one arm; None means no search (closed-book baseline).
# The answers filename derives from search engine + benchmark + answerer.
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
# First entry is the strongest answerer — the inspector's default view.
ANSWERER_CONFIGS = [
    AnswererConfig(model="AZURE_GPT_54_2026_0305", top_k=10),
    # AnswererConfig(model="AZURE_GPT_41_2025_0414", top_k=10),
]
CONCURRENCY = 4
RESULTS_DIR = Path(__file__).parent / "results"


# %% Input loading: SERP records for engine arms, dataset questions closed-book
def load_inputs(
    engine: EngineConfig | None, benchmark: BenchmarkConfig
) -> list[AnswerInput]:
    if engine is None:
        items = load_dataset(benchmark.dataset, benchmark.sample_n, benchmark.seed)
        return [
            AnswerInput(
                dataset=item.dataset,
                item_id=item.item_id,
                question=item.question,
                gold_answer=item.gold_answer,
                results=None,
            )
            for item in items
        ]
    serps = latest_records(results_path(RESULTS_DIR, engine, benchmark))
    if not serps:
        print(f"WARNING: {engine.slug}: no SERP records — run serp_bench.py first")
    fetch_errors = [r for r in serps if r.error is not None]
    if fetch_errors:
        print(
            f"WARNING: {engine.slug}: skipping {len(fetch_errors)} items whose "
            "fetch errored — finish the fetch stage for a complete run"
        )
    return [
        AnswerInput(
            dataset=r.dataset,
            item_id=r.item_id,
            question=r.question,
            gold_answer=r.gold_answer,
            results=r.results,
        )
        for r in serps
        if r.error is None
    ]


# %% LLM client (Unique gateway; settings resolved from unique.env).
# Built-in exponential backoff handles transient 429s; anything that still
# fails is recorded and retried on the next run.
answer_client = get_async_openai_client().with_options(max_retries=5)

# %% Answer loop — resumable: already-answered items are skipped on re-run
semaphore = asyncio.Semaphore(CONCURRENCY)


async def answer_and_store(
    client: AsyncOpenAI,
    answerer: AnswererConfig,
    slug: str,
    item: AnswerInput,
    path: Path,
) -> None:
    async with semaphore:
        record = await answer_item(client, answerer, slug, item)
    append_jsonl(path, record)


async def answer_all(
    client: AsyncOpenAI,
    search_engines: list[EngineConfig | None],
    benchmark_configs: list[BenchmarkConfig],
    answerers: list[AnswererConfig],
) -> None:
    tasks = []
    for benchmark in benchmark_configs:
        for answerer in answerers:
            print(f"{benchmark.slug} × {answerer.slug}")
            for engine in search_engines:
                slug = search_engine_slug(engine)
                path = answers_path(RESULTS_DIR, slug, benchmark, answerer)
                check_answers_config(path, slug, answerer)
                done = answered_ids(path)
                todo = [
                    item
                    for item in load_inputs(engine, benchmark)
                    if item.item_id not in done
                ]
                print(f"  {slug}: {len(todo)} to answer ({len(done)} already done)")
                tasks += [
                    answer_and_store(client, answerer, slug, item, path)
                    for item in todo
                ]
    await asyncio.gather(*tasks)


# %% Run
await answer_all(  # noqa: F704 — cellscript, run in the interactive window
    answer_client, SEARCH_ENGINES, BENCHMARK_CONFIGS, ANSWERER_CONFIGS
)

# %% Sanity check (latest attempt per item; superseded retries excluded)
for benchmark in BENCHMARK_CONFIGS:
    for answerer in ANSWERER_CONFIGS:
        print(f"{benchmark.slug} × {answerer.slug}")
        for engine in SEARCH_ENGINES:
            slug = search_engine_slug(engine)
            path = answers_path(RESULTS_DIR, slug, benchmark, answerer)
            answers = latest_by_item(load_jsonl(path, AnswerRecord))
            errors = [a for a in answers if a.error]
            declined = [
                a
                for a in answers
                if a.error is None and a.answer.lower().startswith("i don't know")
            ]
            print(
                f"  {slug}: {len(answers)} items, {len(errors)} errors, "
                f"{len(declined)} declined"
            )
            for record in errors[:3]:
                print(f"    {record.item_id}: {record.error}")
