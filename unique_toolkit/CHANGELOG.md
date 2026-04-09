# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.69.5] - 2026-04-09
- Add pytest coverage for OpenAI streaming (`StreamingPatternReplacer`, Chat Completions / Responses stream pipelines, batch reference normalization)

## [1.69.4] - 2026-04-08
- Make `LanguageModelMessage` an abstract base class with `@abstractmethod` for `to_openai()` to prevent direct instantiation
- Move `LanguageModelMessageRole` enum to `language_model.schemas` (includes `TOOL` role, separate from `ChatMessageRole`)
- Simplify `ChatMessage`: remove unused `ToolCall` class and `tool_calls` field, make `id` required, remove `TOOL` role from `ChatMessageRole`
- Deprecate `map_to_chat_messages()` in favor of `ChatMessage.model_validate()`
- Add `to_openai()` method to `LanguageModelMessages` container for batch conversion
- Add `@override` decorators to concrete `to_openai` implementations
- Raise `ValueError` for unknown message roles instead of falling back to base class

## [1.69.3] - 2026-04-08
- Add number zero to allowed tool name pattern

## [1.69.2] - 2026-04-08
- Code interpreter (UN-17972 / UN-17927): remove dead `htmlWithSource` fence generation and regex handling; HTML stays on the unconditional `HtmlRendering` markdown path from #1361 (all prior `HtmlRendering` edge-case fixes remain on `main`)

## [1.69.1] - 2026-04-08
- Add async variants of history construction functions and use them in `get_history_from_db` (`get_full_history_async`, `get_message_tools_async`, `search_contents_async`, `download_content_to_bytes_async`) to avoid blocking the event loop
- Replace sync `modify_assistant_message` with async in Qwen runner
- Replace sync `MCP.call_tool` with `MCP.call_tool_async` in MCP wrapper


## [1.69.0] - 2026-04-07
- Add optional `[monitoring]` extra with Prometheus support: `MetricNamespace`, `track()`, `MetricsMiddleware`, `get_metrics()`

## [1.68.13] - 2026-04-06
- Add concurrency diagnostic logging to code interpreter postprocessor: chunk gap detection, `tracker.update()` blocking measurement, lock contention and publish timing in `_FileProgressTracker`, `modify_assistant_message_async` latency warnings, and SDK upload duration warnings

## [1.68.12] - 2026-04-05
- Disable OpenAI SDK built-in retries (`max_retries=0`) for container file downloads to eliminate silent double-retry compounding — only the manual retry loop with full logging now retries
- Add configurable `download_read_timeout` (default 120s) for container file downloads, down from the SDK default of 600s, to fail faster on stalled connections
- Add background elapsed-time ticker that publishes progress updates even when the OpenAI API is slow to return the first byte
- Add comprehensive timing instrumentation to all critical-path functions: `run()` phase breakdown (load_stm, download_upload, save_stm, orphan), per-file pipeline (download/upload split), first-byte latency, stream transfer time, and `apply_postprocessing` duration
- Log swallowed exceptions in `PersistentShortMemoryManager` — failed short-term memory lookups now log the exception type and message instead of being silently discarded

## [1.68.11] - 2026-04-05
- Add real-time file download/upload progress reporting to code interpreter postprocessor — users see inline progress (percentage or elapsed time), retry indicators, and a summary block while files are being prepared
- Switch container file downloads from buffered to streaming (`with_streaming_response`) to enable chunk-level progress tracking and percentage display when `content-length` is available
- Add `_FileProgressTracker` class with asyncio lock, throttled message updates, inline sandbox-link replacement, and an appended summary block
- Replace tenacity-based download retry with manual retry loop to support per-attempt progress and retry-count reporting to the tracker
- Add `progress_update_interval` and `download_chunk_size` config fields to `DisplayCodeInterpreterFilesPostProcessorConfig`

## [1.68.10] - 2026-04-05
- Add detailed structured logging throughout the code interpreter citation pipeline (`run()`, download/upload, `apply_postprocessing_to_response()`) for production transparency: file counts, per-file outcomes, replacement summaries, and dangling-link detection
- Add `_ChatLoggerAdapter` so all instance-method log messages are prefixed with `[chat_id=…]` for per-conversation traceability
- Improve user-facing error message when file generation permanently fails after retries — now reads "File could not be generated. Please try again." instead of generic "File download failed"

## [1.68.9] - 2026-04-04
- Fix intermittent sandbox URL replacement failures in code interpreter postprocessor caused by transient short-term memory errors crashing `run()` and preventing `apply_postprocessing_to_response()` from executing
- Add retry with exponential backoff to file upload calls (download already had retry)
- Extract `_build_retry()` helper to share retry policy across all I/O operations
- Fix `_replace_container_file_citation` missing `!?` prefix — LLM using `![label](sandbox:...)` syntax for non-image files caused false "download failed" error despite successful upload
- Wrap orphan code block upload in try/except to prevent failures from blocking file replacement

## [1.68.8] - 2026-04-04
- Always render HTML code interpreter files with `HtmlRendering` block, independent of feature flags (`enable_html_rendering_un_15131` and `enable_code_execution_fence_un_17972`)
- Exclude HTML files from fence injection (`imgWithSource`/`fileWithSource`) pipeline to avoid spurious warnings

## [1.68.7] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references
- Update `langchain` optional extra to `>=1.0.0,<2` (was `>=0.3.27,<0.4`) and `langchain-core` to `>=1.0.0,<2`

## [1.68.6] - 2026-04-02
- Adding `uploaded_files` and `selected_uploaded_files` to additional parameters in payload
- Feature flag `FEATURE_FLAG_SELECTED_UPLOADED_FILES_UN_18470` added

## [1.68.5] - 2026-04-01
- Code interpreter (UN-17972): restore `htmlWithSource` fences for HTML when code-execution fence FF is on (legacy `HtmlRendering` path only when fence FF is off and HTML rendering FF is on)
- Extend fence regexes and `_get_next_fence_id` for `htmlWithSource`; include HTML in unmatched-code-block warnings when fences are used

## [1.68.4] - 2026-04-01
- Removing feature flag for tool call persistence (`FEATURE_FLAG_ENABLE_TOOL_CALL_PERSISTENCE_UN_15977`)

## [1.68.3] - 2026-04-01
- `DDMetadata`: add `rerun` (optional bool, default false), aligned with `MagicTableMetadata` in node-chat; accepts legacy `Rerun` key via `validation_alias`

## [1.68.2] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [1.68.1] - 2026-04-01
- Add retry on error when downloading code execution generated files

## [1.68.0] - 2026-04-01
- Adding experimental open pdf tool

## [1.67.3] - 2026-04-01
- Remove adding of extra references when Code Execution Fence FF is on

## [1.67.2] - 2026-03-31
- `forced_tools` and `tool_input_json_schema` were changed from their default values `None` to [] and "" respectively, to enable proper rendering in Space 2.0. Backwards compatibility is ensured.

## [1.67.1] - 2026-03-31
- Appending `chat_id`, `assistant_id`, and `display_name` to debug info for sub agent tool calls

## [1.67.0] - 2026-03-31
- Add `AUTO_CONTAINER_ONLY` model capability for models that require `container: {"type": "auto"}` instead of explicit container IDs (GPT-5.4 Pro)
- Add `force_auto_container` parameter to `OpenAICodeInterpreterTool.build_tool` and `OpenAIBuiltInToolManager.build_manager`/`_build_tool`
- Fix auto-container path dropping `is_exclusive` flag — now correctly forwarded to the constructor

## [1.66.1] - 2026-03-31
- Add Feature Flag `enable_web_search_argument_screening_un_18741`

## [1.66.0] - 2026-03-30
- Add `applied_ingestion_config` to `Content` schema

## [1.65.2] - 2026-03-30
- Remove experimental open pdf tool

## [1.65.1] - 2026-03-30
- Code interpreter (UN-17972): `get_tool_prompts()` now always uses the stored `tool_description_for_system_prompt` (no feature-flag substitution); UI and backend stay aligned when the config default is the fence prompt.
- Code interpreter (UN-18561): extend `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE` — sandbox has no internet; do not use `requests` / `httpx` / `urllib` for web fetches; use the web search tool first, then code interpreter.
- Code interpreter: RJSF textarea `rows` for `tool_description_for_system_prompt` is derived from `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE` so the widget height matches the default body (fixes undersized editor).

## [1.65.0] - 2026-03-29
- Adding experimental open pdf tool

## [1.64.7] - 2026-03-27
- Code interpreter (UN-17972): when the sandbox HTML link is the only content on its line (including indented list continuations), replace the full line so the `HtmlRendering` opening fence starts at column 0; match is anchored to line start so mid-line links still use the separate mid-line path.
- Code interpreter (UN-17972): strip runs of whitespace-only lines immediately preceding that link line so blank indented lines do not remain above the `HtmlRendering` block.
- Code interpreter (UN-17972): when the link is mid-line and the response continues immediately after the closing parenthesis with no newline, append a newline after the closing fence so following text does not adjoin the fence.

## [1.64.6] - 2026-03-27
- Code interpreter (UN-17972): fix `HtmlRendering` block format for fenced code-interpreter HTML — remove an extra blank line before the `unique://content/...` URL (template had `\n\n\n`, parser expected a single blank line; broke rendering when images/PDFs were in the same message).
- Code interpreter (UN-17972): when the model places the sandbox link mid-line (e.g. numbered list item), insert a leading newline before the `HtmlRendering` fence so it starts on its own line (same requirement as `imgWithSource` / `fileWithSource` standalone fences).

## [1.64.5] - 2026-03-27
- RJSF: Add `CustomWidgetName` values `folderScopePicker`, `selectionPolicy`, `toolIconSelect`, and `toggleSwitch` (aligned with TypeScript custom widgets).
- RJSF: `RJSFMetaTag.custom()` accepts `name: CustomWidgetName | str` so callers can pass string widget identifiers (e.g. custom icons) in addition to enum members.

