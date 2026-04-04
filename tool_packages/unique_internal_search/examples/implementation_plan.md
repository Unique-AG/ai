# Implementation Plan: Tool Wrappers + Hybrid Search

This document describes the concrete steps to implement the architecture shown in
`tool_architecture.md` and `hybrid_search_flow.md`.

---

## What exists vs. what needs to be built

| Already done | Still needed |
|---|---|
| `InternalSearchService` v2 in `service_v2.py` | Hybrid search path in `service_v2.py` |
| `InternalSearchState.metadata_filter_override` (UNSET sentinel) | `InternalSearchToolV2` in `tool_v2.py` |
| `_resolve_search_scope()` (KB-only / chat-only) | `EarningCallsInternalSearchTool` in `earnings_calls/` |
| `InternalSearchDeps` (kb_service, chat_service) | Exports in `__init__.py` |

---

## Step 1 — Hybrid search in `service_v2.py`

`_resolve_search_scope()` currently upgrades to `chat_only=True` whenever
`scope_to_chat_on_upload=True` and files are present. Extend it to a tri-state.

### New return type: `tuple[bool, bool, dict | None]` → `(chat_only, hybrid, metadata_filter)`

```python
async def _resolve_search_scope(self) -> tuple[bool, bool, dict | None]:
    chat_only = self._state.chat_only
    hybrid = False

    if not chat_only and self._config.scope_to_chat_on_upload:
        if await self._has_uploaded_files():
            if self._config.scope_ids:      # non-empty → hybrid
                hybrid = True
            else:                            # no KB scope → chat-only (existing behaviour)
                chat_only = True

    metadata_filter = None if chat_only else self._effective_metadata_filter
    return chat_only, hybrid, metadata_filter
```

Decision: `scope_ids=[]` and `scope_ids=None` are both falsy — hybrid only when a real
KB scope exists.

### New method: `_search_single_query_hybrid()`

```python
async def _search_single_query_hybrid(
    self,
    *,
    query: str,
    metadata_filter: dict | None,
    content_ids: list[str] | None,
) -> SearchStringResult:
    """Run KB and chat-file searches in parallel, then interleave round-robin."""
    deps = self._dependencies
    if deps.chat_service is None:
        raise RuntimeError("chat_service is required for hybrid search")

    kb_chunks, chat_chunks = await asyncio.gather(
        deps.kb_service.search_content_chunks_async(
            search_string=query,
            search_type=self._config.search_type,
            limit=self._config.limit,
            reranker_config=self._config.reranker_config,
            search_language=self._config.search_language,
            scope_ids=self._config.scope_ids,
            metadata_filter=metadata_filter,   # KB leg uses the filter
            content_ids=content_ids,
            score_threshold=self._config.score_threshold,
        ),
        deps.chat_service.search_content_chunks_async(
            search_string=query,
            search_type=self._config.search_type,
            limit=self._config.limit,
            reranker_config=self._config.reranker_config,
            search_language=self._config.search_language,
            scope_ids=self._config.scope_ids,
            metadata_filter=None,              # chat leg never uses a metadata filter
            content_ids=content_ids,
            score_threshold=self._config.score_threshold,
        ),
    )

    merged = interleave_search_results_round_robin([
        SearchStringResult(query=query, chunks=kb_chunks),
        SearchStringResult(query=query, chunks=chat_chunks),
    ])
    return SearchStringResult(query=query, chunks=[c for r in merged for c in r.chunks])
```

### Update `run()`

Unpack the 3-tuple and route each query to the correct search method:

```python
chat_only, hybrid, metadata_filter = await self._resolve_search_scope()

results = await asyncio.gather(
    *[
        self._search_single_query_hybrid(
            query=query,
            metadata_filter=metadata_filter,
            content_ids=self._state.content_ids,
        )
        if hybrid
        else self._search_single_query(
            query=query,
            metadata_filter=metadata_filter,
            chat_only=chat_only,
            content_ids=self._state.content_ids,
        )
        for query in search_queries
    ],
    return_exceptions=True,
)
```

Also add `"hybrid": hybrid` to `debug_info` in the returned `InternalSearchResult`.

