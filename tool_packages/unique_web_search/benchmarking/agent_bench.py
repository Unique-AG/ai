# %% [markdown]
# # Benchmark — agent-engine fetch stage (Vertex AI grounding)
#
# Fetches the "SERP evidence" for *agent* engines (Vertex AI grounding) that
# `serp_bench.py` cannot drive — an agent engine grounds *and* drafts a full
# answer in one call, via the `/v1/agent-search` proxy endpoint rather than
# `/v1/search`. This stage stores Vertex's grounded answer as the arm's single
# `SerpResult`, so the **shared answerer** (`answer_bench.py`) then condenses it
# into the short graded answer — the same answerer model as every other arm.
#
# This mirrors an agentic setup where our agent owns the final user-facing
# answer and delegates grounded research to Vertex: Vertex supplies the full,
# nuanced grounded answer; our answerer produces the clean short answer that is
# graded. The answering step is thus held constant across all arms, so deltas
# reflect Vertex's grounded-answer quality, not answerer differences.
#
# Add the SAME `EngineConfig`(s) used here to `SEARCH_ENGINES` in
# `answer_bench.py`, `grade_bench.py` and `inspect_bench.py`; from those stages'
# point of view Vertex is just another engine whose SERP file already exists.
#
# Prerequisite — the search proxy running locally (it holds the provider keys,
# including Vertex/Google credentials):
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
from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput
from unique_search_proxy_sdk import AgentSearchClient, UniqueSearchProxyClient

# %% Parameters
# Vertex arms — fetched here, not in serp_bench.py. `fetch_size=1` because the
# stored evidence is one grounded answer; the model choice lives in `params` so
# it is part of the run identity (changing it starts a fresh file).
ENGINE_CONFIGS = [
    EngineConfig(
        engine="vertexai",
        fetch_size=1,
        params={"vertexai_model_name": "gemini-3-flash-preview"},
    ),
    # Grounding with Bing (Azure AI Projects agent) — same agent-search path as
    # Vertex; `fetch_size=5` is the server's default grounding-result count.
    EngineConfig(engine="bing", fetch_size=5),
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
    BenchmarkConfig(dataset="simpleqa", sample_n=300, seed=20260714),
    BenchmarkConfig(dataset="freshqa", sample_n=None, seed=20260714),
]
PROXY_BASE_URL = "http://localhost:2349"
CONCURRENCY = 4
RESULTS_DIR = Path(__file__).parent / "results"

# generation_instructions that steer Vertex to draft one COMPLETE grounded
# answer. This aligns with the proxy's comprehensive output schema (no terseness
# conflict); the shared answerer handles brevity downstream.
GROUNDING_INSTRUCTIONS = """\
You are a grounded research agent. Using web search, answer the user's question \
as completely and accurately as possible. Return a SINGLE result whose \
`detailed_answer` is your full answer — include every fact, date, name, and \
figure needed for it to be correct and unambiguous. Put the discrete supporting \
facts in `key_facts` and cite your main source in `source_url`/`source_title`. \
If web search does not contain the answer, say so in `detailed_answer`."""

# %% Agent search client (provider keys live server-side in the proxy)
transport = UniqueSearchProxyClient(base_url=PROXY_BASE_URL)
agent_client = AgentSearchClient(transport=transport)


# %% Vertex's grounded answer → one SerpResult the shared answerer will condense
def grounded_answer_to_evidence(raw_answer: str) -> list[SerpResult]:
    """The proxy pins Vertex to a results-list schema; fold it into a single
    evidence blob (the full grounded answer). Falls back to raw text if the
    payload is not the expected JSON (e.g. a provider that answers in prose)."""
    try:
        parsed = AgentSearchOutput.model_validate_json(raw_answer)
    except ValueError:
        text = raw_answer.strip()
        return (
            [SerpResult(url="", title="Vertex AI grounded answer", snippet=text)]
            if text
            else []
        )
    blocks = [
        "\n".join([item.detailed_answer.strip(), *(f"- {k}" for k in item.key_facts)])
        for item in parsed.results
        if item.detailed_answer.strip() or item.key_facts
    ]
    answer_text = "\n\n".join(block.strip() for block in blocks).strip()
    if not answer_text:
        return []
    primary_url = parsed.results[0].source_url if parsed.results else ""
    return [
        SerpResult(
            url=primary_url, title="Vertex AI grounded answer", snippet=answer_text
        )
    ]


# %% Fetch loop — resumable: already-fetched items are skipped on re-run
semaphore = asyncio.Semaphore(CONCURRENCY)


async def fetch_serp(
    client: AgentSearchClient, engine_config: EngineConfig, item: QAItem
) -> SerpRecord:
    error: str | None = None
    results: list[SerpResult] = []
    async with semaphore:
        started = time.perf_counter()
        try:
            response = await client.search(
                query=item.question,
                engine=engine_config.engine,
                generation_instructions=GROUNDING_INSTRUCTIONS,
                **engine_config.params,
            )
            results = grounded_answer_to_evidence(response.answer or "")
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
    client: AgentSearchClient, engine_config: EngineConfig, item: QAItem, path: Path
) -> None:
    append_jsonl(path, await fetch_serp(client, engine_config, item))


async def fetch_all(
    client: AgentSearchClient,
    engine_configs: list[EngineConfig],
    benchmark_configs: list[BenchmarkConfig],
) -> None:
    tasks = []
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
            tasks += [
                fetch_and_store(client, engine_config, item, path) for item in todo
            ]
    await asyncio.gather(*tasks)


# %% Run
await fetch_all(  # noqa: F704 — cellscript, run in the interactive window
    agent_client, ENGINE_CONFIGS, BENCHMARK_CONFIGS
)

# %% Sanity check (latest attempt per item; superseded retries excluded)
for benchmark_config in BENCHMARK_CONFIGS:
    print(benchmark_config.slug)
    for engine_config in ENGINE_CONFIGS:
        records = latest_records(
            results_path(RESULTS_DIR, engine_config, benchmark_config)
        )
        errors = [r for r in records if r.error]
        empty = [r for r in records if r.error is None and not r.results]
        latencies = sorted(r.latency_s for r in records if r.error is None)
        line = (
            f"  {engine_config.slug}: {len(records)} items, {len(errors)} errors, "
            f"{len(empty)} empty"
        )
        if latencies:
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            line += f", latency p50={p50:.2f}s p95={p95:.2f}s"
        print(line)
        for record in errors[:3]:
            print(f"    {record.item_id}: {record.error}")