## [1.64.4] - 2026-03-26
- Code interpreter (UN-17972): when fence FF is on, HTML artifacts use `HtmlRendering` blocks with `800px` / `600px` dimensions and `unique://content/...` (revert from `htmlWithSource` for product UX). Remove `htmlWithSource` from fence building and normalization regexes; skip HTML in unmatched-code-block warnings; update tests.

## [1.64.3] - 2026-03-26
- Config checker: CLI and validator improvements

## [1.64.2] - 2026-03-26
- Add `UniqueSettings.with_auth` to return a new settings instance with a given auth context while preserving app, api, chat, filter options, and env file reference (UN-18484)
- Add tests for `UniqueSettings`

## [1.64.1] - 2026-03-26
- Add `enable_tool_call_persistence_un_15977` feature flag; when disabled (default), `get_full_history_with_contents` is used instead of `get_full_history_with_contents_and_tool_calls` and `enable_tool_call_persistence` is threaded through `HistoryManagerConfig` and `LoopTokenReducer` (UN-15977)

## [1.64.0] - 2026-03-25
- Code interpreter (UN-17972): orphan code runs — synthesise a `.txt` artifact and `fileWithSource` fence when code produces no container files, gated on `enable_code_execution_fence_un_17972` (replaces legacy `<details>` for that case)
- Code interpreter (UN-17972): `OpenAICodeInterpreterTool.get_required_include_params()` returns `["code_interpreter_call.outputs"]` when the fence FF is on; add `OpenAIBuiltInTool.get_required_include_params()`, `OpenAIBuiltInToolManager.get_required_include_params()`, and `ResponsesApiToolManager.get_required_include_params()`; add `_collect_stdout` for `ResponseCodeInterpreterToolCall.outputs` (end-to-end `include` requires orchestrator PR)
- Code interpreter (UN-17972): when fence FF is on, `ShowExecutedCodePostprocessor` is a no-op; remove `strip_executed_code_blocks` and its use in `DisplayCodeInterpreterFilesPostProcessor`; add optional `company_id` on `ShowExecutedCodePostprocessor` (orchestrator should pass company id alongside generated-files postprocessor)
- Add unit test for `message.text is None` handling in `DisplayCodeInterpreterFilesPostProcessor.apply_postprocessing_to_response`

## [1.63.2] - 2026-03-25
- Code interpreter (UN-17972): emit `htmlWithSource` fences for `.html` artifacts when `enable_code_execution_fence_un_17972` is on; HTML uses the same sandbox-link → fence injection path as other files. Legacy `HtmlRendering` block is used only when the fence FF is off and `enable_html_rendering_un_15131` is on.
- Fence-mode system prompt (`DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE`): require HTML only as saved files under `/mnt/data/`, not inline in the assistant text; add UI-oriented best practices (HTML5 shell, self-contained CSS/JS, fluid layout, contrast, semantic elements, no parent-frame access).
- `get_tool_prompts()`: treat stored `tool_description_for_system_prompt` as the unmodified default when it equals either `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT` or `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE`, so spaces created across toolkit versions still receive the fence prompt when the FF is on.

## [1.63.1] - 2026-03-25
- Broaden internal API URL matching to include hostnames that contain `.svc.` or end with `.svc`

## [1.63.0] - 2026-03-24
- Globally unique source numbering across chat turns (UN-15977): source numbers now continue from the highest index persisted in the database, ensuring `[sourceN]` citations remain unique and stable across the entire conversation
- Add `get_content_chunks_for_backend()` to `HistoryManager`: builds a positional content-chunk list where `result[N]` contains the chunk for `[sourceN]`, including prior-turn sources reconstructed from the database
- Remove `percent_for_tool_call_history` from `HistoryManagerConfig` and `_limit_tool_call_tokens` from `LoopTokenReducer`; history truncation now relies solely on `percent_of_max_tokens_for_history` with whole-turn dropping
- Add `compute_max_source_number_from_tool_calls` and `build_source_map_from_tool_calls` utilities
- `get_full_history_with_contents_and_tool_calls` now returns `(messages, max_source_number, source_map)` tuple

## [1.62.4] - 2026-03-24
- Fix tool-history source serialization to preserve readable Unicode in LLM-facing JSON payloads
- Fix reduced tool responses to keep readable Unicode for standard source reduction and `TableSearch`

## [1.62.3] - 2026-03-24
- Add `content_id` to search result source dicts in tool call responses (`transform_chunks_to_string` and `_create_reduced_standard_sources_message`) so the LLM can associate each source with its content object

## [1.62.2] - 2026-03-24
- Code interpreter (UN-18375): harden `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT` and `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE` — require `plt.savefig` + `plt.close` for plots, forbid `sandbox:/mnt/data/` links unless the file was created by executed code in the same response, and use `<filename>` (not a literal `filename.png`) in savefig examples so multiple plots do not overwrite the same path

## [1.62.1] - 2026-03-23
- Base `Tool.__init__` accepts config only; optional overload for backward compatibility
- Tools not tied to chat can use `Tool(config)`; legacy tools use `Tool(config, event, tool_progress_reporter)`
- `MCPToolWrapper`, `SubAgentTool`, `DeepResearchTool`, `PMPositionsTool` create their own services when needed

## [1.62.0] - 2026-03-23
- Add `tool_manager` parameter to `DebugInfoManager.extract_builtin_tool_debug_info` and `_extract_tool_calls_from_stream_response`; each code interpreter call entry now includes `is_exclusive` and `is_forced` flags derived from the tool manager
## [1.61.0] - 2026-03-23
- Add option to include Code Execution in tool analytics (Debug Info)

## [1.60.0] - 2026-03-20
- Add `MessageTool` persistence and history reconstruction (UN-15977): after each agentic loop, tool calls and their responses are persisted to the database via `unique_sdk.MessageTool`. On subsequent turns, the full tool-call history is batch-loaded and interleaved into the LLM message history (parallel calls grouped into a single assistant message per round). New `ChatService` methods: `create_message_tools`, `create_message_tools_async`, `get_message_tools`, `get_message_tools_async`. New schema types: `ChatMessageTool`, `ChatMessageToolResponse`. New `HistoryManager` methods: `extract_message_tools`, `compact_message_tools`. Requires `unique-sdk>=0.10.85`.

## [1.59.1] - 2026-03-19
- Add `UniqueServiceFactory` for registry-based service creation via `UniqueContext` (UN-18236)
- Add `UniqueContext` with `from_chat_event` / `from_event` / `from_settings` factory methods
- Add `AuthContext`, `AuthContextProtocol`, `ChatContext`, `ChatContextProtocol` to `unique_settings`
- Add `ChatService.from_context` and `KnowledgeBaseService.from_context` constructors; deprecate old event-based constructors
- Deprecate `UniqueSettings.auth` property in favour of `UniqueSettings.authcontext`

## [1.59.0] - 2026-03-19
- Introduce `AuthContextProtocol` and `AuthContext` (Pydantic `BaseModel`) for unified auth typing across MCP services and apps (UN-18234)
- Add `ChatContextProtocol` and `ChatContext` (Pydantic `BaseModel`) for chat context (UN-18234)
- Add `UniqueEnvironment` class grouping env-only settings (`app` + `api`) (UN-18234)
- Add `UniqueContext` class grouping request/env context (`auth` + `chat`) (UN-18234)
- Enhance `UniqueAuth` with `get_confidential_company_id()`, `get_confidential_user_id()`, and `to_auth_context()` methods (UN-18234)
- Add `authcontext: AuthContextProtocol` property to `UniqueSettings`; deprecate `auth` (still returns `UniqueAuth`) (UN-18234)

## [1.58.1] - 2026-03-18
- Code interpreter fence injection (UN-17972): extend `_build_code_blocks` matching so generated images reliably map to their producing code block — secondary match on quoted filename or stem, plus last-resort assignment to the last code block when paths are fully dynamic (e.g. `f"/mnt/data/chart_{type}_{i}.png"`). Fixes bare `![image](unique://content/...)` instead of `imgWithSource` fences.
- Secondary matching now uses last-writer-wins across code blocks (aligned with primary); only Step 1a primary matches are frozen — earlier secondary logic incorrectly used first-writer-wins.

## [1.58] - 2026-03-18
- Re-apply 1.55.0 (ChatMessage/LanguageModelStreamResponseMessage breaking changes) and 1.56.0 (execution time tracking)

## [1.57] - 2026-03-18
- Revert 1.55.0 (ChatMessage/LanguageModelStreamResponseMessage breaking changes) and 1.56.0 (execution time tracking) — safe baseline for release/2026.12 deployments

## [1.56.0] - 2026-03-17
- Add execution time tracking to `EvaluationManager`, `PostprocessorManager`, and `ToolManager` with `get_execution_times()` accessors
- Add `get_debug_info()` / `get_debug_info_async()` to `ChatService` for retrieving debug info from the current user message

## [1.55.1] - 2026-03-17
- Add `AZURE_GPT_54_2026_0305` (`gpt-5.4-2026-03-05`): 922k input / 128k output, Chat Completions + Responses API, function calling, parallel function calling, reasoning, streaming, structured output, vision; temperature 0.0–1.0, default `reasoning_effort: "none"`
- Add `AZURE_GPT_54_PRO_2026_0305` (`gpt-5.4-pro-2026-03-05`): 922k input / 128k output, Responses API only (no Chat Completions), function calling, parallel function calling, reasoning, streaming, structured output, vision; temperature fixed at 1.0, default `reasoning_effort: "medium"`
- Add `LITELLM_OPENAI_GPT_54` (`litellm:openai-gpt-5-4`): same capabilities as `AZURE_GPT_54_2026_0305`
- Add `LITELLM_OPENAI_GPT_54_THINKING` (`litellm:openai-gpt-5-4-thinking`): Chat Completions + Responses API, temperature fixed at 1.0, default `reasoning_effort: "medium"`
- Fix `AZURE_GPT_51_2025_1113`: correct temperature bounds from 1.0–1.0 to 0.0–1.0 and `reasoning_effort` from `None` to `"none"`
- Fix `AZURE_GPT_52_2025_1211` and `LITELLM_OPENAI_GPT_52`: correct `token_limit_input` from 400k to 272k, temperature bounds from 1.0–1.0 to 0.0–1.0, and `reasoning_effort` from `None` to `"none"`
- Fix `LITELLM_OPENAI_GPT_52_THINKING`: correct `token_limit_input` from 400k to 272k

