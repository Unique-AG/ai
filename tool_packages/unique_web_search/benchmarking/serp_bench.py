# %% [markdown]
# # Benchmark — SERP fetch stage
#
# Runs benchmark questions through one or more engines via the local search
# proxy and persists one JSONL record per (engine, question) under `results/`.
# All engines are fetched interleaved in the same time window, which keeps the
# paired comparison fair on the live web.
#
# Both engine kinds run here: standard search engines (`/v1/search`, a SERP) and
# agent engines (`/v1/agent-search`, one grounded answer folded into a single
# evidence blob — see `agent_evidence.py`). Interleaving them is the point: an
# agent arm compared against a SERP arm fetched days earlier is not a paired
# comparison. `agent_bench.py` fetches agent arms on their own when that is all
# you need.
#
# Prerequisite — the search proxy running locally (it holds the provider keys):
#
#     cd connectors/unique_search_proxy/unique_search_proxy_client
#     uv run uvicorn unique_search_proxy_client.web.app:app --port 2349
#
# Run cell-by-cell in the interactive window (uses top-level `await`).

# %%
import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from itertools import zip_longest
from pathlib import Path

from agent_evidence import (
    AGENT_ENGINES,
    GROUNDING_INSTRUCTIONS,
    grounded_answer_to_evidence,
)
from qa_datasets import QAItem, load_dataset
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
from throttling import EngineThrottle
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import EmptySearchResultsError
from unique_search_proxy_core.schema import WebSearchResults
from unique_search_proxy_sdk import UniqueSearchProxyClient

# %% Parameters
# Each config defines one engine arm; the results filename derives from
# engine + benchmark config, so changing any field starts a fresh file.
ENGINE_CONFIGS = [
    EngineConfig(engine="google", fetch_size=10),
    EngineConfig(engine="brave", fetch_size=10),
    # control arm: single-excerpt snippets — isolates how much of Brave's win
    # is evidence volume (extra_snippets default) vs retrieval quality
    # EngineConfig(engine="brave", fetch_size=10, params={"extra_snippets": False}),
    EngineConfig(engine="perplexity", fetch_size=10),
    # Agent arms (fetched via /v1/agent-search, evidence = one grounded answer,
    # hence `fetch_size=1` — run identity only, not a request knob; Vertex's
    # request body has no fetch-size field). Out of scope for the full-dataset
    # run on cost: measured over 47 sampled items, Vertex grounding fires ~3.2
    # billed Google Search queries per question at $14/1k, so the full 4,326-item
    # SimpleQA arm is ~$215 (~90% of it grounding, not tokens). Enable together
    # with the answer/grade/inspect stages.
    # EngineConfig(
    #     engine="vertexai",
    #     fetch_size=1,
    #     params={"vertexai_model_name": "gemini-3-flash-preview"},
    # ),
    # EngineConfig(engine="bing", fetch_size=5),
    # enterprise-search grounding arm (vs default Google Search grounding):
    # EngineConfig(
    #     engine="vertexai",
    #     fetch_size=1,
    #     params={
    #         "vertexai_model_name": "gemini-3-flash-preview",
    #         "enable_enterprise_search": True,
    #     },
    # ),
]
BENCHMARK_CONFIGS = [
    # full SimpleQA test set (4,326 items) — `sample_n=None` is never pinned to
    # cache/samples/, the seed only names the file. Mind the Google CSE quota:
    # the run is resumable, so re-run after a rate-limit stop to fill the gaps.
    BenchmarkConfig(dataset="simpleqa", sample_n=None, seed=20260714),
    # freshness slice: full valid-premise TEST split (376 items, ~⅓ fast-changing)
    BenchmarkConfig(dataset="freshqa", sample_n=None, seed=20260714),
]
PROXY_BASE_URL = "http://localhost:2349"
# Tenant context sent on every proxy call: the `/v1` routes require it, and
# tagging it `benchmark` keeps bench traffic identifiable in the proxy logs.
BENCH_CONTEXT = RequestContext(
    company_id="benchmark", user_id="benchmark", chat_id="serp-bench"
)
# Concurrency is per engine arm (each has its own throttle), not global.
# Google CSE is the one that throttles in practice, so it gets a smaller slice;
# the agent arms are slow, long-running calls and get one too.
ENGINE_CONCURRENCY = {"google": 4, "vertexai": 4, "bing": 4}
DEFAULT_CONCURRENCY = 8
# Client timeout must outlast the *server's* own budget for the slowest route,
# which is 120s on `/v1/agent-search` (30s on `/v1/search`). Left at the SDK
# default of 60s the client aborts calls the proxy would have completed — in the
# earlier Vertex runs that was every single failure (18 client-side ReadTimeouts,
# no successful call over 60s, i.e. the tail was cut off rather than slow).
CLIENT_TIMEOUT_S = 180.0
RESULTS_DIR = Path(__file__).parent / "results"

# %% Proxy client (provider keys live server-side in the proxy)
# The proxy rejects `/v1` calls without tenant context headers (422), so go
# through the facade — it owns the transport that attaches them. Constructing
# `SearchClient` directly on the facade would leave the context behind. Both
# sub-clients are used: `.search` for SERP arms, `.agent_search` for agent arms.
proxy_client = UniqueSearchProxyClient(
    base_url=PROXY_BASE_URL, context=BENCH_CONTEXT, timeout=CLIENT_TIMEOUT_S
)

