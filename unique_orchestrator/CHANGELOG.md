# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.30.0...unique-orchestrator-v2026.32.0) (2026-07-24)


### Features

* Pricing analytics ([#2146](https://github.com/Unique-AG/ai/issues/2146)) ([57cb3fc](https://github.com/Unique-AG/ai/commit/57cb3fc9ac5e0e09fe30ccf0e03fd694cde4122c))
* Token count analytics ([#2112](https://github.com/Unique-AG/ai/issues/2112)) ([f475dc4](https://github.com/Unique-AG/ai/commit/f475dc4606dd723e0fecfcdd09ace2f9c329e960))


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.28.0...unique-orchestrator-v2026.30.0) (2026-07-17)


### Features

* **orchestrator:** apply per-model temperature on model choice ([#2091](https://github.com/Unique-AG/ai/issues/2091)) ([3a13a89](https://github.com/Unique-AG/ai/commit/3a13a89fe8be2467950f7483337aaf720752e7ec))
* **unique_orchestrator:** Expose Python streaming as experimental flag ([#1990](https://github.com/Unique-AG/ai/issues/1990)) ([a2f796e](https://github.com/Unique-AG/ai/commit/a2f796e001c1f587553e672fea925cf202fe67eb))
* **unique_orchestrator:** expose token usage on Space orchestration messages [UN-20907] ([#2078](https://github.com/Unique-AG/ai/issues/2078)) ([7e286db](https://github.com/Unique-AG/ai/commit/7e286db6f962710e732829f0e073687ee5aab60e))
* **unique_toolkit:** add analytics debug-info snapshot [UN-22110] ([#2055](https://github.com/Unique-AG/ai/issues/2055)) ([fbcbe72](https://github.com/Unique-AG/ai/commit/fbcbe72eef4bf0e697b4eb7acaed73bb7f055deb))
* **unique_toolkit:** add artifact output size analytics ([#2102](https://github.com/Unique-AG/ai/issues/2102)) ([a778134](https://github.com/Unique-AG/ai/commit/a7781340641854c7c36479d6390244be12a4f3d0)), closes [#2076](https://github.com/Unique-AG/ai/issues/2076)
* **unique_toolkit:** populate artifact analytics fields [UN-22110] ([#2076](https://github.com/Unique-AG/ai/issues/2076)) ([fa31ec8](https://github.com/Unique-AG/ai/commit/fa31ec84d5ce8604fd4e48f4685ce7f129ff8c51))
* **unique_toolkit:** Reenable file content serialization ([#2048](https://github.com/Unique-AG/ai/issues/2048)) ([256fbda](https://github.com/Unique-AG/ai/commit/256fbdacd2c9545e6a4950eb0451d67c23a3c22b))
* **unique_toolkit:** Support lazy code interpreter loading ([#1997](https://github.com/Unique-AG/ai/issues/1997)) ([fb72d4c](https://github.com/Unique-AG/ai/commit/fb72d4c7afe88be9c0b7740b22818bab80c20acd))
* **unique-orchestrator:** adding analytics parameters to debug info ([#2063](https://github.com/Unique-AG/ai/issues/2063)) ([e42d6ce](https://github.com/Unique-AG/ai/commit/e42d6ce15e164cf4729794997c564462743d4cb5))
* **unique-toolkit:** force responses api for gpt 56 ([#2065](https://github.com/Unique-AG/ai/issues/2065)) ([f022cfe](https://github.com/Unique-AG/ai/commit/f022cfe4b6fa30ea61df604ef4aaba5e561521ce))
* update logging and config of context memory ([#2098](https://github.com/Unique-AG/ai/issues/2098)) ([a38625e](https://github.com/Unique-AG/ai/commit/a38625efe25891a82e04ea6477113f43d94eaa62))
* update user memory logic ([#2087](https://github.com/Unique-AG/ai/issues/2087)) ([0e8b7df](https://github.com/Unique-AG/ai/commit/0e8b7df00a4169104d273374b147c1664f9fbff7))


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.26.0...unique-orchestrator-v2026.28.0) (2026-07-03)


### Features

* **skills:** triggered skills in debug info ([#1920](https://github.com/Unique-AG/ai/issues/1920)) ([a779839](https://github.com/Unique-AG/ai/commit/a77983985c2cb2ded1bbb8444f2f8f5dd5ee241c))
* **unique_toolkit:** Implement the `AskUser` tool ([#1653](https://github.com/Unique-AG/ai/issues/1653)) ([b2cec51](https://github.com/Unique-AG/ai/commit/b2cec513c6344e4582bb876384a260c2120ebb6b))
* **user-memory:** update config user memory ([#1916](https://github.com/Unique-AG/ai/issues/1916)) ([5ff1d46](https://github.com/Unique-AG/ai/commit/5ff1d46a9ebcf32ea58088fa9439c8fec6f7e51b))
* **user-memory:** update user memory ([#1980](https://github.com/Unique-AG/ai/issues/1980)) ([a461fbc](https://github.com/Unique-AG/ai/commit/a461fbc21344ab9a91d744f9f566daaf135f9235))


### Bug Fixes

* **toolkit:** inject shared ChatService into tools at construction ([#2000](https://github.com/Unique-AG/ai/issues/2000)) ([695697f](https://github.com/Unique-AG/ai/commit/695697f0ef487a3ccae4d1afea6c22944a1ccf7e))
* **unique-toolkit:** preserve concrete config for valid disabled tools [UN-17197] ([#1979](https://github.com/Unique-AG/ai/issues/1979)) ([08dda03](https://github.com/Unique-AG/ai/commit/08dda03dad1e2b231e9d3bd42d0442eece621196))


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.24.0...unique-orchestrator-v2026.26.0) (2026-06-22)


### Features

* trigger dev version deployment for orchestrator ([#1885](https://github.com/Unique-AG/ai/issues/1885)) ([66d4593](https://github.com/Unique-AG/ai/commit/66d45934c8ee68dcfe8b9eea347a4c70b0f22d0f))
* User Memory ([#1771](https://github.com/Unique-AG/ai/issues/1771)) ([098b0de](https://github.com/Unique-AG/ai/commit/098b0de1d11f45cb4f013b49c367e52bf9c3250b))
* **user-memory:** hide config ([#1900](https://github.com/Unique-AG/ai/issues/1900)) ([336913a](https://github.com/Unique-AG/ai/commit/336913a479e4f250c479c0d23a5c5e393d820af3))


### Miscellaneous

* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.22.0...unique-orchestrator-v2026.24.0) (2026-06-04)


### Features

* Enable model picking ([#1735](https://github.com/Unique-AG/ai/issues/1735)) ([753eab5](https://github.com/Unique-AG/ai/commit/753eab56adc3097c269b5c62da4bd2e09d7f871f))
* **unique_orchestrator:** RJSF textarea tags for agent prompt config ([#1780](https://github.com/Unique-AG/ai/issues/1780)) ([96691f0](https://github.com/Unique-AG/ai/commit/96691f0a1beae47529b6eb0d09d6f8358ab99b81))


### Miscellaneous

* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [2026.22.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.20.0...unique-orchestrator-v2026.22.0) (2026-05-21)


### Features

* **unique_orchestrator:** Allow configuration of UploadedSearch Tool ([#1674](https://github.com/Unique-AG/ai/issues/1674)) ([1e41209](https://github.com/Unique-AG/ai/commit/1e412094a97b574ef1dac422ed62793667a34c8d))
* **unique_orchestrator:** Debug info thinking level ([#1716](https://github.com/Unique-AG/ai/issues/1716)) ([660277f](https://github.com/Unique-AG/ai/commit/660277f03902af3c759a6f583b8324fe7a3e3ff2))
* **unique_toolkit:** Add display of code interpreter files to the co… ([#1665](https://github.com/Unique-AG/ai/issues/1665)) ([4d661da](https://github.com/Unique-AG/ai/commit/4d661dabb0269061b3833c36872ff70e9de49fd0))
* **unique-skill-tool:** add optional thinking level to skills ([#1692](https://github.com/Unique-AG/ai/issues/1692)) ([9aad730](https://github.com/Unique-AG/ai/commit/9aad730ac739bdd6f48a10c2f29fb602a052fab6))
* **unique-skill-tool:** load skill by content_id and not name  ([#1698](https://github.com/Unique-AG/ai/issues/1698)) ([926554e](https://github.com/Unique-AG/ai/commit/926554e5046457a46a42c4e8a129f7d0ad0b36fb))


### Bug Fixes

* **unique-skills:** available skill parameter included ([#1691](https://github.com/Unique-AG/ai/issues/1691)) ([b8c35b4](https://github.com/Unique-AG/ai/commit/b8c35b41466ab23165ccde8e1bd6b5dc4a0f1c62))


### Miscellaneous

* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.18.0...unique-orchestrator-v2026.20.0) (2026-05-08)


### Features

* Activate todo tool as experimental ([#1590](https://github.com/Unique-AG/ai/issues/1590)) ([f3541ad](https://github.com/Unique-AG/ai/commit/f3541ad5c6af2a384056e4c34d37e6f5ae56879b))
* **orchestrator:** raise max iteration limits for multi-step workflows ([#1413](https://github.com/Unique-AG/ai/issues/1413)) ([2ea265e](https://github.com/Unique-AG/ai/commit/2ea265e015adb367c5cc95fb1320148314154e55))
* **orchestrator:** wire RetrieveSearchScope experimental tool ([#1473](https://github.com/Unique-AG/ai/issues/1473)) ([e665c56](https://github.com/Unique-AG/ai/commit/e665c569e542d22f386a53e59e86854e1bd798d4))
* **unique-orchestrator:** update skills folder structure ([#1568](https://github.com/Unique-AG/ai/issues/1568)) ([0d0ed34](https://github.com/Unique-AG/ai/commit/0d0ed345e788bf563bcb43d61f14a8bcc2b7d018))
* **unique-skill-tool:** adding selectable skill parameter; allow ski… ([#1597](https://github.com/Unique-AG/ai/issues/1597)) ([1b30de5](https://github.com/Unique-AG/ai/commit/1b30de5408eb0c1a7c8279feb7d18a4dc91eacfe))
* **unique-skill:** including skill choices to payload ([#1636](https://github.com/Unique-AG/ai/issues/1636)) ([36e8275](https://github.com/Unique-AG/ai/commit/36e82750e89d350e2293b8144035bac903829445))
* **unique-skill:** removing scope id and use selectable skills param ([#1630](https://github.com/Unique-AG/ai/issues/1630)) ([28b8b5e](https://github.com/Unique-AG/ai/commit/28b8b5e9ee7e0e01e215dbf54179eb20f88f6cb1))
* **unique-skill:** updating config merging ([#1619](https://github.com/Unique-AG/ai/issues/1619)) ([e84306b](https://github.com/Unique-AG/ai/commit/e84306bc1061d108eb7006aa515f54a33b03b776))
* **uploaded_search:** Update logic of Uploaded files ([#1591](https://github.com/Unique-AG/ai/issues/1591)) ([7407c95](https://github.com/Unique-AG/ai/commit/7407c95a7ac9498e268873794309c06d7c47c63b))


### Bug Fixes

* **unique-skills:** moving tool out of experimental ([#1580](https://github.com/Unique-AG/ai/issues/1580)) ([bcedf9d](https://github.com/Unique-AG/ai/commit/bcedf9d61e44d787d304b105317555122ecf1207))
* **unique-toolkit:** using response API fpr GPT 55 ([#1556](https://github.com/Unique-AG/ai/issues/1556)) ([dd105e9](https://github.com/Unique-AG/ai/commit/dd105e97c5931b872beaa0905cb6e2ae433f345f))


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v1.22.2...unique-orchestrator-v2026.18.0) (2026-04-23)


### Features

* **unique-orchestrator:** Increase max loops ([#1486](https://github.com/Unique-AG/ai/issues/1486)) ([c036e38](https://github.com/Unique-AG/ai/commit/c036e382c73abcc66a71ed50097322b31c2533b5))
* **unique-orchestrator:** skills tool ([#1485](https://github.com/Unique-AG/ai/issues/1485)) ([636db3d](https://github.com/Unique-AG/ai/commit/636db3d26f89f623793c43f157de8556911654d1))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [1.22.2] - 2026-04-22
- Align `SKIP_EXCEL_INGESTION` tests in `_configure_uploaded_search_tool` with the new `Content.is_ingested` semantics from `unique_toolkit` 1.80.1; also pin non-Excel behavior with a regression test.

## [1.22.1] - 2026-04-20
- Pass `selected_content_ids` to `OpenFileToolRuntimeConfig` so only user-selected uploaded PDFs are included
- Fix `filter_uploaded_documents_by_selection` call to handle missing `additional_parameters` gracefully

## [1.22.0] - 2026-04-16
- Add planning middleware support for Responses API

## [1.21.3] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [1.21.2] - 2026-04-14
- Chore: migrate pytest config from `pytest.ini` to `pyproject.toml` with `importlib` import mode
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [1.21.1] - 2026-04-13
- Trigger `uploaded_content_tool` only if at least one file is ingested (and not expired)

## [1.21.0] - 2026-04-09
- Widen `openai` dependency upper bound from `<2` to `<3` to allow openai SDK v2.x (required for litellm security fix)

## [1.20.7] - 2026-04-09
- changing FF from enable_selected_uploaded_files_un_18470 to enable_selected_uploaded_files_un_18215

## [1.20.6] - 2026-04-08
- Including logic for selected uploaded files

## [1.20.5] - 2026-04-06
- Fix sync `modify_assistant_message` calls inside async `run()` and `_process_plan()` blocking the event loop — replaced with `modify_assistant_message_async`

## [1.20.4] - 2026-04-03
- Fix: skip hallucination evaluation when code interpreter is used, preventing false-positive assessments on code-execution-grounded answers

## [1.20.3] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [1.20.2] - 2026-04-01
- Removing `FEATURE_FLAG_ENABLE_TOOL_CALL_PERSISTENCE_UN_15977` and replace it with parameter in loop history config

## [1.20.1] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [1.20.0] - 2026-04-01
- Experimental open file tool

## [1.19.0] - 2026-03-31
- Resolve `AUTO_CONTAINER_ONLY` model capability in `_build_responses` and pass `force_auto_container` to `OpenAIBuiltInToolManager.build_manager`
- Bump `unique-toolkit` lower-bound to `>=1.67.0`

## [1.18.1] - 2026-03-30
- Revert experimental open file tool

## [1.18.0] - 2026-03-26
- Experimental open file tool

## [1.17.1] - 2026-03-26
- Gate tool call persistence and history reconstruction behind `FEATURE_FLAG_ENABLE_TOOL_CALL_PERSISTENCE_UN_15977`; both are disabled by default (UN-15977)
- Bump `unique-toolkit` lower-bound to `>=1.64.1`

## [1.17.0] - 2026-03-25
- Forward Responses API `include` params from `ResponsesApiToolManager.get_required_include_params()` via `ResponsesStreamingHandler` (UN-17972); gating lives in `unique_toolkit` — no FF logic in orchestrator
- Pass `company_id` into `ShowExecutedCodePostprocessor` so fence feature-flag checks match `DisplayCodeInterpreterFilesPostProcessor` (UN-17972)
- Bump `unique-toolkit` lower-bound to `>=1.64.0`

## [1.16.0] - 2026-03-25
- Persist tool calls and compacted responses to the database after each agentic loop via `_persist_tool_calls()` (UN-15977)
- Use `history_manager.get_content_chunks_for_backend()` for citation indexing so `searchContext[N]` correctly resolves `[sourceN]` across turns (UN-15977)
- Remove `percent_for_tool_call_history` from `InputTokenDistributionConfig` and `HistoryManagerConfig` wiring; history truncation now relies solely on `percent_for_history`
- Bump `unique-toolkit` dependency to `>=1.63.0`


## [1.15.1] - 2026-03-25
- Fix debug info

## [1.15.0] - 2026-03-23
- Add support for Code Execution in tool analytics (Debug Info)

## [1.14.3] - 2026-03-17
- Add execution timing tracking to the agentic loop: records per-iteration durations for planning/streaming, tool execution, post-processing, and evaluation
- Persist aggregated execution times (per-loop and total) into user message debug info

## [1.14.2] - 2026-03-16
- Remove unused code interpreter code

## [1.14.1] - 2026-03-13
- Fix uploaded file bootstrapping in the Responses API path by mirroring the `UploadedSearch` registration and forcing behavior used in the completions path

## [1.14.0] - 2026-03-10
- Refactor `build_loop_iteration_runner`: replace `is_qwen_model` check with inline `_get_model_family` helper and if/elif/else dispatch; add `MistralLoopIterationRunner` selection for Mistral models
- Update `UniqueAI._effective_max_loop_iterations`: replace `is_qwen_model` import with inline string check

## [1.13.07] - 2026-03-05
- Build: migrate from Poetry to uv

## [1.13.06] - 2026-03-03
- Fix cancellation polling: replace passive `is_cancelled` flag checks with active `check_cancellation_async()` calls so the orchestrator actually detects user aborts

## [1.13.05] - 2026-02-26
- Add system prompt instruction for image rendering: use `![image](unique://content/[content_id])` when referring to tool-returned images

## [1.13.04] - 2026-02-26
- Hide Responses API config from experimental section in UI (SkipJsonSchema); Code Interpreter is now configured via tools section only

## [1.13.03] - 2026-02-23
- Changing parameter name from `user_instruction` to `user_space_instruction`

## [1.13.02] - 2026-02-23
- Add flag-based cancellation support via `CancellationWatcher`

## [1.13.01] - 2026-02-23
- Fix code interpreter tool toggle: auto-enable Responses API and populate default `CodeInterpreterExtendedConfig` when an enabled `code_interpreter` tool is present and model supports Responses API
- Fix `_build_responses` to filter `tool_names` by `is_enabled` so a disabled tool entry does not block the builder from adding an enabled instance

## [1.13.00] - 2026-01-26
- Including functionality of user instruction in orchestrator

## [1.12.02] - 2026-01-26
- Adjust feature flag

## [1.12.01] - 2026-01-26
- Fix system prompt to enforce proper markdown list indentation for hierarchical formatting

## [1.12.00] - 2026-01-23
- Use responses api version of `LoopIterationHandler`

## [1.11.14] - 2026-01-21
- Add Qwen-specific loop iteration limits to reduce unnecessary agent runs

## [1.11.13] - 2026-01-20
- Fix configuration for backward compatibility

## [1.11.12] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [1.11.11] - 2026-01-16
- Config cleanup of orchestrator

## [1.11.10] - 2026-01-16
- Add unified type checking CI with basedpyright

## [1.11.9] - 2026-01-15
- Add `pytest-cov` dev dependency for coverage testing

## [1.11.8] - 2026-01-13
- Clean up dependencies and add deptry configuration for CI compliance

## [1.11.7] - 2026-01-13
- Removing unused and retired configuration parameters `max_review_steps`, `uploaded_content_config`, `tool_progress_reporter_config`, `force_checks_on_stream_response_references` and `thinking_steps_display`

## [1.11.6] - 2026-01-13
- Deprecate UniqueAIResponsesApi and use UniqueAI directly instead (type safety)

## [1.11.5] - 2026-01-12
- Include feature flag to have message logs compatible with new ChatUI

## [1.11.4] - 2025-12-29
- Fixes orchestrator tests and adds a ci test pipeline for it

## [1.11.3] - 2025-12-29
- Fix system prompt with priority rule

## [1.11.2] - 2025-12-18
- Improve bullet style for tool call message logs (for consistency)

## [1.11.1] - 2025-12-11
- Improving support for forced tool call for Qwen models

## [1.11.0] - 2025-12-11
- Add support for forced tool call for Qwen models

## [1.10.0] - 2025-12-08
- Upgrading swot tool

## [1.9.0] - 2025-12-05
- Add support for planning before every loop iteration

## [1.8.2] - 2025-12-04
- Fix logging tool calls when tool takes over control

## [1.8.1] - 2025-12-03
- Logging tool calls when tool takes over control

## [1.8.0] - 2025-12-02
- Add option to upload code interpreter generated files to the chat.

## [1.7.19] - 2025-12-01
- Systemprompt formatting update

## [1.7.18] - 2025-11-27
- Improvement of message log service to indicate number of tool calls per loop iteration

## [1.7.17] - 2025-11-27
- Fixed an issue where the orchestrator failed when the number of tool calls exceeded the maximum allowed as defined in the configuration.
- Increased default value of max parallel tool calls from 5 to 15

## [1.7.16] - 2025-11-26
- Removing log of Deep Research tool call while keeping messages generated within the Deep Research call

## [1.7.15] - 2025-11-24 
- Streamlining message log service for listing tools and being compatible with SWOT and DeepSearch

## [1.7.14] - 2025-11-20
- Add message log service

## [1.7.13] - 2025-11-20
- Fix bug of handling properly uploaded files that are expired

## [1.7.12] - 2025-11-19
- Bump Swot tool

## [1.7.11] - 2025-11-17
- Fix bug where forcing a tool still sends builtin tools to the LLM when using the responses api.

## [1.7.10] - 2025-11-14
- Move pytest to dev dependencies

## [1.7.9] - 2025-11-12
- Fix bug where Responses API config was not properly validated

## [1.7.8] - 2025-11-11
- Better display of Responses API config in the UI

## [1.7.7] - 2025-11-10
- Remove direct azure client config from responses api config
- Organize Responses API config better

## [1.7.6] - 2025-11-05
- Update default system prompt (including user metadata section)

## [1.7.5] - 2025-11-05
- Adding functionality to include user metadata into user/system prompts of the orchestrator

## [1.7.4] - 2025-11-04
- Update and adapt to toolkit 1.23.0 (refactor sub agents implementation)

## [1.7.3] - 2025-11-03
- Fixed an issue where new assistant messages were not properly generated during streaming outputs with tool calls; the orchestrator now correctly creates messages via `_create_new_assistant_message_if_loop_response_contains_content` when loop_response includes text and tool invocations.

## [1.7.2] - 2025-11-03
- Add Swot tool to the orchestrator

## [1.7.1] - 2025-10-30
- Fixing that system format info is only appended to system prompt if tool is called

## [1.7.0] - 2025-10-30
- Add option to customize the display of tool progress statuses.
- Make follow-questions postprocessor run last to make sure the follow up questions are displayed last.

## [1.6.1] - 2025-10-28
- Removing unused experimental config `full_sources_serialize_dump` in `history_manager`

## [1.6.0] - 2025-10-27
- Add temporary config option `sleep_time_before_update` to avoid rendering issues with sub agent responses`

## [1.5.2] - 2025-10-23
- Run evaluation and post processing in parallel

## [1.5.1] - 2025-10-17
- revert behavior of unique ai upload and chat to 
1. Add upload and chat tool to forced tools if there are tool choices
2. Simply force it if there are no tool choices.
3. Tool not available when no uploaded documents

## [1.5.0] - 2025-10-16
- Make code interpreter configurable through spaces 2.0.

## [1.4.3] - 2025-10-16
- Fix issue with openai base url

## [1.4.2] - 2025-10-16
- Update debug info for better tool call tracking

## [1.4.1] - 2025-10-16
- Temporarily make open ai env vars configurable

## [1.4.0] - 2025-10-14
- Add responses api and code execution support.

## [1.3.0] - 2025-10-14
- Re-organize sub-agents configuration for clarity.

## [1.2.4] - 2025-10-14
- Let control taking tool itself set the message state to completed

## [1.2.3] - 2025-10-13
- Fix bug where follow-up questions were being generated even if the number of questions is set to 0 in the config.

## [1.2.2] - 2025-10-09
- update loading path of `DEFAULT_GPT_4o` from `unique_toolkit`

## [1.2.1] - 2025-10-07
- upgrade to deep research 3.0.0

## [1.2.0] - 2025-10-07
- Add sub agent response referencing.

## [1.1.1] - 2025-10-03
- Adapt orchestrator to toolkit 1.8.0.

## [1.1.0] - 2025-09-29
- Add ability to display sub agent's answers in main agent.
- Add ability to consolidate sub agent's assessment's in main agent.

## [1.0.3] - 2025-09-29
- fix UniqueAI system prompt for not activated tools
- updated README

## [1.0.2] - 2025-09-29
- updated deep-research to v2

## [1.0.1] - 2025-09-18
- updated toolkit

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates 

## [0.0.4] - 2025-09-17
- Updated to latest toolkit

## [0.0.3] - 2025-09-16
- Cleaned configuration

## [0.0.2] - 2025-09-15
- Resolve dependency bug

## [0.0.1] - 2025-08-18
- Initial release of `orchestrator`.