## [1.55.0] - 2026-03-16
- Align `ChatMessage` to `PublicMessageDto`: rename `original_content` → `original_text` (⚠️ breaking), add `started_streaming_at`, `stopped_streaming_at`, `assessment`, `previous_message_id` fields, change `references` default from `None` to `[]`, add `text` property as getter/setter alias for `content` (UN-18040)
- Remove `LanguageModelStreamResponseMessage` class — replaced with backward-compatible alias `= ChatMessage`; `id` and `content` are now `str | None` instead of required `str` (UN-18040)
- Consolidate `LanguageModelMessageRole` as a re-export of `ChatMessageRole` (same values, no runtime change) (UN-18040)
- Add `LanguageModelTokenUsage` model and `usage: LanguageModelTokenUsage | None` field to `LanguageModelStreamResponse`, matching `PublicStreamResultDto` (UN-18040)

## [1.54.1] - 2026-03-16
- Add reusable `NoneToDefault` `BeforeValidator` that replaces incoming `None` values with the field's declared default via `PydanticUseDefault`, enabling backward-compatible migration from nullable fields to non-nullable fields with defaults
- Apply `NoneToDefault` validator to `DocxGeneratorConfig.template_content_id`

## [1.54.0] - 2026-03-16
- Code interpreter (UN-17972 review fix): `get_tool_prompts()` now respects operator-customised `tool_description_for_system_prompt` when the fence FF is on. Previously the fence-aware prompt was applied unconditionally when the FF was enabled, silently ignoring any custom prompt. Now `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE` is only substituted when the operator is still using the unmodified default; a customised prompt is always used regardless of the FF.

## [1.53.4] - 2026-03-13
- Code interpreter (UN-17972 review fixes): `_warn_missing_content_ids` downgraded from WARNING to INFO. Dangling `sandbox:/mnt/data/` links are now replaced with the configured error message in addition to logging a warning. Fence prompt updated (example blank lines, component description, "files" not "images"). Consecutive fences normalised to exactly one newline between them (same-line, list-item, and blank-line cases).

## [1.53.3] - 2026-03-12
- Code interpreter (UN-17972 follow-up): prompt update — `DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE` variant removes the "Descriptive Title" instruction; selected automatically in `get_tool_prompts()` when `FEATURE_FLAG_ENABLE_CODE_EXECUTION_FENCE_UN_17972` is on; legacy prompt (with title) used when flag is off, preserving exact pre-fence behaviour. `company_id` stored on `OpenAICodeInterpreterTool` to enable per-company FF evaluation at prompt-render time.
- Code interpreter: link/file validation — upgraded stage-1 replacement helpers (`_replace_container_*_citation`) from INFO to WARNING when no sandbox link is found for an uploaded file; added WARNING in `_inject_code_execution_fences` when a fence is discarded (no inline ref match); added `_warn_missing_content_ids` end-of-pipeline check that warns for any `content_id` absent from the final message text.
- Code interpreter: fence rendering fix — added `_ensure_fences_are_standalone` (strips markdown list-item prefix before a fence) and `_CONSECUTIVE_FENCES_RE` separator pass (ensures `\n\n` between two fences that land on the same line), so `imgWithSource`/`fileWithSource` blocks are always standalone blocks parseable by the frontend. FF=on prompt updated to instruct the LLM to place a blank line before and after every file reference link.
- Code interpreter: logging coverage — added `_warn_dangling_sandbox_links` (warns when a `sandbox:/mnt/data/` link survives into the final text, indicating a hallucinated or unmatched file) and `_warn_unmatched_code_blocks` (warns when an uploaded file could not be matched to any code block and will fall back to a plain download link without the artifact UI).

## [1.53.2] - 2026-03-11
- Code interpreter: replace all inline file refs in `message.text` with structured fences — `imgWithSource` for images (PNG etc.) and `fileWithSource` for documents (CSV, Excel, PDF, Word, HTML, Markdown). Each fence carries `id` (message-scoped counter), `contentId`, `title` (derived from filename), `type` (for fileWithSource), and the generating `code`. `<details>` blocks and trailing `</br>` from `ShowExecutedCodePostprocessor` are stripped when at least one fence is injected. Feature-flagged via `FEATURE_FLAG_ENABLE_CODE_EXECUTION_FENCE_UN_17972` (default off, safe to merge). `debugInfo.code_blocks` and the `code_blocks` field on `LanguageModelStreamResponseMessage` are removed (superseded by the fences). (UN-17972)
## [1.53.1] - 2026-03-11
- Fix RJSF `ui_schema_for_model` and `_unwrap_optional` to handle Python 3.10+ pipe union syntax (`A | B` / `types.UnionType`) in addition to `typing.Union`, so discriminated unions produce correct `anyOf` branches with per-branch metadata

## [1.53.0] - 2026-03-10
- Responses API: rate-limit retry via **tenacity** (new dependency). Default 1 retry with ~30s backoff for `too_many_requests`; config via `RATE_LIMIT_RETRY_*` env vars. When new answers UI feature flag (`enable_new_answers_ui_un_14411`) is active, a step is written to the message log during each retry wait so the user is informed.

## [1.52.1] - 2026-03-10
- Responses API: rate-limit retry via **tenacity** (new dependency). Exponential backoff (30s→60s→120s) for `too_many_requests`; config via `RATE_LIMIT_RETRY_*` env vars. When new answers UI feature flag (`enable_new_answers_ui_un_14411`) is active, a step is written to the message log during each retry wait.

## [1.52.0] - 2026-03-10
- Refactor loop runner architecture: make `BasicLoopIterationRunner` an extensible base class with overridable hooks (`_handle_forced_tools`, `_handle_last_iteration`, `_handle_normal_iteration`)
- Add `tool_choice_override` parameter to `run_forced_tools_iteration` for model-specific tool choice handling
- Add `MistralLoopIterationRunner` (subclass of `BasicLoopIterationRunner`) that forces `tool_choice="any"` for Mistral models during forced tool iterations
- Refactor `QwenLoopIterationRunner` to subclass `BasicLoopIterationRunner`; align constructor to accept `config: BasicLoopIterationRunnerConfig` instead of bare `max_loop_iterations`
- Remove model-detection helpers `is_qwen_model` and `is_mistral_model` from the toolkit; runner selection is now the orchestrator's responsibility

## [1.51.0] - 2026-03-10
- Make `ToolBuildConfig` generic over the configuration type. Enables downstream consumers to parameterize the configuration type without invariant-override type errors.

## [1.50.4] - 2026-03-05
- Add `INGESTION_UPLOAD_API_URL_INTERNAL` environment variable to override the ingestion upload URL. This can be used to upload content from within a private network like a Kubernetes cluster.

## [1.50.3] - 2026-03-04
- Docs: add minimal langchain example and langchain platform documentation
- Docs: move manual examples to dedicated folder
- Docs: fix missing and duplicated tags in generated examples

## [1.50.2] - 2026-03-03
- Build: migrate from Poetry to uv (PEP 621 metadata, uv_build backend, dependency-groups)

## [1.50.1] - 2026-03-02
- Security: upgrade pillow from 10.4.0 to 12.1.1 (CVE / Dependabot alert — out-of-bounds write in PSD loader)
- Security: upgrade starlette from 0.48.0 to 0.49.1 (Dependabot alert)

## [1.50.0] - 2026-03-02
- Add async download-to-bytes functions: `download_content_to_bytes_async` on `KnowledgeBaseService`, `ContentService`, and `download_chat_content_to_bytes_async` on `ChatService`

## [1.49.0] - 2026-03-02
- Make the code execution tool always available to the agent

## [1.48.1] - 2026-03-02
- Revert `DocxGeneratorConfig` and `DocxGeneratorService` additions from 1.47.11 (broke SWOT tool, pending further testing)

## [1.48.0] - 2026-02-26
- Add pandoc markdown to docx conversion utility

## [1.47.13] - 2026-02-26
- Added support for subagent file access to the ContentService and ChatService based on correlation component of the event.

## [1.47.12] - 2026-02-26
- Attach tool result images (MCP or internal) to the user message so the LLM can see them
- MCP image handling: hide_in_chat uploads, unique content names, small robustness fixes

## [1.47.10] - 2026-02-26
- Code interpreter: bound `expires_after_minutes` to 1–20 (OpenAI API max), add RJSF `NumberWidget.updown` for UI

## [1.47.9] - 2026-02-26
- Fixing bug with chunk relevancy sorter

## [1.47.8] - 2026-02-25
- Use `AliasGenerator` to create the sort keys in `ui_schema_for_model`

## [1.47.7] - 2026-02-25
- Additional `user_space_instructions` to `ChatEventAdditionalParameters`

## [1.47.6] - 2026-02-25
- Rename `cancelled_at` to `user_aborted_at` on `ChatMessage` and update `CancellationWatcher` to poll `userAbortedAt`

## [1.47.5] - 2026-02-25
- Code execution updates:
  - Always upload to chat. Remove ability to upload to scope.
  - Cleanup displayed config

## [1.47.4] - 2026-02-24
- Extend RJSF tags: add `CustomWidget.custom()` with `CustomWidgetName`, `ObjectWidget.collapsible()`, `SpecialWidget.hidden()`
- Add RJSF meta tags to `SubAgentToolConfig` text fields (textarea with rows=5 for tool descriptions and format info)

## [1.47.3] - 2026-02-24
- Add `mcp_server` name to debug info for analytics

## [1.47.2] - 2026-02-23
- Add HTML rendering documentation (inline HTML and content references)

## [1.47.1] - 2026-02-23
- Fix bug with OpenAIBuiltinToolManager

## [1.47.0] - 2026-02-23
- Move `CodeInterpreterExtendedConfig` to toolkit for validation in `ToolBuildConfig`

## [1.46.13] - 2026-02-23
- Add easy access to decoder from llm info

