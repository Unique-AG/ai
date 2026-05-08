# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-orchestrator-v2026.20.0...unique-orchestrator-v2026.20.0) (2026-05-08)


### Features

* Activate todo tool as experimental ([#1590](https://github.com/Unique-AG/ai/issues/1590)) ([f3541ad](https://github.com/Unique-AG/ai/commit/f3541ad5c6af2a384056e4c34d37e6f5ae56879b))
* commands for local ci checks ([#908](https://github.com/Unique-AG/ai/issues/908)) ([25af0f5](https://github.com/Unique-AG/ai/commit/25af0f59b752f54815f726b1ee0d00f19ff3fbbf))
* **loop_runner:** Add support for mistral runner and refactor qwen ([#1176](https://github.com/Unique-AG/ai/issues/1176)) ([e36d178](https://github.com/Unique-AG/ai/commit/e36d178f51e5884d41b9f3f7a772f368c23b330b))
* **orchestrator, deep-research:** use flag-based cancellation via CancellationWatcher ([#1034](https://github.com/Unique-AG/ai/issues/1034)) ([3be5ce3](https://github.com/Unique-AG/ai/commit/3be5ce360e26b8a7f0953d6a3166b74e3942a7d5))
* **orchestrator:** Add LoopIterationHandler for responses api ([#936](https://github.com/Unique-AG/ai/issues/936)) ([25263c3](https://github.com/Unique-AG/ai/commit/25263c3b6bb79407d53f92916a0ae1d3c4fda678))
* **orchestrator:** Add support for planning middleware when responses api is activated ([#1434](https://github.com/Unique-AG/ai/issues/1434)) ([ad7966d](https://github.com/Unique-AG/ai/commit/ad7966dede8081b3f5001edddf7fe4c0a70c3c25))
* **orchestrator:** Allow code interpreter tool to be included in ana… ([#1223](https://github.com/Unique-AG/ai/issues/1223)) ([831b42c](https://github.com/Unique-AG/ai/commit/831b42c0a22cffc1a3d96fd57d5d88bf718b9106))
* **orchestrator:** forward Responses API include params from manager (UN-17972) ([#1262](https://github.com/Unique-AG/ai/issues/1262)) ([0479da6](https://github.com/Unique-AG/ai/commit/0479da689a96aef7832da65cabd98d8824e9a24c))
* **orchestrator:** gate tool call persistence behind feature flag (UN-15977) ([#1273](https://github.com/Unique-AG/ai/issues/1273)) ([e46589c](https://github.com/Unique-AG/ai/commit/e46589cc8b921e8d3b46f9f3c1d518a8b3a79635))
* **orchestrator:** integrate experimental OpenFile tool (UN-17905) ([#1289](https://github.com/Unique-AG/ai/issues/1289)) ([9fb8b04](https://github.com/Unique-AG/ai/commit/9fb8b046924a7df285b6ce74916415a50d514548))
* **orchestrator:** limit uploaded files based on selection ([#1353](https://github.com/Unique-AG/ai/issues/1353)) ([5061d98](https://github.com/Unique-AG/ai/commit/5061d985bdbbf5d3890a5ab5a105f027b8ff25a2))
* **orchestrator:** persist tool calls and fix citation indexing [UN-15977] ([#1104](https://github.com/Unique-AG/ai/issues/1104)) ([1ff52b7](https://github.com/Unique-AG/ai/commit/1ff52b7cca3eeefd69ab198ca53c6e7f0cbe9e7c))
* **orchestrator:** raise max iteration limits for multi-step workflows ([#1413](https://github.com/Unique-AG/ai/issues/1413)) ([2ea265e](https://github.com/Unique-AG/ai/commit/2ea265e015adb367c5cc95fb1320148314154e55))
* **orchestrator:** replace tool call persistence feature flag ([#1343](https://github.com/Unique-AG/ai/issues/1343)) ([d12ae4a](https://github.com/Unique-AG/ai/commit/d12ae4af890616bc82877833ba4e67cf2022a0da))
* **orchestrator:** resolve AUTO_CONTAINER_ONLY capability for GPT-5.4 Pro ([#1328](https://github.com/Unique-AG/ai/issues/1328)) ([deca23a](https://github.com/Unique-AG/ai/commit/deca23aee251eea41f55703fe7a252e3b51e32a8))
* **orchestrator:** system prompt change for image rendering in chat ([#1032](https://github.com/Unique-AG/ai/issues/1032)) ([b035733](https://github.com/Unique-AG/ai/commit/b03573377b9acbdbcf07f0472dcec89b6990223b))
* **orchestrator:** wire RetrieveSearchScope experimental tool ([#1473](https://github.com/Unique-AG/ai/issues/1473)) ([e665c56](https://github.com/Unique-AG/ai/commit/e665c569e542d22f386a53e59e86854e1bd798d4))
* **unique-orchestrator:** add execution time tracking to the agentic loop ([#1143](https://github.com/Unique-AG/ai/issues/1143)) ([15ed98c](https://github.com/Unique-AG/ai/commit/15ed98c439f9f0369b42d4f05fe72a29121a5c0d))
* **unique-orchestrator:** adding open pdf tool ([#1337](https://github.com/Unique-AG/ai/issues/1337)) ([50e01b8](https://github.com/Unique-AG/ai/commit/50e01b807914b15eb1d8d13130fc321d87156b4e))
* **unique-orchestrator:** adding user instruction ([#1060](https://github.com/Unique-AG/ai/issues/1060)) ([884671c](https://github.com/Unique-AG/ai/commit/884671c98355bd45b1284d4485eaacc54be77695))
* **unique-orchestrator:** change ff ([#1404](https://github.com/Unique-AG/ai/issues/1404)) ([017e135](https://github.com/Unique-AG/ai/commit/017e1359a3e4f8f561dff614d80eb42f9eefd3e6))
* **unique-orchestrator:** Increase max loops ([#1486](https://github.com/Unique-AG/ai/issues/1486)) ([c036e38](https://github.com/Unique-AG/ai/commit/c036e382c73abcc66a71ed50097322b31c2533b5))
* **unique-orchestrator:** revert adding open file tool ([#1316](https://github.com/Unique-AG/ai/issues/1316)) ([5b42389](https://github.com/Unique-AG/ai/commit/5b42389c808682a3dba12f931aa19b29b30ed00f))
* **unique-orchestrator:** skills tool ([#1485](https://github.com/Unique-AG/ai/issues/1485)) ([636db3d](https://github.com/Unique-AG/ai/commit/636db3d26f89f623793c43f157de8556911654d1))
* **unique-orchestrator:** update skills folder structure ([#1568](https://github.com/Unique-AG/ai/issues/1568)) ([0d0ed34](https://github.com/Unique-AG/ai/commit/0d0ed345e788bf563bcb43d61f14a8bcc2b7d018))
* **unique-orchestrator:** user_instruction to user_space_instruction ([#1082](https://github.com/Unique-AG/ai/issues/1082)) ([36d664e](https://github.com/Unique-AG/ai/commit/36d664e986b9557691b4e9fc18a5706a2c130250))
* **unique-skill-tool:** adding selectable skill parameter; allow ski… ([#1597](https://github.com/Unique-AG/ai/issues/1597)) ([1b30de5](https://github.com/Unique-AG/ai/commit/1b30de5408eb0c1a7c8279feb7d18a4dc91eacfe))
* **unique-skill:** including skill choices to payload ([#1636](https://github.com/Unique-AG/ai/issues/1636)) ([36e8275](https://github.com/Unique-AG/ai/commit/36e82750e89d350e2293b8144035bac903829445))
* **unique-skill:** removing scope id and use selectable skills param ([#1630](https://github.com/Unique-AG/ai/issues/1630)) ([28b8b5e](https://github.com/Unique-AG/ai/commit/28b8b5e9ee7e0e01e215dbf54179eb20f88f6cb1))
* **unique-skill:** updating config merging ([#1619](https://github.com/Unique-AG/ai/issues/1619)) ([e84306b](https://github.com/Unique-AG/ai/commit/e84306bc1061d108eb7006aa515f54a33b03b776))
* **uploaded_search:** Update logic of Uploaded files ([#1591](https://github.com/Unique-AG/ai/issues/1591)) ([7407c95](https://github.com/Unique-AG/ai/commit/7407c95a7ac9498e268873794309c06d7c47c63b))


### Bug Fixes

* Adjust feature flag for Orchestrator ([#982](https://github.com/Unique-AG/ai/issues/982)) ([387b81c](https://github.com/Unique-AG/ai/commit/387b81c60651ce3e924521c0c869e033a4f00c9c))
* **ai:** config cleanup - orchestrator - hallucination check ([#888](https://github.com/Unique-AG/ai/issues/888)) ([0c9b48b](https://github.com/Unique-AG/ai/commit/0c9b48b9a6e682a6b6f8f198e426a6bcd65ffa2b))
* formating and dates on all changelogs ([#1114](https://github.com/Unique-AG/ai/issues/1114)) ([9a7998b](https://github.com/Unique-AG/ai/commit/9a7998b9617ee88698385537c2ecde0ab30366f4))
* **orchestrator:** Add check for ingestion mode when enabling uploade… ([#1424](https://github.com/Unique-AG/ai/issues/1424)) ([a15ce6e](https://github.com/Unique-AG/ai/commit/a15ce6eea63ea05c1b89e96c34daa7bfbca1393a))
* **orchestrator:** align uploaded-search ingestion tests with new is_ingested semantics ([#1466](https://github.com/Unique-AG/ai/issues/1466)) ([4354db7](https://github.com/Unique-AG/ai/commit/4354db7ead51c21aa3eb14128bcde285ae54267a))
* **orchestrator:** correct changelog date to 2026-03-05 ([#1153](https://github.com/Unique-AG/ai/issues/1153)) ([72a1d0d](https://github.com/Unique-AG/ai/commit/72a1d0d72805ac8b0ac2e22961a0b6cd805d60ac))
* **orchestrator:** enable code interpreter via UI tool toggle ([#1049](https://github.com/Unique-AG/ai/issues/1049)) ([50d7541](https://github.com/Unique-AG/ai/commit/50d7541f71823ea2082d6491f283a879ffb5629c))
* **orchestrator:** enforce markdown indentation for hierarchical lists ([#939](https://github.com/Unique-AG/ai/issues/939)) ([ec4857a](https://github.com/Unique-AG/ai/commit/ec4857a3c0a6da246e82b764eeaaa1c2a60539ef))
* **orchestrator:** hide responses API config from experimental UI sec… ([#1090](https://github.com/Unique-AG/ai/issues/1090)) ([7aab5c7](https://github.com/Unique-AG/ai/commit/7aab5c742bc98107672b43ffaba5174c713d6513))
* **orchestrator:** preserve uploaded search in responses path [UN-18125] ([#1199](https://github.com/Unique-AG/ai/issues/1199)) ([16d9075](https://github.com/Unique-AG/ai/commit/16d907564cc4077a2d542524d467d3b20a9a49ec))
* **orchestrator:** Remove unused code interpreter code ([#1169](https://github.com/Unique-AG/ai/issues/1169)) ([89f87ba](https://github.com/Unique-AG/ai/commit/89f87ba6caa1a6a8700d90fe59b2fe0416dd764f))
* **orchestrator:** replace sync modify_assistant_message with async in run() ([#1374](https://github.com/Unique-AG/ai/issues/1374)) ([3ec2efd](https://github.com/Unique-AG/ai/commit/3ec2efd07bb101f1340ea6e277639caee4a66f06))
* **orchestrator:** skip hallucination check when code interpreter is used ([#1359](https://github.com/Unique-AG/ai/issues/1359)) ([b285d49](https://github.com/Unique-AG/ai/commit/b285d49b74eab79f053acd6c3e47d323a14a1d24))
* **orchestrator:** UN-15221 poll for cancellation instead of only checking flag ([#1126](https://github.com/Unique-AG/ai/issues/1126)) ([74d34e9](https://github.com/Unique-AG/ai/commit/74d34e9eecf36e001eb70743b4b93bb866c04ef8))
* **unique-orchestrator:** backward compatibility configs ([#921](https://github.com/Unique-AG/ai/issues/921)) ([13ea2fd](https://github.com/Unique-AG/ai/commit/13ea2fd3c9fe6c7f6a0a4a4effa9069297daff65))
* **unique-orchestrator:** selected images files ([#1452](https://github.com/Unique-AG/ai/issues/1452)) ([b0ff088](https://github.com/Unique-AG/ai/commit/b0ff0887c4a9a1ae4128457ed2819f650acb580b))
* **unique-orchestrator:** update debug info ([#1271](https://github.com/Unique-AG/ai/issues/1271)) ([58e5bec](https://github.com/Unique-AG/ai/commit/58e5bec0d43dda4c42fa61bff300a4eba124e7a6))
* **unique-skills:** moving tool out of experimental ([#1580](https://github.com/Unique-AG/ai/issues/1580)) ([bcedf9d](https://github.com/Unique-AG/ai/commit/bcedf9d61e44d787d304b105317555122ecf1207))
* **unique-toolkit:** using response API fpr GPT 55 ([#1556](https://github.com/Unique-AG/ai/issues/1556)) ([dd105e9](https://github.com/Unique-AG/ai/commit/dd105e97c5931b872beaa0905cb6e2ae433f345f))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))
* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

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