---

## Step 2 — `InternalSearchToolV2` in `tool_v2.py`

New file. Holds `InternalSearchService` (v2) **by composition**, not inheritance.
Subscribes to `service.progress_publisher` to drive `_message_step_logger` UI updates.

```python
# tool_packages/unique_internal_search/unique_internal_search/tool_v2.py

class InternalSearchToolV2(Tool[InternalSearchConfig]):
    name = "InternalSearch"

    def __init__(
        self,
        config: InternalSearchConfig,
        event: BaseEvent,
        tool_progress_reporter=None,
    ) -> None:
        super().__init__(config, event, tool_progress_reporter)
        settings = (
            UniqueSettings.from_chat_event(event)
            if isinstance(event, ChatEvent)
            else None
        )
        self._service = InternalSearchService.from_config(config)
        if settings:
            self._service.bind_settings(settings)
        self._active_message_log: MessageLog | None = None
        self._service.progress_publisher.subscribe(self._on_progress)

    async def _on_progress(self, msg: InternalSearchProgressMessage) -> None:
        _STAGE_MSG = {
            SearchStage.RETRIEVING:     "_Retrieving search results_",
            SearchStage.RESORTING:      "_Resorting search results_",
            SearchStage.POSTPROCESSING: "_Postprocessing search results_",
        }
        if msg.stage == SearchStage.COMPLETED:
            self._active_message_log = (
                await self._message_step_logger.display_search_in_message_log(
                    active_message_log=self._active_message_log,
                    search_queries=msg.search_queries,
                    chunks=msg.chunks,
                    search_type="InternalSearch",
                    status=MessageLogStatus.COMPLETED,
                )
            )
        elif msg.stage in _STAGE_MSG:
            self._active_message_log = (
                await self._message_step_logger.display_search_in_message_log(
                    active_message_log=self._active_message_log,
                    progress_message=_STAGE_MSG[msg.stage],
                    search_queries=msg.search_queries,
                    search_type="InternalSearch",
                    status=MessageLogStatus.RUNNING,
                )
            )

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        if (
            tool_call.arguments is None
            or not isinstance(tool_call.arguments, dict)
            or "search_string" not in tool_call.arguments
        ):
            self.logger.error("Tool call arguments are missing or invalid")
            return ToolCallResponse(
                id=tool_call.id, name=self.name, content_chunks=[], debug_info={}
            )

        raw = tool_call.arguments["search_string"]
        search_strings: list[str] = [raw] if isinstance(raw, str) else list(raw)

        self._service.reset_state()
        self._service.state.search_queries = search_strings
        # language_model_info: left None for now → falls back to config.max_tokens_for_sources.
        # Follow-up: expose set_language_model_info() for the orchestrator to call pre-run.

        result = await self._service.run()
        chunks = append_metadata_in_chunks(
            result.chunks, self.config.metadata_chunk_sections
        )
        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content_chunks=chunks,
            debug_info=result.debug_info,
            system_reminder=self.config.experimental_features
                .tool_response_system_reminder.get_reminder_prompt,
        )

    def tool_description(self) -> LanguageModelToolDescription: ...
    def tool_description_for_system_prompt(self) -> str: ...
    def tool_format_information_for_system_prompt(self) -> str: ...
    def evaluation_check_list(self) -> list[EvaluationMetricName]: ...
    def get_evaluation_checks_based_on_tool_response(self, ...) -> ...: ...


ToolFactory.register_tool(InternalSearchToolV2, InternalSearchConfig)
```

`tool_description()` is identical to the v1 tool — copy as-is.

Note: The legacy `tool_progress_reporter.notify_from_tool_call` path (guarded by
`enable_new_answers_ui_un_14411`) is **omitted** — v2 targets the new UI event-bus
path exclusively.

---

## Step 3 — `EarningCallsInternalSearchTool` in `earnings_calls/`

New subdirectory. Same composition pattern; adds an optional `ticker` parameter that
sets `state.metadata_filter_override` without touching any private service state.

### Files to create

```
earnings_calls/__init__.py      (empty)
earnings_calls/config.py
earnings_calls/tool.py
```