## [1.46.12] - 2026-02-21
- Add `litellm:gemini-3-1-pro-preview` to `info.py`

## [1.46.11] - 2026-02-20
- Add OpenAI-proxy direct streaming with Python-side reference injection (UN-17264)
- Add `stream_complete_with_references_openai()` using async OpenAI client and `chat.completions.stream()`
- Add stream transformation pipeline: `StreamTransform` protocol, `TextTransformPipeline`, `ReferenceInjectionTransform` (reuses `add_references_to_message`), `NormalizationTransform` placeholder
- Export `stream_complete_with_references_openai` and stream transform types from `unique_toolkit.language_model`

## [1.46.10] - 2026-02-19
- Add flag-based cancellation support via `CancellationWatcher` and `TypedEventBus`
- Expose `ChatService.cancellation` property for polling, event subscription, and `run_with_cancellation` helper
- Add `CancellationEvent`, `user_aborted_at` on `ChatMessage`, and `stopped_by_user` on `LanguageModelStreamResponse`

## [1.46.9] - 2026-02-19
- Add `litellm:anthropic-claude-sonnet-4-6` to `info.py`

## [1.46.8] - 2026-02-17
- Add Configuration Check utility as class, CLI and CI workflow

## [1.46.7] - 2026-02-13
- Add documentation versioning support using `mike`
- Add versioned documentation build and deploy workflows

## [1.46.6] - 2026-02-12
- Add `litellm:grok-4-1-fast-non-reasoning` and `litellm:grok-4-1-fast-non-reasoning` to `info.py`

## [1.46.5] - 2026-02-11
- Add `DEFAULT_LANGUAGE_MODEL` environment-based resolution with fallback support for invalid or missing values
- Allow default model configuration via both enum value strings and enum member names
- Export `DEFAULT_LANGUAGE_MODEL` and `DEFAULT_GPT_4o` from `unique_toolkit.language_model` for easier imports
- Keep `unique_toolkit._common.default_language_model.DEFAULT_GPT_4o` backward compatible via re-export
- Add unit tests for default language model resolution behavior

## [1.46.4] - 2026-02-10

- Fix: Add `union_mode="left_to_right"` to `encoder_name` field so Pydantic tries `EncoderName` enum before `str`,
  enabling bundled tokenizers when UI sends string values

## [1.46.3] - 2026-02-09
### Fixed

- Fix hallucination check crash when responses contain invalid source indices (e.g., from code blocks with array
  indexing)
- Use existing `context_text_from_stream_response()` utility with built-in bounds checking instead of manual extraction

### Removed
- Remove unused `regex` dependency (no longer needed after refactoring)

## [1.46.2] - 2026-02-09
- Add `litellm:anthropic-claude-opus-4-6` and `AZURE_MODEL_ROUTER_2025_1118` to `info.py`

## [1.46.1] - 2026-02-06
- Add model-agnostic token counting via `LanguageModelInfo.get_encoder()`
- Add bundled Qwen/DeepSeek tokenizers for accurate token counting
- Deprecate `content.utils.count_tokens()` in favor of `_common.token.count_tokens()`

## [1.46.0] - 2026-02-05
- Add `ElicitationService` to manage user elicitation requests with both sync and async methods
- Add elicitation schemas: `Elicitation`, `ElicitationMode`, `ElicitationAction`, `ElicitationStatus`,
  `ElicitationSource`
- Add elicitation exceptions: `ElicitationCancelledException`, `ElicitationDeclinedException`,
  `ElicitationExpiredException`, `ElicitationFailedException`
- Add `elicitation` property to `ChatService` for easy access to elicitation functionality
- Refactor feature flags system with new `FeatureFlag` class supporting both boolean and company-specific enablement
- Add feature flag `FEATURE_FLAG_ENABLE_ELICITATION_UN_15809` for elicitation support
- Add async methods to `MessageStepLogger`: `create_message_log_entry_async`, `update_message_log_entry_async`,
  `create_or_update_message_log_async`
- Add `Correlation` schema to `ChatEventPayload` for tracking parent message relationships across chats
- Add correlation support to sub-agent tool for better message tracking
- Update MCP tool wrapper and sub-agent tool to use new feature flag system

## [1.45.10] - 2026-02-05
- Add `RERUN_ROW` event type and `MagicTableRerunRowPayload` for targeted row re-execution in Agentic Tables

## [1.45.9] - 2026-02-03
- Add feature flag `FEATURE_FLAG_ENABLE_HTML_RENDERING_UN_15131` for HTML rendering support
- Put HTML rendering for code interpreter files behind the feature flag

## [1.45.8] - 2026-02-02
- Hallucination: Hide Source Selection Mode and Reference pattern from schema

## [1.45.7] - 2026-01-30
- Add JSON string parsing support for reasoning and text parameters in responses API (UI compatibility)
- Fix variable name bug in `_attempt_extract_verbosity_from_options` function
- Improve `other_options` handling to prevent overwriting explicitly set parameters

## [1.45.6] - 2026-01-30
- hallucination evaluator: Use original response to retrieve referenced chunk

## [1.45.5] - 2026-01-29
- Add HTML rendering support for code interpreter generated files

## [1.45.4] - 2026-01-26
- Add ArtifactType `AGENTIC_REPORT`

## [1.45.3] - 2026-01-26
- Include message log update in subagents and MCP tools

## [1.45.2] - 2026-01-26
- Make FileMimeType backwards compatible with legacy extensions

## [1.45.1] - 2026-01-26
- Add FileMimeType utility helpers

## [1.45.0] - 2026-01-23
- Remove unused code execution options from config

## [1.44.0] - 2026-01-23

- Add LoopIterationRunner abstraction for the responses api

## [1.43.11] - 2026-01-23
- Add `RESPONSES_API` Capablity to some models that were missing it

## [1.43.10] - 2026-01-21
- Lowering the max iterations of the main agents and hard blocking Qwen3 from using too many agent rounds

## [1.43.9] - 2026-01-20

- Fix system message role conversion in responses API mode (was incorrectly set to "user", now correctly set to "
  system")

## [1.43.8] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [1.43.7] - 2026-01-15
- Cleanup hallucination config that is displayed in space config

## [1.43.6] - 2026-01-14
- Update message execution pipeline functions and service

## [1.43.5] - 2026-01-14
- Add deptry to dev dependencies for CI dependency checks
- Fix missing base_settings fixture parameter in FastAPI test

## [1.43.4] - 2026-01-14
- chore(deps-dev): bump aiohttp from 3.13.2 to 3.13.3

## [1.43.3] - 2026-01-13
- Changing default `assessment_type` in `SubAgentEvaluationServiceConfig` to `HALLUCINATION`

## [1.43.2] - 2026-01-12
- `DocxGeneratorService`: Alignment need to be specified by the template rather than in code

## [1.43.1] - 2026-01-12
- Remove accidental example report.md from repo

## [1.43.0] - 2026-01-11
- Add `WriteUpAgent` as an experimental service

## [1.42.9] - 2026-01-11
- Include feature flag to have message logs compatible with new ChatUI

## [1.42.8] - 2026-01-08
- Add validator to `BaseMetadata` in case `additional_sheet_information` is empty
- Add more code snippets to create references and pull file metadata

## [1.42.7] - 2026-01-08
- Add aliases for endpoint secret env var.

## [1.42.6] - 2026-01-07
- Remove double redundant condition

## [1.42.5] - 2026-01-07
- Add Mapping of metadata to the `search_content` calls
- Remove additional indentation by the markdown to docx converter

## [1.42.4] - 2026-01-07
- Added `additionalSheetInformation` to magic table event.

## [1.42.3] - 2026-01-05
- Added example code for agentic table

## [1.42.2] - 2026-01-05
- Fix naming of code interpreter tool in its `ToolPrompts`.

## [1.42.1] - 2026-01-05
- Version bump of SDK

## [1.42.0] - 2026-01-05
- Add new params for elicitation to `call_tool` api

## [1.41.0] - 2025-12-29
- Add `AgenticTable` service to unique_toolkit

## [1.40.0] - 2025-12-22
- Add option to use retrieve referenced chunks from their order
- Add `hide_in_chat` parameter to `upload_to_chat_from_bytes` and `upload_to_chat_from_bytes_async`
- Hide code interpreter files in chat
- Code Interpreter files are now uploaded to chat by default

## [1.39.2] - 2025-12-18

- Add `litellm:gemini-3-flash-preview`, `litellm:openai-gpt-5-2` and `litellm:openai-gpt-5-2-thinking` to
  `language_model/info.py`

## [1.39.1] - 2025-12-17
- Add GPT-5.2, GPT-5.2_CHAT to supported models list

## [1.39.0] - 2025-12-17
- Adding simpler shortterm message abilities to chat service

## [1.38.4] - 2025-12-17
- Improving handling of tool calls with Qwen models

## [1.38.3] - 2025-12-17
- Move the failsafe exception to root folder of unique_toolkit from agentic tools

## [1.38.2] - 2025-12-17
- Fixing bug that language model infos were not loaded correctly

## [1.38.1] - 2025-12-16
- chore(deps): Bump urllib3 from 2.5.0 to 2.6.2 and unique_sdk from 0.10.48 to 0.10.58 to ensure urllib3 transitively

## [1.38.0] - 2025-12-15
- Including capability to load LanguageModelInfos in env variable

## [1.37.0] - 2025-12-15
- Adding a prompt appendix to enforce forced tool calls when using Qwen models

## [1.36.0] - 2025-12-11
- Add support for a sub agent tool system reminder when no references are present in the sub agent response.

## [1.35.4] - 2025-12-10
- Fix a potential stacktrace leak

## [1.35.3] - 2025-12-10
- Add option to ignore some options when calling the LLM for the planning step.

## [1.35.2] - 2025-12-05
- Increase speed of token reducer

## [1.35.1] - 2025-12-05
- Improve efficiency of token reducer if tool calls overshoot max token limit

## [1.35.0] - 2025-12-04
- Add `LoopIterationRunner` abstraction and support for planning before every loop iteration.

## [1.34.1] - 2025-12-02
- Update code interpreter tool instructions.

## [1.34.0] - 2025-12-02
- Add option to upload code interpreter generated files to the chat.

## [1.33.3] - 2025-12-02
- Fix serialization of ToolBuildConfig `configuration` field.

## [1.33.2] - 2025-12-01
- Upgrade numpy to >2.1.0 to ensure compatibility with langchain library

## [1.33.1] - 2025-12-01
- Add `data_extraction` to unique_toolkit

## [1.33.0] - 2025-12-01
- Add support for system reminders in sub agent responses.

## [1.32.1] - 2025-12-01
- Added documentation for the toolkit,some missing type hints and doc string fixes.

## [1.32.0] - 2025-11-28
- Add option to filter duplicate sub agent answers.

## [1.31.2] - 2025-11-27

- Added the function `filter_tool_calls_by_max_tool_calls_allowed` in `tool_manager` to limit the number of parallel
  tool calls permitted per loop iteration.

## [1.31.1] - 2025-11-27
- Various fixes to sub agent answers.

## [1.31.0] - 2025-11-26
- Adding model `litellm:anthropic-claude-opus-4-5` to `language_model/info.py`

## [1.30.0] - 2025-11-26
- Add option to only display parts of sub agent responses.

## [1.29.4] - 2025-11-25
- Add display name to openai builtin tools

## [1.29.3] - 2025-11-24
- Fix jinja utility helpers import

## [1.29.2] - 2025-11-21
- Add `jinja` utility helpers to `_common`

## [1.29.1] - 2025-11-21

- Add early return in `create_message_log_entry` if chat_service doesn't have assistant_message_id (relevant for agentic
  table)

