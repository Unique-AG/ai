# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.20.0...unique-sdk-v2026.20.0) (2026-05-08)


### Features

* Add RERUN_ROW action to MagicTableAction enum ([#970](https://github.com/Unique-AG/ai/issues/970)) ([7455938](https://github.com/Unique-AG/ai/commit/74559388a1b021dd53a7655c3d7b75f6e49f53d1))
* add User.get_by_id method to retrieve user by ID UN-17073 ([#1013](https://github.com/Unique-AG/ai/issues/1013)) ([50fd144](https://github.com/Unique-AG/ai/commit/50fd144fb7e8c9af78b0bc30c49257b229fc35ab))
* **cli:** add MCP tool call command to unique-cli ([#1325](https://github.com/Unique-AG/ai/issues/1325)) ([4eec9b7](https://github.com/Unique-AG/ai/commit/4eec9b7cfd1c55721280a6085606215cde04e499))
* commands for local ci checks ([#908](https://github.com/Unique-AG/ai/issues/908)) ([25af0f5](https://github.com/Unique-AG/ai/commit/25af0f59b752f54815f726b1ee0d00f19ff3fbbf))
* **sdk:** Add Analytics Order API and run utility ([#1503](https://github.com/Unique-AG/ai/issues/1503)) ([01f37aa](https://github.com/Unique-AG/ai/commit/01f37aa3666b66a19cb22a5636c734f57a1d0f17))
* **sdk:** add elicit CLI command group and agent skill ([#1443](https://github.com/Unique-AG/ai/issues/1443)) ([5549f20](https://github.com/Unique-AG/ai/commit/5549f20d852ddd20bc267f32907d6058fe23dd66))
* **sdk:** Add get_spaces API method to list spaces with filtering ([#1437](https://github.com/Unique-AG/ai/issues/1437)) ([eeb04ea](https://github.com/Unique-AG/ai/commit/eeb04ea3bce41a459c072b58dfd93e9819723157))
* **sdk:** add message correlation [UN-16427] ([#959](https://github.com/Unique-AG/ai/issues/959)) ([e3f2282](https://github.com/Unique-AG/ai/commit/e3f228205af7e7a1c4f63077387d78a51997cc99))
* **sdk:** add missing docs ([#1500](https://github.com/Unique-AG/ai/issues/1500)) ([73c0dcd](https://github.com/Unique-AG/ai/commit/73c0dcd7d37deb36a55d1483f64e6ae09fdb9df5))
* **sdk:** Add Module API resource for managing assistant modules ([#1471](https://github.com/Unique-AG/ai/issues/1471)) ([b376a1d](https://github.com/Unique-AG/ai/commit/b376a1d460d52f2d34181dda801fa63111b43909))
* **sdk:** add scheduled tasks API resource and CLI commands ([#1358](https://github.com/Unique-AG/ai/issues/1358)) ([f45941b](https://github.com/Unique-AG/ai/commit/f45941b9cecb148244a0b6087a0255f0e87397a1))
* **sdk:** add update ingestion state sdk function [UN-16631] ([#952](https://github.com/Unique-AG/ai/issues/952)) ([b4dd0fa](https://github.com/Unique-AG/ai/commit/b4dd0fad0bce1162ea557d9fc517cdcd555aca16))
* **sdk:** add WebSearch / WebCrawl resources and unique-cli web-search ([#1611](https://github.com/Unique-AG/ai/issues/1611)) ([2cc2fab](https://github.com/Unique-AG/ai/commit/2cc2fab0c3e19806c1797ae7b169fd71acee35e4))
* **sdk:** Added searchtype `FULL_TEXT` and `POSTGRES_FULL_TEXT` ([#924](https://github.com/Unique-AG/ai/issues/924)) ([7208da1](https://github.com/Unique-AG/ai/commit/7208da15b80079fe37b496d0c9afc1310701b022))
* **sdk:** align AgenticTable with public magic-table API [UN-19885] ([#1467](https://github.com/Unique-AG/ai/issues/1467)) ([f13afea](https://github.com/Unique-AG/ai/commit/f13afea2bc7f00a6d832980cf7507bf9bf03fe9f))
* **sdk:** allow download_content to write to caller-specified target_path ([#1585](https://github.com/Unique-AG/ai/issues/1585)) ([df57cc9](https://github.com/Unique-AG/ai/commit/df57cc9610d7065fd0292a6b4211406d37c3e89c))
* **sdk:** benchmarking script ([#1282](https://github.com/Unique-AG/ai/issues/1282)) ([244cec6](https://github.com/Unique-AG/ai/commit/244cec662889a1ad6dd89bcb0a5ef220468ccbe2))
* **sdk:** Briefing API resource and PUT HTTP support ([#1574](https://github.com/Unique-AG/ai/issues/1574)) ([23455e7](https://github.com/Unique-AG/ai/commit/23455e7e90792767b41e43122230b52f6ef12975))
* **sdk:** create chat fucntion ([#1277](https://github.com/Unique-AG/ai/issues/1277)) ([a866a12](https://github.com/Unique-AG/ai/commit/a866a12a02981bd8c74ba529c9f6e173c50fea35))
* **sdk:** create folders by scope id [UN-17011] ([#1012](https://github.com/Unique-AG/ai/issues/1012)) ([5fb60b7](https://github.com/Unique-AG/ai/commit/5fb60b7e37ffe85098dcfbf276ea8a59fc2feb5a))
* **sdk:** delete space [UN-16434] ([#930](https://github.com/Unique-AG/ai/issues/930)) ([d5407a1](https://github.com/Unique-AG/ai/commit/d5407a1d93ddec34e939518b2236e1db41220388))
* **sdk:** implement elicitation functions [UN-16334] ([#920](https://github.com/Unique-AG/ai/issues/920)) ([bca3aab](https://github.com/Unique-AG/ai/commit/bca3aab5f03f2bfc2962ad62b23911efae07c34a))
* **sdk:** rewrite blob upload URLs via INGESTION_UPLOAD_API_URL_INTERNAL ([#1588](https://github.com/Unique-AG/ai/issues/1588)) ([5783fb5](https://github.com/Unique-AG/ai/commit/5783fb5c4d4053ed83a505ce75b3ca271d8d1757))
* **sdk:** search qdrant params ([#1225](https://github.com/Unique-AG/ai/issues/1225)) ([10cff12](https://github.com/Unique-AG/ai/commit/10cff126a11fd618e8fa8ae525034b30a4959e55))
* **sdk:** ship CLI as part of unique_sdk (experimental) ([#1248](https://github.com/Unique-AG/ai/issues/1248)) ([bf947e8](https://github.com/Unique-AG/ai/commit/bf947e825e1cd16d25f120a3d896b481c926e090))
* **sdk:** UN-15977 add ToolCall API resource ([#1102](https://github.com/Unique-AG/ai/issues/1102)) ([3fda725](https://github.com/Unique-AG/ai/commit/3fda725bbd65efa77a95b5d1d83d7f9ce288a192))
* **sdk:** update assistant function ([#1108](https://github.com/Unique-AG/ai/issues/1108)) ([e16a138](https://github.com/Unique-AG/ai/commit/e16a1383c452384c689be685680aeba2bf12343e))
* **unique-sdk:** derive preview-PDF blob name from content id ([#1532](https://github.com/Unique-AG/ai/issues/1532)) ([d36d130](https://github.com/Unique-AG/ai/commit/d36d130e6c38f781d767c2a53c6bf2ac933c1ccc))
* **unique-skill:** including skill choices to payload ([#1636](https://github.com/Unique-AG/ai/issues/1636)) ([36e8275](https://github.com/Unique-AG/ai/commit/36e82750e89d350e2293b8144035bac903829445))


### Bug Fixes

* Add Literals to elicitation ([#972](https://github.com/Unique-AG/ai/issues/972)) ([f4fccfb](https://github.com/Unique-AG/ai/commit/f4fccfb3eec380f98f56fa666fa7695ca5402a84))
* **ci:** exempt workspace packages from uv exclude-newer cutoff ([#1455](https://github.com/Unique-AG/ai/issues/1455)) ([28af03b](https://github.com/Unique-AG/ai/commit/28af03b8edbadeb5e5059540733eba16567aacf8))
* **cli:** enforce .unique-search.json scope across search, ls, and write ops ([#1627](https://github.com/Unique-AG/ai/issues/1627)) ([7f0e6ee](https://github.com/Unique-AG/ai/commit/7f0e6eeeb2f67e8cf6ecc131110bc6287755b9b8))
* formating and dates on all changelogs ([#1114](https://github.com/Unique-AG/ai/issues/1114)) ([9a7998b](https://github.com/Unique-AG/ai/commit/9a7998b9617ee88698385537c2ecde0ab30366f4))
* resolve CodeQL alerts and fix gitignore negation for uv.lock ([#1408](https://github.com/Unique-AG/ai/issues/1408)) ([0969aa0](https://github.com/Unique-AG/ai/commit/0969aa07edb1b35a13dae13a98d9822a76278af9))
* **sdk:** correct typing for integrated stream completion endpoint (UN-18109) ([#1193](https://github.com/Unique-AG/ai/issues/1193)) ([943ab57](https://github.com/Unique-AG/ai/commit/943ab579aa37c8e64574c201b76c9d0199ab0c4a))
* **sdk:** make UNIQUE_API_KEY and UNIQUE_APP_ID optional in unique-cli ([#1428](https://github.com/Unique-AG/ai/issues/1428)) ([3412f82](https://github.com/Unique-AG/ai/commit/3412f829c8fce3ca6503fb1aef56265c82a336ee))
* **sdk:** replace sync-in-async blocking calls in AgenticTable and file_io ([#1372](https://github.com/Unique-AG/ai/issues/1372)) ([1ad25a0](https://github.com/Unique-AG/ai/commit/1ad25a0374da6ee644bbb4c4619ecbb6b6f135d2))
* **sdk:** tolerate MCP responses missing optional fields ([#1463](https://github.com/Unique-AG/ai/issues/1463)) ([620775b](https://github.com/Unique-AG/ai/commit/620775b69d8a8f11ba947bf9ab8d878b72729e1e))
* **sdk:** UN-19815 elicitation visibility workaround + CLI fixes ([#1459](https://github.com/Unique-AG/ai/issues/1459)) ([9ba8dcd](https://github.com/Unique-AG/ai/commit/9ba8dcdbbe168cac06f5fd37d3d8bed6838ef4ff))
* **sdk:** use async HTTP path in responses_stream_async ([#1368](https://github.com/Unique-AG/ai/issues/1368)) ([f3b7dfe](https://github.com/Unique-AG/ai/commit/f3b7dfe79afa81af3ff679408c3b4568fcdae78c))
* **unique-sdk:** UN-15976 resolve all basedpyright errors under standard mode ([#1192](https://github.com/Unique-AG/ai/issues/1192)) ([a5d3d91](https://github.com/Unique-AG/ai/commit/a5d3d91a181b2b199b8dde4276b9f2c116f0c42f))
* **unique-sdk:** UN-15976 upgrade basedpyright to recommended mode with zero errors ([#1196](https://github.com/Unique-AG/ai/issues/1196)) ([8afc0ef](https://github.com/Unique-AG/ai/commit/8afc0ef3548d3f4a4d8bd9bc65dfe67cc6f55ebf))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))
* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v2026.18.0...unique-sdk-v2026.20.0) (2026-05-08)


### Features

* **sdk:** Add Analytics Order API and run utility ([#1503](https://github.com/Unique-AG/ai/issues/1503)) ([01f37aa](https://github.com/Unique-AG/ai/commit/01f37aa3666b66a19cb22a5636c734f57a1d0f17))
* **sdk:** add missing docs ([#1500](https://github.com/Unique-AG/ai/issues/1500)) ([73c0dcd](https://github.com/Unique-AG/ai/commit/73c0dcd7d37deb36a55d1483f64e6ae09fdb9df5))
* **sdk:** Add Module API resource for managing assistant modules ([#1471](https://github.com/Unique-AG/ai/issues/1471)) ([b376a1d](https://github.com/Unique-AG/ai/commit/b376a1d460d52f2d34181dda801fa63111b43909))
* **sdk:** add WebSearch / WebCrawl resources and unique-cli web-search ([#1611](https://github.com/Unique-AG/ai/issues/1611)) ([2cc2fab](https://github.com/Unique-AG/ai/commit/2cc2fab0c3e19806c1797ae7b169fd71acee35e4))
* **sdk:** allow download_content to write to caller-specified target_path ([#1585](https://github.com/Unique-AG/ai/issues/1585)) ([df57cc9](https://github.com/Unique-AG/ai/commit/df57cc9610d7065fd0292a6b4211406d37c3e89c))
* **sdk:** Briefing API resource and PUT HTTP support ([#1574](https://github.com/Unique-AG/ai/issues/1574)) ([23455e7](https://github.com/Unique-AG/ai/commit/23455e7e90792767b41e43122230b52f6ef12975))
* **sdk:** rewrite blob upload URLs via INGESTION_UPLOAD_API_URL_INTERNAL ([#1588](https://github.com/Unique-AG/ai/issues/1588)) ([5783fb5](https://github.com/Unique-AG/ai/commit/5783fb5c4d4053ed83a505ce75b3ca271d8d1757))
* **unique-sdk:** derive preview-PDF blob name from content id ([#1532](https://github.com/Unique-AG/ai/issues/1532)) ([d36d130](https://github.com/Unique-AG/ai/commit/d36d130e6c38f781d767c2a53c6bf2ac933c1ccc))
* **unique-skill:** including skill choices to payload ([#1636](https://github.com/Unique-AG/ai/issues/1636)) ([36e8275](https://github.com/Unique-AG/ai/commit/36e82750e89d350e2293b8144035bac903829445))


### Bug Fixes

* **cli:** enforce .unique-search.json scope across search, ls, and write ops ([#1627](https://github.com/Unique-AG/ai/issues/1627)) ([7f0e6ee](https://github.com/Unique-AG/ai/commit/7f0e6eeeb2f67e8cf6ecc131110bc6287755b9b8))


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-sdk-v0.11.12...unique-sdk-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [0.11.12] - 2026-04-22
- `AgenticTable.GetSheetData`: add `includeSheetMetadata` and `includeRowMetadata` (optional GET query params; `includeRowMetadata` for `GET /magic-table/{tableId}` aligns with in-flight public API work)
- Align other `AgenticTable` request/response types with the public magic-table REST contract (`2023-12-06` / `node-chat`): `RowVerificationStatus` uses `NEEDS_REVIEW` to match `MagicTableRowStatus`; `MagicTableAction` adds `InsertRow` and `GenerateOverview`; `bulk_update_status` adds optional `locked`; `SetArtifact` optional `name`/`mimeType` and `MagicTableArtifactType` including `AGENTIC_REPORT`; `set_activity` returns `MagicTableActivityResponse`, `set_artifact` returns `ColumnMetadataUpdateStatus`; extend cell/sheet TypedDicts (`metaData`, `rowMetadata`, `magicTableSheetMetadata`, optional `chatId` / `magicTableRowCount`); export `AgenticTableCellMetaData`, `MagicTableActivityResponse`, `MagicTableArtifactType`, `MagicTableMetadataEntry`
- Docs: update `agentic_table` reference for the above; add test coverage for `includeSheetMetadata` / `includeRowMetadata` on `get_sheet_data`

## [0.11.11] - 2026-04-22
- Add `Space.get_spaces` / `Space.get_spaces_async` to list spaces with optional name filter and skip/take pagination

## [0.11.10] - 2026-04-21
- Fix `unique-cli mcp` crashing with `AttributeError: isError` on spec-compliant `CallToolResult` responses that only include `content`. `format_mcp_response` now reads `isError`, `name`, and `mcpServerId` defensively via `getattr(..., default)` and accepts a keyword-only `tool_name` fallback so the header stays informative when the server omits `name`
- `cmd_mcp` now threads the parsed payload name into `format_mcp_response` and wraps the final format step in a defensive `try/except` that prints the raw response payload instead of a traceback if the formatter ever errors
- Mark `MCP.isError`, `MCP.name`, `MCP.mcpServerId` as `NotRequired` on the response type to match the MCP spec and the Unique backend's observed behaviour (typing-only change)

## [0.11.9] - 2026-04-21
- Docs: update the `unique-cli-elicitation` skill to require both `--chat-id "$UNIQUE_CHAT_ID"` and `--message-id "$UNIQUE_MESSAGE_ID"` on every `elicit ask` call, explain that every elicitation is anchored to a `(chatId, messageId)` pair in the backend, and document the two new env vars agents should always forward

## [0.11.8] - 2026-04-21
- Workaround for UN-19815: `elicit ask` / `elicit create` now wrap the elicitation in a short-lived placeholder "thinking" timeline (a placeholder `ASSISTANT` message + a `RUNNING` `MessageLog` step) so the chat UI actually renders the elicitation while it is pending. The placeholder is torn down automatically (collapsed or deleted) when the user responds, on timeout, on API error, or on Ctrl-C
- Add `--visible` / `--no-visible`, `--assistant-id`, `--placeholder-text`, `--cleanup` flags to `elicit ask` and `elicit create` in both the one-shot CLI and the REPL shell. The workaround is enabled by default whenever `--chat-id` is passed and `--message-id` is not; pass `--no-visible` to opt out once the UN-19815 UI fix lands
- `elicit wait` and `elicit respond` now auto-clean any placeholder a prior `elicit create --visible` left behind, by reading the placeholder ids back from the elicitation's `metadata`
- Serialize `completedAt` as an ISO-8601 UTC string (not a raw `datetime`) when collapsing the visibility placeholder via `Message.modify`, so the `PATCH /messages/{id}` body is accepted by the backend; without this the placeholder would stay visually "running" after the user responded
- Fix `elicit pending` crashing with `AttributeError: 'list' object has no attribute 'get'` — the backend returns a raw JSON array; both list and dict shapes are now accepted
- Fix `elicit wait` / `elicit ask` never terminating when the user answers — `ACCEPTED` and `REJECTED` are now recognised as terminal statuses alongside `RESPONDED` / `DECLINED` / `CANCELLED` / `EXPIRED` / `COMPLETED`
- Accept `REJECT` as a valid `elicit respond --action` value (forwarded to the backend as `REJECT`)
- Update the `unique-cli-elicitation` skill and the CLI docs page with the new flags and a note on when to turn the workaround off

## [0.11.7] - 2026-04-20
- Chore: exempt `unique-sdk` from the workspace root `exclude-newer` cutoff so recent SDK releases resolve correctly under `UV_NO_SOURCES=1`

## [0.11.6] - 2026-04-20
- Add `mimeType` field to `Content`

## [0.11.5] - 2026-04-16
- Add `elicit` CLI command group with `ask`, `create`, `pending`, `get`, `wait`, `respond` subcommands for both one-shot and interactive REPL modes, wrapping the existing `Elicitation` API resource
- Add `elicit ask` convenience command that creates a FORM elicitation and blocks until the user responds, declines, cancels, or the request expires
- Add formatting helpers for elicitation display (detail view, pending list, response result)
- Add agent skill for elicitation (`unique-cli-elicitation`) so agents route user-facing questions through the platform UI instead of asking in plain chat
- Add `CLI > Elicitation` documentation page and expose it in the mkdocs nav

## [0.11.4] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [0.11.3] - 2026-04-14
- Make `UNIQUE_API_KEY` and `UNIQUE_APP_ID` optional in the CLI — not needed on localhost or in a secured cluster

## [0.11.2] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [0.11.1] - 2026-04-09
- Fix stack trace exposure in custom-assistant example: return generic error messages instead of `str(e)` in HTTP responses

## [0.11.0] - 2026-04-09
- Widen `openai` dependency upper bound from `<2` to `<3` to allow openai SDK v2.x (required for litellm security fix)

## [0.10.101] - 2026-04-06
- Fix all `async def` methods in `AgenticTable` that incorrectly called synchronous `_static_request` instead of `await _static_request_async`, blocking the event loop
- Fix `wait_for_ingestion_completion` to use `Content.search_async` instead of synchronous `Content.search`

## [0.10.100] - 2026-04-06
- Fix `Integrated.responses_stream_async` blocking the asyncio event loop by calling synchronous `_static_request` instead of `await _static_request_async` — concurrent coroutines (STM lookups, file downloads, other API calls) were starved for 60-75s per LLM call

## [0.10.99] - 2026-04-02
- Add `ScheduledTask` API resource with full CRUD operations (create, list, retrieve, modify, delete) and async variants
- Add `schedule` CLI command group with `list`, `get`, `create`, `update`, `delete` subcommands for both one-shot and interactive REPL modes
- Add formatting helpers for scheduled task display (detail view and table view)
- Add agent skill for scheduled task management (`unique-cli-scheduled-tasks`)

## [0.10.98] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [0.10.97] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [0.10.96] - 2026-03-31
- Remove leftover `poetry` references from tox config, CONTRIBUTING.md, and tutorial docs — all replaced with `uv` equivalents

## [0.10.95] - 2026-03-30
- Add `mcp` command to the CLI for calling MCP server tools directly via JSON payload
- Support inline JSON, `--file`, and `--stdin` input modes for MCP tool payloads
- Add Claude Code skill for CLI MCP tool calls (`unique-cli-mcp`)

## [0.10.94] - 2026-03-30
- Add `Benchmarking` functions and script.

## [0.10.93] - 2026-03-25
- Add `Space.create_chat`

## [0.10.92] - 2026-03-19
- Add experimental CLI (`unique-cli`) for interactive file exploration of the Unique knowledge base
- Add `click` as a required dependency for the CLI
- Add Claude Code skills for CLI file management and search

## [0.10.91] - 2026-03-17
- Chore: switch basedpyright to `recommended` mode with zero errors/warnings
- Refactor: replace deprecated `typing` aliases (`Optional`, `List`, `Dict`, `Type`, `typing.Mapping`, `typing.Iterator`) with modern PEP 585/604 equivalents
- Refactor: rename `_ApiVersion` → `ApiVersion`; use `inspect.iscoroutinefunction` instead of deprecated `asyncio.iscoroutinefunction`
- Fix: use `list_result.data` instead of dict-key access in `chat_history` to access typed `ListObject` response

## [0.10.90] - 2026-03-17
- Add `qdrantParams` to `Search.create` for configuring Qdrant search parameters (hnsw_ef, exact, quantization, consistency)

## [0.10.89] - 2026-03-16
- Add `usage: Integrated.Usage | None` field to `ResponsesStreamResult` TypedDict (UN-18040)

## [0.10.88] - 2026-03-12
- Add `MessageTool` API resource for node-chat `POST/GET /messages/tools` (batch create and get by messageIds). Enables toolkit and orchestrator to persist and load tool calls via a dedicated table.

## [0.10.87] - 2026-03-12
- Fix: resolve non-breaking basedpyright errors; modern typing in core modules (`__init__`, `_api_requestor`, `_http_client`)
- Fix: restore strict key access in `AgenticTable.set_multiple_cells` so missing required fields raise `ValueError` instead of silently defaulting (UN-17995)

## [0.10.86] - 2026-03-12
- Fix return type for `Integrated.chat_stream_completion` and `Integrated.chat_stream_completion_async` to correctly reflect `StreamCompletionResult` (message, toolCalls, usage) instead of `Message`

## [0.10.85] - 2026-03-10
- Examples: migrate custom-assistant from Poetry to uv with `src/` layout
- Examples: replace hardcoded credentials in custom-assistant with `os.getenv()` for env-based configuration
- Examples: fix Ollama import (`langchain.llms` → `langchain_community.llms`) and add langchain dependencies

## [0.10.84] - 2026-03-03
- Build: migrate from Poetry to uv (PEP 621 `pyproject.toml`, `uv.lock`)

## [0.10.83] - 2026-02-28
- Add `Space.update` method to update a space (assistant) configuration

## [0.10.82] - 2026-02-13
- Add `User.get_by_id` method to retrieve a user by their ID

## [0.10.81] - 2026-02-13
- Add documentation versioning support using `mike`
- Add versioned documentation build and deploy workflows

## [0.10.80] - 2026-02-12
- Add support for creating folders by scope using `parentScopeId` and `relativePaths` parameters in `Folder.create_paths`

## [0.10.79] - 2026-02-05
- Add update_ingestion_state function to update content ingestion state.

## [0.10.78] - 2026-02-05
- Internal Improvements.

## [0.10.77] - 2026-02-05
- Add `RERUN_ROW` action to `MagicTableAction` enum for targeted row re-execution in Agentic Tables

## [0.10.76] - 2026-02-05
- Use literals for action source and mode in Elicitation for better API clarity

## [0.10.75] - 2026-02-02
- Add correlation parameter to Message.create for linking messages to parent messages in other chats.
- Add correlation parameter to Space.create_message and send_message_and_wait_for_completion utility.

## [0.10.74] - 2026-01-22
- Add delete space function.

## [0.10.73] - 2026-01-21
- added searchtype `FULL_TEXT` and `POSTGRES_FULL_TEXT`

## [0.10.72] - 2026-01-20
- Expose elicitation functions [BETA feature].

## [0.10.71] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [0.10.70] - 2026-01-16
- Adding additional parameters `isQueueable`, `executionOptions` and `progressTitle` to the message execution

## [0.10.69] - 2026-01-16
- Add unified type checking CI with basedpyright

## [0.10.68] - 2026-01-14
- Add missing direct dependencies (httpx, anyio, aiohttp, regex, tiktoken) for deptry compliance

## [0.10.67] - 2026-01-14
- chore(deps): bump requests from 2.31.0 to 2.32.4 in examples/custom-assistant

## [0.10.66] - 2026-01-05
- Expose appliedIngestionConfig field on content search.

## [0.10.65] - 2026-01-05
- Add new params for elicitation to `call_tool` api

## [0.10.64] - 2025-12-31
- Add create path functionality to theupsert function and allow getinfo(s) to query by parentfolderpath.

## [0.10.63] - 2025-12-23
- Add functions to create a space and manage its access.

## [0.10.62] - 2025-12-23
- Add get user groups function and allow the get users function to filter by username.

## [0.10.61] - 2025-12-22
- Add `displayInChat` field to ingestion config, allowing silent uploads to chat.

## [0.10.60] - 2025-12-19
- Expose startedStreamingAt and gptRequest fields

## [0.10.59] - 2025-12-19
- Add context field to MagicTableSheetIngestParams.
- Add rowMetadata and context fields to MagicTableRow.

## [0.10.58] - 2025-12-16
- chore(deps): Bump urllib3 from 2.5.0 to 2.6.2

## [0.10.57] - 2025-12-06
- Add description field on create chat completions params.

## [0.10.56] - 2025-12-05
- Add description field on create chat completions params.

## [0.10.55] - 2025-12-04
- Allow configuring inherit access on folder creation.

## [0.10.54] - 2025-12-02
- Add types for Agentic Table api methods.

## [0.10.53] - 2025-12-01
- Improve OpenAI Proxy docs https://unique-ag.github.io/ai/unique-sdk/

## [0.10.52] - 2025-11-21
- Centralized docs to https://unique-ag.github.io/ai/unique-sdk/

## [0.10.51] - 2025-11-21
- Add function to get a space.

## [0.10.50] - 2025-11-21
- Allow updating the configuration of a user and group.

## [0.10.49] - 2025-11-21
- Add get folder by scope id function

## [0.10.48] - 2025-11-20
- Update Agentic Table LogDetail and LogEntry types.

## [0.10.47] - 2025-11-19
- Add expired/s at fields on content search result.

## [0.10.46] - 2025-11-18
- chat_against_file function allows now a should_delete_chat flag.

## [0.10.45] - 2025-11-18
- Create group and manage users functions.

## [0.10.44] - 2025-11-18
- add function to get all messages in a chat.

## [0.10.43] - 2025-11-14
- Add get, delete and update groups functions.

## [0.10.42] - 2025-11-14
- Add get_users function.

## [0.10.41] - 2025-11-13
- Add create_message and get_latest_message.

## [0.10.40] - 2025-11-10
- Don't send description if not defined.

## [0.10.39] - 2025-11-07
- Add function to get llm models

## [0.10.38] - 2025-11-06
- Add description property to Reference and Content.

## [0.10.37] - 2025-11-04
- Introduce local integration tests for Content API Resource

## [0.10.36] - 2025-11-04
- Introduce local integration tests for Folder API Resource

## [0.10.35] - 2025-11-04
- Inmprove folder get infos types.

## [0.10.34] - 2025-10-29
- Add documentation for agentic table.

## [0.10.33] - 2025-10-27
- Improve messagelog and message execution types.

## [0.10.32] - 2025-10-14
- Add function to stream to chat frontend.

## [0.10.31] - 2025-10-13
- Add readme for message log and execution.

## [0.10.30] - 2025-10-07
- Improve types for content get infos.

## [0.10.29] - 2025-10-06
- Switch default model used from `GPT-3.5-turbo (0125)` to `GPT-4o (1120)`

## [0.10.28] - 2025-10-03
- Use non blocking versions of `Space.get_latest_message` and `Message.retrieve` in `send_message_and_wait_for_completion`.

## [0.10.27] - 2025-09-24
- Improve readme to use Unique AI.

## [0.10.26] - 2025-09-22
- Improve typing.

## [0.10.25] - 2025-09-18
- Add support for udpate and delete files by file or folder path.

## [0.10.24] - 2025-09-17
- Add function to update a folder.

## [0.10.23] - 2025-09-12
- Revert to using default reasoning effort.

## [0.10.22] - 2025-09-12
- Add support for metadata update of a file.

## [0.10.21] - 2025-09-04
- Update Chat Completions API types and add support for reasoning effort.

## [0.10.20] - 2025-09-04
- Update Responses API types

## [0.10.19] - 2025-09-02
- Improve `send_message_and_wait_for_completion`:
    - Add option to select stop_condition `["stoppedStreamingAt", "completedAt"]`. 
    - Load `debugInfo` from `last_user_message` for better developer experience.

## [0.10.18] - 2025-09-02
- Temporarily remove support for update and delete files by filePath.

## [0.10.17] - 2025-09-01
- Add function to update a file

## [0.10.16] - 2025-08-31
- Add function to delete a content.

## [0.10.15] - 2025-08-28
- Add default values for message log types

## [0.10.14] - 2025-08-28
- Add function to delete folders and files recursively

## [0.10.13] - 2025-08-24
- Add functions to create, get and update a message eecution and create and update a message log.

## [0.10.12] - 2025-08-24
- Switch to using Content get info deprecated endpoint to make sure we support older release versions.

## [0.10.11] - 2025-08-24
- Enforce usage of ruff using pipeline

## [0.10.10] - 2025-08-18
- Fix wrong name of references in `Space.Message`. 
- Fix wrong name of assessment in `Space.Message`.
- Remove default values for `text`, `originalText` and `debugInfo` in `Space.Message` as these don't have an effect.

## [0.10.9] - 2025-08-15
- Add script to wait for content ingestion finished.

## [0.10.8] - 2025-08-13
- Add support for Agentic Table.

## [0.10.7] - 2025-08-13
- Make metadata optional when uploading a file.

## [0.10.6] - 2025-08-06
- Make tools optional for running an agent.

## [0.10.5] - 2025-08-06
- Get paginated files and folders info.

## [0.10.4] - 2025-08-05
- Add support for reasoning API with streaming within a chat.

## [0.10.3] - 2025-08-05
- Expose scoreThreshold param for search.

## [0.10.2] - 2025-08-05
- Add script to chat against file.

## [0.10.1] - 2025-08-05
- Allow deletion of a space chat.

## [0.10.0] - 2025-08-04
- Add MCP support

## [0.9.42] - 2025-07-31
- Fix wrong chat in space example.

## [0.9.41] - 2025-07-31
- Fix double-slash error in open ai proxy script.

## [0.9.40] - 2025-07-22
- Fixed bug where get requests send body with the request. This is not allowed by WAF policies.

## [0.9.39] - 2025-07-18
- Add script to chat in a space.

## [0.9.38] - 2025-07-18
- [Experimental] Add support for Unique OpenAI proxy. You can now use the OpenAI SDK directly through Unique. Checkout how to do this and a few examples here: `tutorials/unique_basics/sdk_examples/openai_scripts.py`.

## [0.9.37] - 2025-07-10
- Add `sheetName` property to the `MagicTableSheetIngestParams` object used by function that ingests magic table sheets.

## [0.9.36] - 2025-06-23
- Allow passing a user id when creating chat completions. This is optional and it does not impact the current behaviour.

## [0.9.35] - 2025-06-18
- Allow scope access updates (add/remove) on folder based on scope id or path.

## [0.9.34] - 2025-06-17
- Allow ingestion config updates on folder based on scope id or path.

## [0.9.33] - 2025-06-11
- Add function to get a folder by id or by path.

## [0.9.32] - 2025-06-11
- Add function to ingest magic table sheets.

## [0.9.31] - 2025-05-21
- Add function to update folder access (add or remove).

## [0.9.30] - 2025-05-21
- Add function to update folder ingestion config.

## [0.9.29] - 2025-05-20
- Add function to create folder paths if they do not exist.

## [0.9.28] - 2025-05-20
- Add function to search content info. This also allows filtering content info by metadata info.

## [0.9.27] - 2025-05-14
- Add the possibility to specify metadata when creating or updating a Content.

## [0.9.26] - 2025-05-13
- Add the possibility to specify ingestionConfig when creating or updating a Content.

## [0.9.25] - 2025-05-02
- Fixed typos in `README.md`, including incorrect `sdk.utils` imports and code example errors.

## [0.9.24] - 2025-04-23
- Make `chatId` property in `Search.CreateParams` optional

## [0.9.23] - 2025-03-25
- Define programming language classifier explicitly for python 3.11

## [0.9.22] - 2025-02-25
- update the retry_on_error to only `APIError` and `APIConnectionError` update the `resp["error"]` to be `resp.get("error")` to avoid key error

## [0.9.21] - 2025-02-21
- Add title parameter and change labels in `MessageAssessment`

## [0.9.20] - 2025-02-01
- Add url parameter to `MessageAssessment.create_async` and `MessageAssessment.modify_async`

## [0.9.19] - 2025-01-31
- Add `MessageAssessment` resource

## [0.9.18] - 2025-01-22
- Removed `Invalid response body from API` from `retry_dict` as it's our own artificail error.

## [0.9.17] - 2025-01-03
- BREAKING CHANGE!! Removed unused `id` from `ShortTermMemory` create and find methods.

## [0.9.16] - 2024-12-19
- Corrected return type of `Search.create` and `Search.create_async` to `List[Search]`
- Retry on `Connection aborted` error

## [0.9.15] - 2024-12-06
- Add `Internal server error` and `You can retry your request` to the retry logic

## [0.9.14] - 2024-12-06
- Add `contentIds` to `Search.create` and `Search.create_async`

## [0.9.13] - 2024-11-21
- Add retry for `5xx` errors, add additional error message.

## [0.9.12] - 2024-11-21
- Include original error message in returned exceptions

## [0.9.11] - 2024-11-18
- Add  `ingestionConfig` to `UpsertParams.Input` parameters 

## [0.9.10] - 2024-10-23
- Remove `temperature` parameter from `Integrated.chat_stream_completion`, `Integrated.chat_stream_completion_async`, `ChatCompletion.create` and `ChatCompletion.create_async` methods. To use `temperature` parameter, set the attribute in `options` parameter instead.

## [0.9.9] - 2024-10-23
- Revert deletion of `Message.retrieve` method

## [0.9.8] - 2024-10-16
- Add `retries` for `_static_request` and `_static_request_async` in `APIResource` - When the error messages contains either  `"problem proxying the request"`,
        or `"Upstream service reached a hard timeout"`,
## [0.9.7] - 2024-09-23
- Add `completedAt` to `CreateParams` of `Message`

## [0.9.6] - 2024-09-03
- Added `metaDataFilter` to `Search` parameters.

## [0.9.5] - 2024-08-07
- Add `completedAt` to `ModifyParams`

## [0.9.4] - 2024-07-31
- Add `close` and `close_async` to `http_client`
- Make `httpx` the default client for async requests

## [0.9.3] - 2024-07-31
- `Search.create`, `Message`, `ChatCompletion` parameters that were marked `NotRequired` are now also `Optional`

## [0.9.2] - 2024-07-30
- Bug fix in `Search.create`: langugage -> language 

## [0.9.1] - 2024-07-30
- Added parameters to `Search.create` and `Search.create_async`
    - `language` for full text search
    - `reranker` to reranker search results

## [0.9.0] - 2024-07-29
- Added the possibility to make async requests to the unique APIs using either aiohttp or httpx as client
