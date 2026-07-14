# %% [markdown]
# # Benchmark — SERP fetch stage
#
# Runs benchmark questions through one or more search engines via the local
# search proxy and persists one JSONL record per (engine, question) under
# `results/`. All engines are fetched interleaved in the same time window,
# which keeps the paired comparison fair on the live web.
#
# Prerequisite — the search proxy running locally (it holds the provider keys):
#
#     cd connectors/unique_search_proxy/unique_search_proxy_client
#     uv run uvicorn unique_search_proxy_client.web.app:app --port 2349
#
# Run cell-by-cell in the interactive window (uses top-level `await`).

# %%
import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

from qa_datasets import QAItem, load_simpleqa
from serp_records import (
    BenchmarkConfig,
    EngineConfig,
    SerpRecord,
    SerpResult,
    append_jsonl,
    check_config,
    completed_ids,
    latest_records,
    results_path,
)
from unique_search_proxy_core.errors import EmptySearchResultsError
from unique_search_proxy_core.schema import WebSearchResults
from unique_search_proxy_sdk import SearchClient, UniqueSearchProxyClient

# %% Parameters
# Each config defines one engine arm; the results filename derives from
# engine + benchmark config, so changing any field starts a fresh file.
ENGINE_CONFIGS = [
    EngineConfig(engine="google", fetch_size=10),
    EngineConfig(engine="brave", fetch_size=10),
    # control arm: single-excerpt snippets — isolates how much of Brave's win
    # is evidence volume (extra_snippets default) vs retrieval quality
    EngineConfig(engine="brave", fetch_size=10, params={"extra_snippets": False}),
    EngineConfig(engine="perplexity", fetch_size=10),
]
BENCHMARK_CONFIG = BenchmarkConfig(
    dataset="simpleqa",
    sample_n=300,
    seed=20260714,
)
PROXY_BASE_URL = "http://localhost:2349"
CONCURRENCY = 8
RESULTS_DIR = Path(__file__).parent / "results"

# %% Load dataset
items = load_simpleqa(sample_n=BENCHMARK_CONFIG.sample_n, seed=BENCHMARK_CONFIG.seed)
print(f"{len(items)} questions loaded, e.g.: {items[0].question!r}")

# %% Search client (provider keys live server-side in the proxy)
transport = UniqueSearchProxyClient(base_url=PROXY_BASE_URL)
search_client = SearchClient(transport=transport)

# %% Fetch loop — resumable: already-fetched items are skipped on re-run
semaphore = asyncio.Semaphore(CONCURRENCY)


async def fetch_serp(
    client: SearchClient, engine_config: EngineConfig, item: QAItem
) -> SerpRecord:
    error: str | None = None
    results: list[SerpResult] = []
    async with semaphore:
        started = time.perf_counter()
        try:
            response = await client.search(
                query=item.question,
                engine=engine_config.engine,
                fetch_size=engine_config.fetch_size,
                **engine_config.params,
            )
            serp = WebSearchResults.model_validate(
                {"results": response.to_dict()["curated"]}
            )
            results = [
                SerpResult(url=r.url, title=r.title, snippet=r.snippet)
                for r in serp.results
            ]
        except EmptySearchResultsError:
            results = []  # a legitimate engine outcome, not a failure:
            # the answerer sees "(no results returned)" and declines
        except Exception as exc:  # noqa: BLE001 — engine failures are benchmark data
            error = f"{type(exc).__name__}: {exc}"
        latency_s = round(time.perf_counter() - started, 3)
    return SerpRecord(
        dataset=item.dataset,
        item_id=item.item_id,
        question=item.question,
        gold_answer=item.gold_answer,
        engine=engine_config.engine,
        fetch_size=engine_config.fetch_size,
        params=engine_config.params,
        fetched_at=datetime.now(UTC).isoformat(),
        latency_s=latency_s,
        error=error,
        results=results,
    )


async def fetch_and_store(
    client: SearchClient, engine_config: EngineConfig, item: QAItem, path: Path
) -> None:
    append_jsonl(path, await fetch_serp(client, engine_config, item))


async def fetch_all(
    client: SearchClient,
    engine_configs: list[EngineConfig],
    benchmark_config: BenchmarkConfig,
    items: list[QAItem],
) -> None:
    tasks = []
    for engine_config in engine_configs:
        path = results_path(RESULTS_DIR, engine_config, benchmark_config)
        check_config(path, engine_config, benchmark_config)
        done = completed_ids(path)
        todo = [item for item in items if item.item_id not in done]
        print(f"{engine_config.slug}: {len(todo)} to fetch ({len(done)} already done)")
        tasks += [fetch_and_store(client, engine_config, item, path) for item in todo]
    await asyncio.gather(*tasks)


# %% Run
await fetch_all(  # noqa: F704 — cellscript, run in the interactive window
    search_client, ENGINE_CONFIGS, BENCHMARK_CONFIG, items
)

# %% Sanity check (latest attempt per item; superseded retries excluded)
for engine_config in ENGINE_CONFIGS:
    records = latest_records(results_path(RESULTS_DIR, engine_config, BENCHMARK_CONFIG))
    errors = [r for r in records if r.error]
    latencies = sorted(r.latency_s for r in records if r.error is None)
    line = f"{engine_config.slug}: {len(records)} items, {len(errors)} errors"
    if latencies:
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        line += f", latency p50={p50:.2f}s p95={p95:.2f}s"
    print(line)
    for record in errors[:3]:
        print(f"  {record.item_id}: {record.error}")