## [1.29.0] - 2025-11-21
- Add option to force include references in sub agent responses even if unused by main agent response.

## [1.28.9] - 2025-11-21
- Remove `knolwedge_base_service` from DocXGeneratorService

## [1.28.8] - 2025-11-20
- Add query params to api operation
- Add query params to endpoint builder

## [1.28.7] - 2025-11-20
- Adding Message Step Logger Class to the agentic tools.

## [1.28.6] - 2025-11-20
- Adding tests for message role filtering in chat functions

## [1.28.5] - 2025-11-20
- Including `expired_at` parameter in content schema
- Including chatRole `SYSTEM` into chat schema

## [1.28.4] - 2025-11-20
- Bump tiktoken to 0.12.0

## [1.28.3] - 2025-11-20
- Add batch upload of files to knowledgebase
- Add create folders utilities

## [1.28.2] - 2025-11-20
- Adding model `litellm:gemini-3-pro-preview` to `language_model/info.py`

## [1.28.1] - 2025-11-19
- Remove `chat_service` from DocXGeneratorService
- Set review standards in pyright for toolkit
- Refactor type check pipeline

## [1.28.0] - 2025-11-19
- Add option to interpret sub agent responses as content chunks.
- Add option to specify a custom JSON schema for sub agent tool input.

## [1.27.2] - 2025-11-19
- Add test to token counting

## [1.27.1] - 2025-11-18
- Add missing `create_query_params_from_model` in experimental endoint_builder.py

## [1.27.0] - 2025-11-18
- Add `session_config` field to `ChatEventPayload` schema for chat session configuration support
- Add `ingestion_state` field to `Content` model for tracking content ingestion status
- Add `include_failed_content` parameter to content search functions in `KnowledgeBaseService`, `search_contents`, and
  `search_contents_async`
- Experimental:
    - Fix HTTP GET requests in `build_request_requestor` to use query parameters (`params`) instead of JSON body
    - `build_requestor` to properly pass kwargs to `build_request_requestor`

## [1.26.2] - 2025-11-17
- Adding tool format information for MCP tools

## [1.26.1] - 2025-11-17
- Fix bug where forcing a tool still sends builtin tools to the LLM when using the responses api.

## [1.26.0] - 2025-11-17

- Adding model `AZURE_GPT_51_2025_1113`, `AZURE_GPT_51_THINKING_2025_1113`, `AZURE_GPT_51_CHAT_2025_1113`,
  `AZURE_GPT_51_CODEX_2025_1113`,  `AZURE_GPT_51_CODEX_MINI_2025_1113` and `litellm:openai-gpt-51` and
  `litellm:openai-gpt-51-thinking` to `language_model/info.py`

## [1.25.2] - 2025-11-12
- Standardize paths in unique toolkit settings

## [1.25.1] - 2025-11-12
- Make pipeline steps reusable
- Add pipeline checks for type errors
- Add pipeline checks for coverage

## [1.25.0] - 2025-11-10
- Download files generated by code execution in parrallel.
- Better display of files in the chat while loading.

## [1.24.5] - 2025-11-10
- Fix bug where images were not properly converted to responses api format.

## [1.24.4] - 2025-11-07
- Add `user_id` to language service for tracking
- Track `user_id` in hallucination check

## [1.24.3] - 2025-11-07
- Adding litellm models `litellm:gemini-2-5-flash-lite`

## [1.24.2] - 2025-11-06
- Fix build_requestor typehints

## [1.24.1] - 2025-11-06
- Add IconChartBar Icon to ToolIcon

## [1.24.0] - 2025-11-04

- Introduce ability to include system reminders in tools to be appended when the response is included in the tool call
  history

## [1.23.0] - 2025-11-04
- Refactor sub agent tools implementation for clarity and testability.

## [1.22.2] - 2025-11-03

- Updated `unique_ai_how-it-works.md` and `plan_processing.md` to document how new assistant messages are generated when
  the orchestrator produces output text and triggers tool calls within the same loop iteration.

## [1.22.1] - 2025-11-03

- Add missing package required markdown-it-py

## [1.22.0] - 2025-10-31
- Add `DocxGeneratorService` for generating Word documents from markdown with template support
- Fix documentation for `update_message_execution`, `update_message_execution_async`,
  `update_assistant_message_execution`, and `update_assistant_message_execution_async` functions to correctly reflect
  that the `status` parameter is now optional

## [1.21.2] - 2025-10-30
- Fixing that system format info is only appended to system prompt if tool is called

## [1.21.1] - 2025-10-30
- Improve Spaces 2.0 display of tool progress reporter configuration.

## [1.21.0] - 2025-10-30
- Add option to customize the display of tool progress statuses.

## [1.20.1] - 2025-10-30
- Fix typing issues in `LanguageModelFunction`.

## [1.20.0] - 2025-10-30
- Fix bug where async tasks executed with `SafeTaskExecutor` did not log exceptions.
- Add option to customize sub agent response display title.
- Add option to display sub agent responses after the main agent response.
- Add option to specify postprocessors to run before or after the others in the `PostprocessorManager`.

## [1.19.3] - 2025-10-29
- More documentation on advanced rendering

## [1.19.2] - 2025-10-29
- Removing unused tool specific `get_tool_call_result_for_loop_history` function
- Removing unused experimental config `full_sources_serialize_dump` in `history_manager`

## [1.19.1] - 2025-10-29
- Make api operations more flexible
- Make verification button text adaptable

## [1.19.0] - 2025-10-28
- Enable additional headers on openai and langchain client

## [1.18.1] - 2025-10-28

- Fix bug where sub agent references were not properly displayed in the main agent response when the sub agent response
  was hidden.

## [1.18.0] - 2025-10-27
- Temporary fix to rendering of sub agent responses.
- Add config option `stop_condition` to `SubAgentToolConfig`
- Add config option `tool_choices` to `SubAgentToolConfig`
- Make sub agent evaluation use the name of the sub agent name if only one assessment is valid

## [1.17.3] - 2025-10-27
- Update Hallucination check citation regex parsing pattern

## [1.17.2] - 2025-10-23
- Adding model `AZURE_GPT_5_PRO_2025_1006` and `litellm:openai-gpt-5-pro` to `language_model/info.py`

## [1.17.1] - 2025-10-23
- Fix hallucination check input with all cited reference chunks.

## [1.17.0] - 2025-10-22
- Add more options to display sub agent answers in the chat.

## [1.16.5] - 2025-10-18
- Adding litellm models `litellm:anthropic-claude-haiku-4-5`

## [1.16.4] - 2025-10-18
- Fix bug with MCP tool parameters schema

## [1.16.3] - 2025-10-18
- Add logging of MCP tool schema and constructed parameters

## [1.16.2] - 2025-10-16
- Reduce operation dependency on path instead of full url

## [1.16.1] - 2025-10-16
- Update debug info for better tool call tracking

## [1.16.0] - 2025-10-16
- Add responses api support.
- Add utilities for code execution.

## [1.15.0] - 2025-10-15
- Enable to distinguish between environment and modifiable payload parameters in human verification

## [1.14.11] - 2025-10-13
- Introduce testing guidelines for AI
- Add AI tests to `tool_config` and `tool_factory.py`

## [1.14.10] - 2025-10-13
- Fix token counter if images in history

## [1.14.9] - 2025-10-13
- Fix removal of metadata

## [1.14.8] - 2025-10-13
- Use default tool icon on validation error

## [1.14.7] - 2025-10-13
- Update of token_limit parameters for Claude models

## [1.14.6] - 2025-10-10
- Fix circular import appearing in orchestrator

## [1.14.5] - 2025-10-09

- Move `DEFAULT_GPT_4o` constant from `_common/default_language_model.py` to `language_model/constants.py` and deprecate
  old import path

## [1.14.4] - 2025-10-09
- Small fixes when deleting content
- Fixes in documentation

## [1.14.3] - 2025-10-08

- Reorganizes documentation
- All service interface towards a single folder
- Add main imports to __init__

## [1.14.2] - 2025-10-08
- Add utilities for testing and fix external import issue

## [1.14.1] - 2025-10-08
- Add utilities for testing

## [1.14.0] - 2025-10-07
- Manipulate Metadata with knowledge base service

## [1.13.0] - 2025-10-07
- Delete contents with knowledge base service

## [1.12.1] - 2025-10-07
- Fix bug where failed evaluations did not show an error to the user.

