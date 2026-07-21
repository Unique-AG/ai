# Web search benchmarking

Compares search engines on QA accuracy for the Google→Brave migration case
(Google Search API retires 2027-01-01; we need evidence for Customer Success
that the alternatives are as good or better). Deliberately minimal: cellscripts
+ small util modules + append-only JSONL files. No CI footprint — the dir is
excluded from deptry and basedpyright in the package `pyproject.toml`.

## Design

- **Staged pipeline with frozen artifacts.** Each stage writes JSONL that the
  next stage reads: SERPs are fetched once per engine (quota-bound, live-web
  snapshot), answering and grading re-run cheaply against frozen evidence.

  ```
  serp_bench.py          answer_bench.py         grade_bench.py       inspect_bench.py
  question → SERP file → answers file          → grades file       → inspect.html
             (per engine) (per engine×answerer)  (…×grader)
  closed-book arm: dataset ─────→ answers file → …    (skips the SERP stage)
  agent arm: agent_bench.py → SERP file → …           (agent engine, replaces the
             (engine grounds & drafts a full answer)   SERP fetch; then identical)
  ```

- **Two ways to fill a SERP file.** SERP engines (google, brave, perplexity) go
  through `serp_bench.py` (`/v1/search`, a result list). *Agent* engines (Vertex
  AI grounding, Grounding with Bing) go through `agent_bench.py`
  (`/v1/agent-search`): the engine grounds *and* drafts a full answer, which is
  stored as the arm's single `SerpResult`. From `answer_bench.py` onward an
  agent arm is just another engine — the **shared answerer condenses the
  engine's grounded answer** into the short graded answer, so the answering
  step is held constant across every arm (realistic agentic setup: our agent
  owns the final answer; the grounding engine is its research tool).

- **Configs define run identity.** Every result filename derives from the
  config objects (`EngineConfig` incl. engine-specific `params`,
  `BenchmarkConfig`, `AnswererConfig`, `GraderConfig`), so changing any
  parameter starts a fresh file and can never silently mix runs; a
  `check_*_config` guard catches hand-renamed files. Each stage loops over
  the full grid: datasets × answerers × engine arms.
- **Grader is pinned.** The judge is always the strongest available model
  (currently GPT 5.4, `AZURE_GPT_54_2026_0305`) regardless of which model
  answers, so grades stay comparable across runs; bump it only when a
  stronger model lands (old grade files stay on disk under the old lineage).
- **Resume everywhere.** Files are append-only; a re-run skips successful
  items and retries errored ones; readers dedupe to the latest attempt per
  item (`latest_by_item`). Declined answers ("I don't know") are successes,
  not errors — they become NOT_ATTEMPTED at grading and are never retried.
- **Failures are data.** Engine errors and empty SERPs are recorded, not
  raised: an empty SERP flows to the answerer as "(no results returned)" and
  grades as NOT_ATTEMPTED.

## Stages

1. **Fetch** (`serp_bench.py`) — runs the dataset through every arm in
   `ENGINE_CONFIGS` via the search-proxy SDK, all engines interleaved in the
   same time window (fair live-web pairing). Engine knobs go in
   `EngineConfig.params` (e.g. `{"extra_snippets": False}` for the Brave
   volume-control arm) and pass through to the proxy request verbatim.

   **Agent fetch** (`agent_bench.py`) — the SERP-file producer for agent engines
   (Vertex AI, Grounding with Bing). Calls `/v1/agent-search`, stores the
   engine's full grounded answer as the arm's single `SerpResult`. Add the same
   `EngineConfig`(s) to
   `SEARCH_ENGINES` in the answer/grade/inspect stages so the arm flows through
   the rest of the pipeline unchanged. Needs the search proxy running, like fetch.
2. **Answer** (`answer_bench.py`) — every answerer in `ANSWERER_CONFIGS`
   (model + `top_k`; list the strongest first — it becomes the inspector's
   default) answers each question from the persisted snippets only, via the
   Unique gateway, for every arm in `SEARCH_ENGINES`. `None` = no search: the
   closed-book baseline measuring that model's parametric-knowledge floor.
3. **Grade** (`grade_bench.py`) — the official SimpleQA grader protocol
   (prompt in `simpleqa_grader_prompt.py`, extracted verbatim from
   openai/simple-evals — do not edit) scores answers CORRECT / INCORRECT /
   NOT_ATTEMPTED with the pinned judge model (`GraderConfig`), blind to which
   engine produced the evidence. Final cells print the per-arm accuracy
   table per dataset × answerer and sample INCORRECT answers.