### `earnings_calls/config.py`

```python
from pydantic import Field
from unique_internal_search.config import InternalSearchConfig


class EarningsCallsSearchConfig(InternalSearchConfig):
    ticker_param_description: str = Field(
        default=(
            "Stock ticker symbol to scope the search (e.g. 'AAPL'). "
            "Leave empty to search all tickers."
        ),
        description="Description shown to the LLM for the ticker parameter.",
    )
```

### `earnings_calls/tool.py` (key parts)

```python
class EarningCallsInternalSearchTool(Tool[EarningsCallsSearchConfig]):
    name = "EarningsCallsSearch"

    def __init__(self, config, event, tool_progress_reporter=None):
        # identical init pattern to InternalSearchToolV2
        ...

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        ...
        self._service.reset_state()
        self._service.state.search_queries = search_strings

        ticker: str | None = tool_call.arguments.get("ticker")
        if ticker:
            # Clean per-call override — no private mutation anywhere
            self._service.state.metadata_filter_override = {
                "ticker": {"equals": ticker}
            }
        # If no ticker: metadata_filter_override stays UNSET (reset_state default)
        # → _effective_metadata_filter falls back to context.chat.metadata_filter

        result = await self._service.run()
        ...

    def tool_description(self) -> LanguageModelToolDescription:
        # Adds optional `ticker: str | None` field alongside search_string
        EarningsCallsToolInput = create_model(
            "EarningsCallsToolInput",
            search_string=...,
            ticker=(str | None, Field(default=None, description=self.config.ticker_param_description)),
        )
        ...


ToolFactory.register_tool(EarningCallsInternalSearchTool, EarningsCallsSearchConfig)
```

---

## Step 4 — Shared progress helper

`_on_progress` is identical in both tools. Extract before finalising to avoid copy-paste:

```python
# In tool_v2.py or a shared _progress_mixin.py
async def _handle_search_progress(
    msg: InternalSearchProgressMessage,
    message_step_logger: MessageStepLogger,
    active_log: MessageLog | None,
    search_type: str = "InternalSearch",
) -> MessageLog | None:
    ...
```

---

## Step 5 — Exports

```python
# unique_internal_search/__init__.py
from unique_internal_search.tool_v2 import InternalSearchToolV2
from unique_internal_search.earnings_calls.tool import EarningCallsInternalSearchTool
from unique_internal_search.earnings_calls.config import EarningsCallsSearchConfig
```

---

## Implementation order

1. `service_v2.py` — hybrid scope + `_search_single_query_hybrid` + update `run()`
2. `tool_v2.py` — composition tool
3. `earnings_calls/` — config + tool
4. `__init__.py` — exports

---

## Key design decisions

| Concern | Decision |
|---|---|
| `scope_ids=[]` vs `None` in hybrid check | Both falsy; hybrid only when non-empty list |
| Chat leg metadata filter | Always `None` — metadata filters are KB-specific |
| `UNSET` vs `None` override | `None` = explicit no filter; `UNSET` = use context default. `reset_state()` restores `UNSET` each call — no bleed-through |
| Duplicate name `"InternalSearch"` | `ToolFactory` last-writer-wins. During migration, name v2 `"InternalSearchV2"` if both must coexist |
| `language_model_info` | `None` for now → follows up with orchestrator setter |
| Legacy `tool_progress_reporter` path | Omitted from v2 — targets new UI path only |

---

## Verification checklist

- [ ] `pytest tests/` green before any new code
- [ ] `test_service_v2_hybrid.py` — parametrise `_resolve_search_scope` over all scope combinations; assert hybrid calls both services; assert chat leg always passes `metadata_filter=None`
- [ ] `test_tool_v2.py` — mock service; assert `reset_state()` called before `state.search_queries` set; assert `append_metadata_in_chunks` applied; verify progress stage → logger mapping
- [ ] `test_earnings_calls_tool.py` — ticker present → override set; no ticker → `UNSET`; empty string → `UNSET`; tool schema includes optional `ticker` field
- [ ] Smoke: `python -c "from unique_internal_search import InternalSearchToolV2, EarningCallsInternalSearchTool"`