## [1.12.0] - 2025-10-07
- Add the `OpenAIUserMessageBuilder` for complex user messages with images
- More examples with documents/images on the chat

## [1.11.4] - 2025-10-07
- Make newer `MessageExecution` and `MessageLog` method keyword only

## [1.11.3] - 2025-10-07
- Move smart rules to content
- Add to documentation

## [1.11.2] - 2025-10-07
- Fix for empty metadata filter at info retrieval

## [1.11.1] - 2025-10-07
- Fix bug where hallucination check was taking all of the chunks as input instead of only the referenced ones.

## [1.11.0] - 2025-10-07
- Add sub-agent response referencing.

## [1.10.0] - 2025-10-07
- Introduce future proof knowledgebase service decoupled from chat
- Extend chat service to download contents in the chat
- Update documentation

## [1.9.1] - 2025-10-06
- Switch default model used in evaluation service from `GPT-3.5-turbo (0125)` to `GPT-4o (1120)`

## [1.9.0] - 2025-10-04
- Define the RequestContext and add aihttp/httpx requestors

## [1.8.1] - 2025-10-03
- Fix bug where sub agent evaluation config variable `include_evaluation` did not include aliases for previous names.

## [1.8.0] - 2025-10-03
- Sub Agents now block when executing the same sub-agent multiple times with `reuse_chat` set to `True`.
- Sub Agents tool, evaluation and post-processing refactored and tests added.

## [1.7.0] - 2025-10-01
- Add functionality to remove text in `get_user_visible_chat_history`

## [1.6.0] - 2025-10-01

- revert and simplify 1.5.0

## [1.5.1] - 2025-10-01
- Fix filtering logic to raise a ConfigurationException if chat event filters are not specified

## [1.5.0] - 2025-10-01
- Allow history manager to fetch only ui visible text

## [1.4.4] - 2025-09-30

- Fix bugs with display of sub-agent answers and evaluations when multiple sub-agent from the same assistant run
  concurrently.

## [1.4.3] - 2025-09-30
- Fix bug with sub-agent post-processing reference numbers.

## [1.4.2] - 2025-09-30
- Adding litellm models `litellm:anthropic-claude-sonnet-4-5` and `litellm:anthropic-claude-opus-4-1`

## [1.4.1] - 2025-09-30
- Handle sub agent failed assessments better in sub agent evaluator.

## [1.4.0] - 2025-09-30
- Add ability to consolidate sub agent's assessments.

## [1.3.3] - 2025-09-30
- fix bug in exclusive tools not making them selectable

## [1.3.2] - 2025-09-29
- Auto-update unique settings on event arrival in SSE client

## [1.3.1] - 2025-09-29
- More documentation on referencing

## [1.3.0] - 2025-09-28
- Add utilitiy to enhance pydantic model with metadata
- Add capability to collect this metadata with same hierarchy as nested pydantic models

## [1.2.1] - 2025-09-28
- Fix bug where camel case arguments were not properly validated.

## [1.2.0] - 2025-09-24
- Add ability to display sub agent responses in the chat.

## [1.1.9] - 2025-09-24
- Fix bug in `LanguageModelFunction` to extend support mistral tool calling.

## [1.1.8] - 2025-09-23
- Revert last to version 1.1.6

## [1.1.7] - 2025-09-23
- Introduce keyword only functions in services for better backward compatibility
- Deprecatea functions that are using positional arguments in services

## [1.1.6] - 2025-09-23
- Fix model_dump for `ToolBuildConfig`

## [1.1.5] - 2025-09-23
- Fix a circular import and add tests for `ToolBuildConfig`

## [1.1.4] - 2025-09-23
- First version human verification on api calls

## [1.1.3] - 2025-09-23
- Updated LMI JSON schema input type to include annotated string field with title

## [1.1.2] - 2025-09-22
- Fixed bug tool selection for exclusive tools

## [1.1.1] - 2025-09-18
- Fixed bug on tool config added icon name

## [1.1.0] - 2025-09-18
- Enable chat event filtering in SSE event generator via env variables

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates

## [0.9.1] - 2025-09-17

- update to python 3.12 due to security

## [0.9.0] - 2025-09-14
- Moved agentic code into the `agentic` folder. This breaks imports of
  - `debug_info_amanager`
  - `evals`
  - `history_manager`
  - `post_processor`
  - `reference-manager`
  - `short_term_memory_manager`
  - `thinking_manager`
  - `tools`

## [0.8.57] - 2025-09-14
- Added more utils to commons

## [0.8.56] - 2025-09-12
- Fixed token counter in utils

## [0.8.55] - 2025-09-10
- Update documentation with agentic managers

## [0.8.54] - 2025-09-10
- HistoryManager: compute source numbering offset from prior serialized tool messages using `load_sources_from_string`
- LoopTokenReducer: serialize reduced tool messages as JSON arrays to keep offsets parsable

## [0.8.53] - 2025-09-09
- Add support for skip ingestion for only excel files.

## [0.8.52] - 2025-09-08
- Fix import error in token counting

## [0.8.51] - 2025-09-08
- Update token counter to latest version of monorepo.

## [0.8.50] - 2025-09-08
- Minor fix in documentation
- Updated examples

## [0.8.49] - 2025-09-05
- Fixed token reducer now has a safety margin of 10% less did not work.

## [0.8.48] - 2025-09-05
- Add documentation on language models to markdown

## [0.8.47] - 2025-09-05
- Removed old code
- Fixed small bugs in history manager & set the hallucination to use gpt4o as default.

## [0.8.46] - 2025-09-04
- Bugfix for hostname identification inside Unique cluster in `unique_settings.py`

## [0.8.45] - 2025-09-04
- Introduce handoff capability to tools. with the `takes_control()` function.

## [0.8.44] - 2025-09-03
- Refine `EndpointClass` and create `EndpointRequestor`

## [0.8.43] - 2025-09-03
- Add alias for `UniqueSettings` api base `API_BASE`

## [0.8.42] - 2025-09-02
- updated schema of `chunk_relevancy_sorter`

## [0.8.41] - 2025-09-02
- Make A2A tool auto register with tool factory

## [0.8.40] - 2025-09-02
- Add frontend compatible type for pydantic BaseModel types in pydantic BaseModels

## [0.8.39] - 2025-09-02
- include `get_async_openai_client`

## [0.8.38] - 2025-09-01
- Sanitize documentation

## [0.8.37] - 2025-09-01
- Adapt defaults and json-schema in `LanguageModelInfo`

## [0.8.36] - 2025-09-01
- Added dependency `Pillow` and `Platformsdir`

## [0.8.35] - 2025-09-01
- Initial toolkit documentation (WIP)

## [0.8.34] - 2025-09-01
- Automatic initializations of services and event generator

## [0.8.33] - 2025-08-31
- fixed tool for `web_search`

## [0.8.32] - 2025-08-30
- moved over general packages for `web_search`

## [0.8.31] - 2025-08-29
- Add various openai models to supported model list
  - o1
  - o3
  - o3-deep-research
  - o3-pro
  - o4-mini
  - o4-mini-deep-research
  - gpt-4-1-mini
  - gpt-4-1-nano

## [0.8.30] - 2025-08-28
- Added A2A manager

## [0.8.29] - 2025-08-28

- Include `MessageExecution` and `MessageLog` in toolkit

## [0.8.28] - 2025-08-28
- Fix paths for `sdk_url` and `openai_proxy` for localhost

## [0.8.27] - 2025-08-28
- Fixed function "create_async" in language_model.functions : "user_id" argument should be optional.

## [0.8.26] - 2025-08-27
- Optimized MCP manager

## [0.8.25] - 2025-08-27
- Load environment variables automatically from plattform dirs or environment
- General Endpoint definition utility
- Expose `LanguageModelToolDescription` and `LanguageModelName` directly
- Get initial debug information from chat payload

## [0.8.24] - 2025-08-27
- Optimized hallucination manager

## [0.8.23] - 2025-08-27
- Add MCP manager that handles MCP related logic

## [0.8.22] - 2025-08-26
- Add DeepSeek-R1, DeepSeek-V3.1, Qwen3-235B-A22B and Qwen3-235B-A22B-Thinking-2507 to supported model list

## [0.8.21] - 2025-08-26

- Fixed old (not used) function "create_async" in language_model.functions : The function always returns "
  Unauthorized" --> Added "user_id" argument to fix this.

## [0.8.20] - 2025-08-24
- Fixed forced-tool-calls
- Bump SDK version to support the latest features.

## [0.8.19] - 2025-08-24
- Enforce usage of ruff using pipeline

## [0.8.18] - 2025-08-22
- moved class variables into instance variables

## [0.8.17] - 2025-08-22
- fixed circular dependencies in tools

## [0.8.16] - 2025-08-19
- moved Hallucination evaluator into toolkit

## [0.8.15] - 2025-08-19
- Added history loading from database for History Manager

## [0.8.14] - 2025-08-19
- Including GPT-5 series deployed via LiteLLM into language model info

## [0.8.13] - 2025-08-18
- Adding initial versions of
  - Evaluation Manager
  - History Manager
  - Postprocessor Manager
  - Thinking Manager
- Updated tool manager

## [0.8.12] - 2025-08-18
- Fix no tool call respoonse in ChatMessage -> Open Ai messages translation
- Add simple append method to OpenAIMessageBuilder

## [0.8.11] - 2025-08-15
- Fix no tool call respoonse in ChatMessage -> Open Ai messages translation
- Add simple append method to OpenAIMessageBuilder

## [0.8.10] - 2025-08-15
- Add min and max temperature to `LanguageModelInfo`: temperature will be clamped to the min and max temperature
- Add default options to `LanguageModelInfo`: These are used by default

## [0.8.9] - 2025-08-15

- Reduce input token limits for `ANTHROPIC_CLAUDE_3_7_SONNET_THINKING`, `ANTHROPIC_CLAUDE_3_7_SONNET`,
  `ANTHROPIC_CLAUDE_OPUS_4` and `ANTHROPIC_CLAUDE_SONNET_4` to 180_000 from 200_000

## [0.8.8] - 2025-08-11