4. **Inspect** (`inspect_bench.py`, pure read) — writes a self-contained
   `results/inspect.html` with dataset and answerer dropdowns (defaults:
   first dataset, strongest answerer): per-arm summary (accuracy ±CI,
   declines, mean search time, evidence chars/query, errors), paired
   win/loss counts vs the baseline arm, an optional category slice (FreshQA
   fact_type), and a filterable per-item drill-down showing each arm's SERP,
   answer, and grade side by side.

## Running

Fetch and the agent fetch stage need the search proxy running locally (it holds
all provider keys, including Vertex/Google and Bing/Azure AI credentials):

```bash
cd connectors/unique_search_proxy/unique_search_proxy_client
uv run uvicorn unique_search_proxy_client.web.app:app --port 2349
```

Answering/grading need Unique gateway credentials: a `unique.env` the toolkit
can find (`ENVIRONMENT_FILE_PATH`, cwd, or user config dir); without one they
fall back to the local dev backend on localhost:8092.

Run each `*_bench.py` cell-by-cell in the interactive window (they use
top-level `await`), in pipeline order — SERP arms via `serp_bench`, agent arms
via `agent_bench`, then both meet at `answer_bench` → `grade_bench`. The
inspector also runs headless: `uv run python inspect_bench.py`, then open
`results/inspect.html`.

Mind quotas: free-tier Google CSE allows 100 queries/day.

## Datasets (`qa_datasets.py`)

- **SimpleQA** (openai/simple-evals, MIT) — 4,326 items, downloaded and
  cached on first use; subsets are seeded and stable via `item_id`.
- **FreshQA** (freshllms/freshqa, Apache-2.0) — freshness slice: TEST split,
  valid-premise questions only (~376 items, roughly balanced across
  never-/slow-/fast-changing `fact_type`, exposed as `category` for slicing
  in the inspector). Gold answers change as the world does, so the loader
  discovers the newest maintained answer key via the repo README and caches
  it by release date; `item_id` uses the sheet's stable `id`, and multiple
  acceptable answers are folded into one gold string for the grader.
  Caveat: gold answers are frozen into records at fetch/answer time — if a
  new key lands mid-experiment, clear the stale rows rather than mixing.
- **Sampled subsets are pinned.** When `sample_n` selects a subset, the chosen
  questions are written once to `cache/samples/{dataset}_n{sample_n}_seed{seed}.jsonl`
  (mirroring `BenchmarkConfig.slug`) and reused on every later load. This makes
  the exact sample inspectable and keeps all stages of one experiment on the
  same selection even if the FreshQA key drifts. Delete the file to re-sample
  against the current pool; `sample_n=None` (full set) is never pinned.

## Known caveats for reporting

- Results are **snippet-grounded**: the production pipeline crawls result
  pages, so engine deltas here reflect retrieval + snippet quality, not
  end-to-end answer quality. Brave's default `extra_snippets=True` returns
  ~6× Google's evidence volume — the `extra_snippets-false` control arm
  isolates that effect.
- The **agent arms** (Vertex AI, Grounding with Bing) are not strictly the same
  shape as the SERP arms: their "SERP" is a full grounded answer the engine
  drafts, which the shared answerer then condenses (SERP arms instead feed the
  answerer raw snippets). The answerer model is held constant across all arms,
  so this is a fair comparison of *what each engine hands the agent* — but the
  agent arms credit grounded *answering*, the SERP arms credit *retrieval*. One
  mechanism note: the proxy pins both agent engines to a structured
  results-list output schema (no free-form answer field), so `agent_bench.py`
  steers each engine, via `generation_instructions`, to draft one complete
  answer inside that schema and folds it into the evidence blob. Because we no
  longer force the engine to be terse (the answerer handles brevity), the
  schema no longer fights the prompt — but the arm still routes through that
  schema rather than the engine's native free-text output.
- Latency is measured from a dev machine through a local proxy: valid as a
  paired engine comparison, not as absolute production latency.
- English-only (SimpleQA, FreshQA); DE/FR/IT and client-shaped finance
  questions are the next dataset tier.
- Answerers and the grader are all OpenAI-family models; a judge-sensitivity
  pass is additive thanks to lineage-derived filenames.
- FreshQA's false-premise questions (149 of 600) are excluded: their gold
  behaviour is rebutting the premise, which the SimpleQA grader protocol
  does not model (`load_freshqa(include_false_premise=True)` re-adds them).

`cache/` and `results/` are gitignored (fetched web content may carry
copyright/PII); committed summaries can come later with a reporting stage.