# %% Fetch loop — resumable: already-fetched items are skipped on re-run
# One throttle per engine arm: it owns that arm's concurrency, retries its
# retryable failures behind a shared cooldown, and halts the arm if the engine
# stays rate limited (see throttling.py). Other arms are unaffected.
throttles = {
    engine_config.engine: EngineThrottle(
        engine_config.engine,
        concurrency=ENGINE_CONCURRENCY.get(engine_config.engine, DEFAULT_CONCURRENCY),
    )
    for engine_config in ENGINE_CONFIGS
}


async def search_evidence(
    client: UniqueSearchProxyClient, engine_config: EngineConfig, item: QAItem
) -> list[SerpResult]:
    """One proxy call → the evidence this arm stores for the shared answerer.

    A SERP for standard engines; for agent engines the grounded answer folded
    into a single evidence blob, which is what makes the two kinds comparable
    downstream of fetch.
    """
    if engine_config.engine in AGENT_ENGINES:
        agent_response = await client.agent_search.search(
            query=item.question,
            engine=engine_config.engine,
            generation_instructions=GROUNDING_INSTRUCTIONS,
            **engine_config.params,
        )
        return grounded_answer_to_evidence(
            agent_response.answer or "", engine=engine_config.engine
        )
    response = await client.search.search(
        query=item.question,
        engine=engine_config.engine,
        fetch_size=engine_config.fetch_size,
        **engine_config.params,
    )
    serp = WebSearchResults.model_validate({"results": response.to_dict()["curated"]})
    return [
        SerpResult(url=r.url, title=r.title, snippet=r.snippet) for r in serp.results
    ]


async def fetch_serp(
    client: UniqueSearchProxyClient, engine_config: EngineConfig, item: QAItem
) -> SerpRecord:
    error: str | None = None
    results: list[SerpResult] = []
    latency_s = 0.0
    throttle = throttles[engine_config.engine]
    try:
        # `latency_s` is the successful attempt only — cooldown waits and
        # retries must not inflate the engine's measured search time.
        results, latency_s = await throttle.run(
            lambda: search_evidence(client, engine_config, item)
        )
    except EmptySearchResultsError:
        results = []  # a legitimate engine outcome, not a failure:
        # the answerer sees "(no results returned)" and declines
    except Exception as exc:  # noqa: BLE001 — engine failures are benchmark data
        error = f"{type(exc).__name__}: {exc}"
    latency_s = round(latency_s, 3)
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
    client: UniqueSearchProxyClient,
    engine_config: EngineConfig,
    item: QAItem,
    path: Path,
) -> None:
    append_jsonl(path, await fetch_serp(client, engine_config, item))


async def fetch_all(
    client: UniqueSearchProxyClient,
    engine_configs: list[EngineConfig],
    benchmark_configs: list[BenchmarkConfig],
) -> None:
    for throttle in throttles.values():
        throttle.reset()  # a re-run must not inherit the last run's breaker
    per_arm: list[list[Coroutine[None, None, None]]] = []
    for benchmark_config in benchmark_configs:
        items = load_dataset(
            benchmark_config.dataset, benchmark_config.sample_n, benchmark_config.seed
        )
        print(f"{benchmark_config.slug}: {len(items)} questions")
        for engine_config in engine_configs:
            path = results_path(RESULTS_DIR, engine_config, benchmark_config)
            check_config(path, engine_config, benchmark_config)
            done = completed_ids(path)
            todo = [item for item in items if item.item_id not in done]
            print(
                f"  {engine_config.slug}: {len(todo)} to fetch "
                f"({len(done)} already done)"
            )
            per_arm.append(
                [fetch_and_store(client, engine_config, item, path) for item in todo]
            )
    # Round-robin across arms. `gather` starts tasks in list order, so a flat
    # per-arm list would run *every* item of arm 1 before arm 2 — at
    # full-dataset scale (and with one engine rate limited) the arms would be
    # fetched days apart, which breaks the paired live-web comparison.
    tasks = [
        task for column in zip_longest(*per_arm) for task in column if task is not None
    ]
    await asyncio.gather(*tasks)


# %% Run
await fetch_all(  # noqa: F704 — cellscript, run in the interactive window
    proxy_client, ENGINE_CONFIGS, BENCHMARK_CONFIGS
)

# %% Throttling summary — how hard each engine pushed back this run
for engine, throttle in throttles.items():
    state = "HALTED" if throttle.halted else "ok"
    print(
        f"  {engine}: {state}, {throttle.retries} retried attempts, "
        f"{throttle.cooldowns} cooldowns"
    )

# %% Sanity check (latest attempt per item; superseded retries excluded)
for benchmark_config in BENCHMARK_CONFIGS:
    print(benchmark_config.slug)
    for engine_config in ENGINE_CONFIGS:
        records = latest_records(
            results_path(RESULTS_DIR, engine_config, benchmark_config)
        )
        errors = [r for r in records if r.error]
        latencies = sorted(r.latency_s for r in records if r.error is None)
        line = f"  {engine_config.slug}: {len(records)} items, {len(errors)} errors"
        if latencies:
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            line += f", latency p50={p50:.2f}s p95={p95:.2f}s"
        print(line)
        for record in errors[:3]:
            print(f"    {record.item_id}: {record.error}")