- Make chat service openai stream response openai compatible
- Make `ChatMessage` openai compatible

## [0.8.7] - 2025-08-11
- Make chat service openai compatible
- Fix some bugs
- Make OpenAIMessageBuilder more congruent to MessageBuilder

## [0.8.6] - 2025-08-11
- Add GPT-5, GPT-5_MINI, GPT-5_NANO, GPT-5_CHAT to supported models list

## [0.8.5] - 2025-08-06
- Refactored tools to be in the tool-kit

## [0.8.4] - 2025-08-06
- Make unique settings compatible with legacy environment variables

## [0.8.3] - 2025-08-05
- Expose threshold field for search.

## [0.8.2] - 2025-08-05
- Implement overloads for services for clearer dev experience
- Proper typing for SSE event handling
- Enhanced unique settings. Expose usage of default values in logs
- SDK Initialization from unique settings
- Add utilities for to run llm/agent flows for devs

## [0.8.1] - 2025-08-05
- Bump SDK version to support the latest features.

## [0.8.0] - 2025-08-04
- Add MCP support

## [0.7.42] - 2025-08-01
- Added tool definitions

## [0.7.41] - 2025-07-31
- Add new chat event attribute indicating tools disabled on a company level

## [0.7.40] - 2025-07-30
- Remove `GEMINI_2_5_FLASH_PREVIEW_0417` model

## [0.7.39] - 2025-07-28
- Implement utitilites to work with openai client
- Implement utitilites to work with langchain llm

## [0.7.38] - 2025-07-25
- Fix issues with secret strings in settings

## [0.7.36] - 2025-07-25
- Fix issues with settings
- Add testing to unique settings

## [0.7.35] - 2025-07-23
- Bump version of SDK to have access to the latest features and fixes

## [0.7.34] - 2025-06-25
- Fix incorrect mapping in `ContentService` for the `search_content` function when mapping into `ContentChunk` object

## [0.7.33] - 2025-06-25
- Update reference post-processing

## [0.7.32] - 2025-06-24
- Create `classmethod` for `LanguageModelMessages` to load raw messages to root

## [0.7.31] - 2025-06-20

- Add typings to references in payload from `LanguageModelStreamResponseMessage`
- Add `original_index` to the base reference to reflect updated api

## [0.7.30] - 2025-06-20

- Adding litellm models `litellm:gemini-2-5-flash`, `gemini-2-5-flash-lite-preview-06-17`, `litellm:gemini-2-5-pro`,
  `litellm:gemini-2-5-pro-preview-06-05`

## [0.7.29] - 2025-06-19
- Fix typehintin in services
- Error on invalid initialization

## [0.7.28] - 2025-06-17

- Revert default factory change on `ChatEventPayload` for attribute `metadata_filter` due to error in
  `backend-ingestion` on empty dict

## [0.7.27] - 2025-06-16
- Introduce a protocol for `complete_with_references` to enable testable services
- Rename/Create functions `stream_complete` in chat service and llm service accordingly

## [0.7.26] - 2025-06-05
- Add `scope_rules` to `ChatEventPayload`
- Added `UniqueQL` compiler and pydantic classes for `UniqueQL`. Note this is functionally equivalent but not identical
  to `UQLOperator` or `UQLCombinator` in `unique_sdk`.

## [0.7.25] - 2025-06-05
- Adding models `AZURE_GPT_41_MINI_2025_0414`, `AZURE_GPT_41_NANO_2025_0414`

## [0.7.24] - 2025-05-30
- Adding litellm model `gemini-2-5-flash-preview-05-20`, `anthropic-claude-sonnet-4` and `anthropic-claude-opus-4`

## [0.7.23] - 2025-05-22
- add encoder for `AZURE_GPT_4o_2024_1120` to be part of the encoder function returns.

## [0.7.22] - 2025-05-22

- `messages` are now always serialized by alias. This affects `LanguageModelService.complete` and
  `LanguageModelService.complete_async`.

## [0.7.21] - 2025-05-21
- Extend the update the `ChatMessage` object to include the `Reference` object introduced in the public api

## [0.7.20] - 2025-05-21
- Deprecate `LanguageModelTool` and associated models in favor of `LanguageModelToolDescription`

## [0.7.19] - 2025-05-20
- Extend the `MessageBuilder` to allow for appending any `LanguageModelMessage`

## [0.7.18] - 2025-05-20
- Add the possibility to specify metadata when creating or updating a Content.

## [0.7.17] - 2025-05-16
- Change inheritance hierarchy of events for easier deprecation

## [0.7.16] - 2025-05-16
- Add classmethods to create LanguageModelAssistatnMessage from functions and stream response
- Add completion like method to chat
- Add protocol for completion like method

## [0.7.15] - 2025-05-13
- Add the possibility to specify ingestionConfig when creating or updating a Content.

## [0.7.14] - 2025-05-08
- Fix bug not selecting the correct llm
- Add LMI type for flexible init of LanguageModelInfo
- Replace LanguageModel with LanguageModelInfo in hallucination check

## [0.7.13] - 2025-05-07

- Adding litellm models `litellm:anthropic-claude-3-7-sonnet`, `litellm:anthropic-claude-3-7-sonnet-thinking`,
  `litellm:gemini-2-0-flash`, `gemini-2-5-flash-preview-04-17` , `litellm:gemini-2-5-pro-exp-03-25`

## [0.7.12] - 2025-05-02
- add `AZURE_o3_2025_0416` and `AZURE_o4_MINI_2025_0416` as part of the models

## [0.7.11] - 2025-04-28

- Removing `STRUCTURED_OUTPUT` capability from `AZURE_GPT_35_TURBO_0125`, `AZURE_GPT_4_TURBO_2024_0409` and
  `AZURE_GPT_4o_2024_0513`

## [0.7.10] - 2025-04-22
- Deprecate internal variables of services

## [0.7.9] - 2025-04-17
- add `AZURE_GPT_41_2025_0414` as part of the models

## [0.7.8] - 2025-04-11
- add `AZURE_GPT_4o_2024_1120` as part of the models

## [0.7.7] - 2025-04-11
- Add tool choice parameter to chat event payload

## [0.7.6] - 2025-04-08
- De provisioning o1-preview

## [0.7.5] - 2025-04-07
- Skip None values when serializing to json schema for LanguageModelInfo

## [0.7.4] - 2025-03-20
- add `AZURE_GPT_45_PREVIEW_2025_0227` as part of the models

## [0.7.3] - 2025-03-20
- Enable handling tool calls in message builder

## [0.7.2] - 2025-03-17
- HotFix `ContentService.search_content_chunks` to use `chat_id` from event if provided.

## [0.7.1] - 2025-03-11

- Fix Breaking change: `ContentService.search_content_chunks` `ContentService.search_content_chunks` now accepts
  `chat_id` for the specific to handle chat_only instances

## [0.7.0] - 2025-03-11

- Fix the issue with `ShortTermMemoryService.create_memory_async` adding `self.chat_id` and `self.message_id` as part of
  the parameter.
- Breaking change: `ContentService.search_content_on_chat` now requires you pass in a `chat_id` for the specific chat
  instance

## [0.6.9] - 2025-03-11
- Add o1-preview as part of the language model info, make the name consistent across board.

## [0.6.8] - 2025-03-11
- Add `verify_request_and_construct_event` to `verification.py`

## [0.6.7] - 2025-03-10
- Extend language model message builder

## [0.6.6] - 2025-03-10
- Add o1, o1-mini and o3-mini models
- Remove deprecated gpt4 models
- Make token_limits and encoder a required attribute of LanguageModelInfo

## [0.6.5] - 2025-03-04
- Add `upload_content_from_bytes` to `ContentService`
- Add `download_content_to_bytes` to `ContentService`

## [0.6.3] - 2025-02-27

- Simplified imports for services. `from unique_toolkit.language_model import LanguageModelService` ->
  `from unique_toolkit import LanguageModelService` to reduce number of import lines.
- Add `builder` method to `LanguageModelMessages` class

## [0.6.2] - 2025-02-25
- Deprecate `LanguageModel` in favor of `LanguageModelInfo`
- `LanguageModelTokenLimits` properties become mandatory, initialization allows
  - init with `token_limit` and `fraction_input` or `input_token_limit` and `output_token_limit`
  - only `input_token_limit` and `output_token_limit` are members of model

## [0.6.1] - 2025-02-25

- [BREAKING] `LanguageModelService.stream_complete` and `LanguageModelService.stream_complete_async` are now moved to
  `ChatService.stream_complete` and `ChatService.stream_complete_async`. Correspondingly `assistant_message_id` and
  `user_message_id` are removed from `LanguageModelService`.
- Add `create_user_message` and `create_user_message_async` to `ChatService` (similar to `create_assistant_message` and
  `create_assistant_message_async`)

## [0.6.0] - 2025-02-21
- make for each domain, its base functionality accessible from `functions.py`
- make it possible to instantiate the domain services directly from different event types, inhereted from common
  `BaseEvent`
- extend the functionalities in the ShortTermMemoryService by adding the `find_latest_memory` and `create_memory`
  functions for sync and async usage
- remove logger dependency from service classes
- marked deprecated:
  - `from_chat_event` in ShortTermMemoryService, use `ShortTermMemoryService(event=event)` instead
  - `complete_async_util` in LanguageModelService, use `functions.complete_async` instead
  - `stream_complete_async` in LanguageModelService, use `stream_complete_to_chat_async` instead
  - `stream_complete` in LanguageModelService, use `stream_complete_to_chat` instead
  - `Event` and nested schemas in `app`, use `ChatEvent` and `ChatEventUserMessage`, `ChatEventAssistantMessage` and
    `ChatEventToolMessage` instead

## [0.5.56] - 2025-02-19
- Add `MessageAssessment` title field and change label values

## [0.5.55] - 2025-02-18
- Log `contentId` for better debugging

## [0.5.54] - 2025-02-10
- Add `created_at`, `completed_at`, `updated_at` and `gpt_request` to `ChatMessage` schema.

## [0.5.53] - 2025-02-01
- Correct `MessageAssessment` schemas

## [0.5.52] - 2025-02-01
- Add `MessageAssessment` schemas and functions to `ChatService` to handle message assessments.
- Fix `LanguageModelService.complete_async_util` to use the correct async method.

## [0.5.51] - 2025-01-30
- Add missing structured output arguments in complete_async

## [0.5.50] - 2025-01-30
- Add the possibility to define completion output structure through a pydantic class

## [0.5.49] - 2025-01-24
- Add `parsed` and `refusal` to `LanguageModelAssistantMessage` to support structured output

## [0.5.48] - 2025-01-19

- Added the possibility define tool parameters with a json schema (Useful when generating tool parameters from a
  pydantic object)

## [0.5.47] - 2025-01-07
- Added a message builder to build language model messages conveniently without importing all different messages.
- Move tool_calls to assistant message as not needed anywhere else.

## [0.5.46] - 2025-01-07

- Added `AZURE_GPT_35_TURBO_0125` as new model into toolkit.

## [0.5.45] - 2025-01-03
- Added `ShortTermMemoryService` class to handle short term memory.

## [0.5.44] - 2024-12-18
- Add `event_constructor` to `verify_signature_and_construct_event` to allow for custom event construction.

## [0.5.43] - 2024-12-13

- Add `Prompt` class to handle templated prompts that can be formatted into LanguageModelSystemMessage and
  LanguageModelUserMessage.

## [0.5.42] - 2024-12-11
- Update `LanguageModelTokenLimits` with fix avoiding floats for token

## [0.5.41] - 2024-12-11
- Update `LanguageModelTokenLimits` includes a fraction_input now to always have input/output token limits available.

## [0.5.40] - 2024-12-11

- Add `other_options` to `LanguageModelService.complete`, `LanguageModelService.complete_async`,
  `LanguageModelService.stream_complete` and `LanguageModelService.stream_complete_async`

## [0.5.39] - 2024-12-09
- Add `contentIds` to `Search.create` and `Search.create_async`
- Use `metadata_filter` from event in `ContentService.search_content_chunks` and
  `ContentService.async_search_content_chunks` as default.

## [0.5.38] - 2024-11-26
- Added string representation to `LanguageModelMessage` and `LanguageModelMessages` class

## [0.5.37] - 2024-11-26

- `content` parameter in `ChatService.modify_assistant_message` and `ChatService.modify_assistant_message_async` is now
  optional
- Added optional parameter `original_content` to `ChatService.modify_assistant_message` and
  `ChatService.modify_assistant_message_async`
- Added optional parameter `original_content` to `ChatService.create_assistant_message` and
  `ChatService.create_assistant_message_async`

## [0.5.36] - 2024-11-19
- Add possibility to return the response from the download file from chat request
- Add possibility to not specify a filename and use filename from response headers

## [0.5.35] - 2024-11-18

- Add the possibilty to upload files without triggering ingestion by setting `skip_ingestion` to `True` in
  `ContentService.upload_content`

## [0.5.34] - 2024-11-15
- Add `content_id_to_translate` to `EventAdditionalParameters`

## [0.5.33] - 2024-10-30
- Force randomizing tool_call_id. This is helpful to better identify the tool_calls.

## [0.5.32] - 2024-10-30
- Extending `LanguageModelName` with GPT-4o-2024-0806. This model is invoked using `AZURE_GPT_4o_2024_0806`.

## [0.5.31] - 2024-10-29

- Adding support for function calling. Assistant message for tool calls can be directly created with
  `LanguageModelFunctionCall.create_assistant_message_from_tool_calls`. Better separation of schemas for different types
  of `LanguageModelMessages`.

## [0.5.30] - 2024-10-28

- Correctly use `temperature` parameter in `LanguageModelService.complete` and `LanguageModelService.complete_async`
  methods

## [0.5.29] - 2024-10-28
- Allow numbers in `LanguageModelTool` name

## [0.5.28] - 2024-10-23

- Correctly use `temperature` parameter in `LanguageModelService.stream_complete` and
  `LanguageModelService.stream_complete_async` methods

## [0.5.27] - 2024-10-22
- Add encoder_name to to language model info
- Verify tool name for `LanguageModelTool` to conform with frontent requirements.
- Add `search_on_chat` to `ContentService`

## [0.5.26] - 2024-10-16
- Bump `unique_sdk` version

## [0.5.25] - 2024-09-26
- Add `evaluators` for hallucination and context relevancy evaluation

## [0.5.24] - 2024-09-26

- Add `originalText` to `_construct_message_modify_params` and `_construct_message_create_params`. This addition makes
  sure that the `originalText` on the database is populated with the `text`

## [0.5.23] - 2024-09-23

- Add `set_completed_at` as a boolen parameter to the following functions: `modify_user_message`,
  `modify_user_message_async`, `modify_assistant_message`, `modify_assistant_message_async`, `create_assistant_message`
  and `create_assistant_message`. This parameter allows the `completedAt` timestamp on the database to be updated when
  set to True.

## [0.5.22] - 2024-09-17
- Add `LanguageModelToolMessage` as additional `LanguageModelMessage`

## [0.5.21] - 2024-09-16
- Add `tool` as new role to `ChatMessage`, as well as `tool_calls` and `tool_call_id` as additional parameters

## [0.5.20] - 2024-09-16

- `LanguageModelService` now supports complete_util_async that can be called without instantiating the class, currently
  being used in the Hallucination service and evaluation API

## [0.5.19] - 2024-09-11

- `LanguageModelMessage` now supports content as a list of dictionary. Useful when adding image_url content along user
  message.

## [0.5.18] - 2024-09-03
- Adds option to use `metadata_filter` with search.
- Adds `user_metadata`, `tool_parameters` and `metadata_filter` to `EventPayload`.
- Adds `update_debug_info` and `modify_user_message` (and the corresponding `async` variants) to `ChatService`.

## [0.5.17] - 2024-08-30
- Add option to initiate `LanguageModel` with a string.
- Add option to call `LanguageModelService` functions also with a string instead of `LanguageModelName` enum for
  parameter `model_name`.

## [0.5.16] - 2024-08-29
- Fix `ContentService.upload_content` function.

## [0.5.15] - 2024-08-27
- Possibility to specify root directory in `ContentService.download_content`

## [0.5.14] - 2024-08-26
- Add AZURE_GPT_4o_MINI_2024_0718 to language model infos

## [0.5.13] - 2024-08-19
- Added `items` to `LanguageModelToolParameterProperty` schema to add support for parameters with list types.
- Added `returns` to `LanguageModelTool` schema to describe the return types of tool calls.

## [0.5.12] - 2024-08-7
- added `completedAt` datetime to `unique_sdk.Message.modify` and `unique_sdk.Message.modify_async`
- added `original_text` and `language` to `EventUserMessage`

## [0.5.11] - 2024-08-6
- made all domain specific functions and classes directly importable from `unique_toolkit.[DOMAIN_NAME]`
- renamed `RerankerConfig` to `ContentRerankerConfig`
- renamed `get_cosine_similarity` to `calculate_cosine_similarity` and moved it to `unique_toolkit.embedding.utils`
- moved `calculate_tokens` from `unique_toolkit.content.utils` to `unique_toolkit.embedding.utils`
- disabled deprecation warning in `LanguageModel`
- added `additional_parameters` to event
- removed `ChatState` and use `Event` instead

## [0.5.10] - 2024-08-6
- fix content schema

## [0.5.9] - 2024-08-6
- added `created_at` and `updated_at` to content schema

## [0.5.8] - 2024-08-1
- `RerankerConfig` serialization alias added

## [0.5.7] - 2024-07-31

- Replace mocked async service calls with async calls in `unique_sdk`
- Change async methods name from `async_*` to `*_async`
- Remove `chat_only` and `scope_ids` attributes from `ChatState` class
- Replace `AsyncExecutor` by simpler utility function `run_async_tasks_parallel`

## [0.5.6] - 2024-07-30

- Bug fix: `ContentService.search_content_chunks` and it's `async` equivalent now accept `None` as a valid parameter
  value for `scope_ids`.

## [0.5.5] - 2024-07-30
- Added parameters to `ContentService.search_content_chunks` and `ContentService.async_search_content_chunks`
  - `reranker_config` to optinally rerank the search results
  - `search_language` to specify a language for full-text-search

## [0.5.4] - 2024-07-26
- correct ChatMessage schema

## [0.5.3] - 2024-07-25
- downgrade numpy version to ^1.26.4 to be compatible with langchain libraries (require numpy<2.0)

## [0.5.2] - 2024-07-25
- correct event schema

## [0.5.1] - 2024-07-23
- correct documentation

## [0.5.0] - 2024-07-23
### Added
- Added `unique_toolkit.app` module with the following components:
  - `init_logging.py` for initializing the logger.
  - `init_sdk.py` for initializing the SDK with environment variables.
  - `schemas.py` containing the Event schema.
  - `verification.py` for verifying the endpoint secret and constructing the event.

- Added `unique_toolkit.chat` module with the following components:
  - `state.py` containing the `ChatState` class.
  - `service.py` containing the `ChatService` class for managing chat interactions.
  - `schemas.py` containing relevant schemas such as `ChatMessage`.
  - `utils.py` with utility functions for chat interactions.

- Added `unique_toolkit.content` module with the following components:
  - `service.py` containing the `ContentService` class for interacting with content.
  - `schemas.py` containing relevant schemas such as `Content` and `ContentChunk`.
  - `utils.py` with utility functions for manipulating content objects.

- Added `unique_toolkit.embedding` module with the following components:
  - `service.py` containing the `EmbeddingService` class for working with embeddings.
  - `schemas.py` containing relevant schemas such as `Embeddings`.

- Added `unique_toolkit.language_model` module with the following components:
  - `infos.py` containing information on language models deployed on the Unique platform.
  - `service.py` containing the `LanguageModelService` class for interacting with language models.
  - `schemas.py` containing relevant schemas such as `LanguageModelResponse`.
  - `utils.py` with utility functions for parsing language model output.

## [0.0.2] - 2024-07-10
- Initial release of `unique_toolkit`.
