# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.20.0...unique-internal-search-v2026.20.0) (2026-05-08)


### Features

* commands for local ci checks ([#908](https://github.com/Unique-AG/ai/issues/908)) ([25af0f5](https://github.com/Unique-AG/ai/commit/25af0f59b752f54815f726b1ee0d00f19ff3fbbf))
* **internal_search:** using parent_chat_id in internal search tool ([#1121](https://github.com/Unique-AG/ai/issues/1121)) ([5afb1b8](https://github.com/Unique-AG/ai/commit/5afb1b8acfca2ffc61489a57d09fcf83ba843b2c))
* **internal-search:** add configurable tool-response system reminder for citation enforcement ([#1280](https://github.com/Unique-AG/ai/issues/1280)) ([3669fd9](https://github.com/Unique-AG/ai/commit/3669fd9393f1ec8524a5ba454d663b6357beec01))
* **internal-search:** add contentId to uploaded document system prompt ([#1260](https://github.com/Unique-AG/ai/issues/1260)) ([657d7dc](https://github.com/Unique-AG/ai/commit/657d7dcf829d2d5bffab56b558ddbce2d091fa52))
* **internal-search:** limit uploaded files based on selection ([#1354](https://github.com/Unique-AG/ai/issues/1354)) ([c632dca](https://github.com/Unique-AG/ai/commit/c632dcae5e3e60b78797e26deef3710178528f01))
* **internal-search:** migrate token counting to model-agnostic encoder ([#998](https://github.com/Unique-AG/ai/issues/998)) ([25cd41b](https://github.com/Unique-AG/ai/commit/25cd41b7d315887124452e4662958c38a1b5c2e3))
* **unique-internal-sesarch:** change ff ([#1405](https://github.com/Unique-AG/ai/issues/1405)) ([052b1e1](https://github.com/Unique-AG/ai/commit/052b1e16ecafad3b7dd2236a7f77bc632a2420eb))
* **uploaded_search:** Update logic of Uploaded files ([#1591](https://github.com/Unique-AG/ai/issues/1591)) ([7407c95](https://github.com/Unique-AG/ai/commit/7407c95a7ac9498e268873794309c06d7c47c63b))


### Bug Fixes

* Adjust feature flag for internal search ([#981](https://github.com/Unique-AG/ai/issues/981)) ([37be10c](https://github.com/Unique-AG/ai/commit/37be10c10ae7137e7c93856d8dbd3c766faf335c))
* **internal-search:** guard against missing additional_parameters on magic table payloads ([#1417](https://github.com/Unique-AG/ai/issues/1417)) ([aa3fed5](https://github.com/Unique-AG/ai/commit/aa3fed58011fc664ee4b8f772df70738c98a744b))
* **internal-search:** Introduce message logger service for internal search and fix logger misbehaviour ([#1640](https://github.com/Unique-AG/ai/issues/1640)) ([c24d1cd](https://github.com/Unique-AG/ai/commit/c24d1cd0a24af04a4aec3040d303a456dc2155bb))
* References swot and naming of uploaded search ([#919](https://github.com/Unique-AG/ai/issues/919)) ([3c339c1](https://github.com/Unique-AG/ai/commit/3c339c1429a0004f2dd5764d4fb48c5278f9904e))
* **toolkit:** preserve readable unicode in tool history ([#1247](https://github.com/Unique-AG/ai/issues/1247)) ([8333c3f](https://github.com/Unique-AG/ai/commit/8333c3fa9163473ed9a52ee45504008462555fc2))
* **unique-internal-search:** adjust limit of search chunks to LLM input ([#1442](https://github.com/Unique-AG/ai/issues/1442)) ([f93a04d](https://github.com/Unique-AG/ai/commit/f93a04df89ba76a68f5e707bf41c9147409f003d))
* **unique-internal-search:** Expose Experimental Configs ([#1281](https://github.com/Unique-AG/ai/issues/1281)) ([bc8e0f0](https://github.com/Unique-AG/ai/commit/bc8e0f0d9197f923957850039e886e781a302b0b))
* **unique-internal-search:** Fix behavior when no files are selected ([#979](https://github.com/Unique-AG/ai/issues/979)) ([ba62416](https://github.com/Unique-AG/ai/commit/ba62416777fe521739591723c8d1e64bc29d6579))
* **unique-internal-search:** Revert internal search fix ([#1026](https://github.com/Unique-AG/ai/issues/1026)) ([874797a](https://github.com/Unique-AG/ai/commit/874797a58936bdf9f0ff6404cafffb17cb460b61))
* **unique-internal-search:** update log based on ff ([#1007](https://github.com/Unique-AG/ai/issues/1007)) ([f649a40](https://github.com/Unique-AG/ai/commit/f649a40e8f6770129649be028417659307f11eb3))
* **unique-internal-sesarch:** Internal message log update ([#1093](https://github.com/Unique-AG/ai/issues/1093)) ([fdb6a9d](https://github.com/Unique-AG/ai/commit/fdb6a9d32ccb9da814f337eeb796751723413810))
* **unique-orchestrator:** include uploaded files when int. search is … ([#1615](https://github.com/Unique-AG/ai/issues/1615)) ([a9961b3](https://github.com/Unique-AG/ai/commit/a9961b3a909821856dfd4483d402129f7df1f678))
* Use Aliases to set the UI Order ([#1083](https://github.com/Unique-AG/ai/issues/1083)) ([dc7e905](https://github.com/Unique-AG/ai/commit/dc7e90529bf4c6231c45d7579fe7ed34f0a8c767))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))
* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.18.0...unique-internal-search-v2026.20.0) (2026-05-08)


### Features

* **uploaded_search:** Update logic of Uploaded files ([#1591](https://github.com/Unique-AG/ai/issues/1591)) ([7407c95](https://github.com/Unique-AG/ai/commit/7407c95a7ac9498e268873794309c06d7c47c63b))


### Bug Fixes

* **internal-search:** Introduce message logger service for internal search and fix logger misbehaviour ([#1640](https://github.com/Unique-AG/ai/issues/1640)) ([c24d1cd](https://github.com/Unique-AG/ai/commit/c24d1cd0a24af04a4aec3040d303a456dc2155bb))
* **unique-orchestrator:** include uploaded files when int. search is … ([#1615](https://github.com/Unique-AG/ai/issues/1615)) ([a9961b3](https://github.com/Unique-AG/ai/commit/a9961b3a909821856dfd4483d402129f7df1f678))


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v1.2.43...unique-internal-search-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [1.2.43] - 2026-04-16
- Reducing limit based on max input tokens (speed improvement)

## [1.2.42] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [1.2.41] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [1.2.40] - 2026-04-10
- Fix `AttributeError` in `extract_selected_uploaded_file_ids` when payload lacks `additional_parameters` (e.g. magic table events from RfpAgent)
- Add regression test using `MagicTableBasePayload` spec to guard against future breakage

## [1.2.39] - 2026-04-09
- changing FF from enable_selected_uploaded_files_un_18470 to enable_selected_uploaded_files_un_18215

## [1.2.38] - 2026-04-02
- Adding logic about selected uploaded files

## [1.2.37] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [1.2.36] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [1.2.35] - 2026-03-31
- Chore: remove leftover poetry.toml config file

## [1.2.34] - 2026-03-26
- Expose Experimental Configs

## [1.2.33] - 2026-03-26
- Add configurable tool-response system reminder for citation enforcement
  - New `ToolResponseSystemReminderConfig` under `ExperimentalFeatures` with `enabled` toggle and customisable prompt
  - When enabled, the reminder text is attached as `system_reminder` on every successful `InternalSearch` tool response

## [1.2.32] - 2026-03-24
- Add regression coverage for readable Unicode in `InternalSearch` loop-history tool payloads
- Clarify that loop-history tool content remains JSON text while preserving readable Unicode when provided by `unique_toolkit`

## [1.2.31] - 2026-03-23
- Add `content_id` to uploaded document listings in the system prompt so the LLM can identify each document by its content ID

## [1.2.30] - 2026-03-05
- Build: migrate from Poetry to uv

## [1.2.29] - 2026-03-03
- Fix bug in `InternalSearchTool` when `correlation` is present in the event
  - Use `parent_chat_id` if correlation is present
  - Use `chat_id` if correlation is not present

## [1.2.28] - 2026-02-26
- Update message log

## [1.2.27] - 2026-02-25
- Remove `AliasChoices=ftsSearchLanguage` as its not used anymore (replaced with `searchLanguage`) 

## [1.2.26] - 2026-02-17
- Reverting fix the behavior so that when no knowledge base files are selected, only uploaded files are considered, rather than searching across all files.

## [1.2.25] - 2026-02-12
- Add optional `language_model_orchestrator` parameter (defaults to `None`) and pass to `pick_content_chunks_for_token_window()` for model-agnostic token counting. Ready for orchestrator to pass LLM in future update.

## [1.2.24] - 2026-02-11
- Fix the behavior so that when no knowledge base files are selected, only uploaded files are considered, rather than searching across all files.

## [1.2.23] - 2026-02-11
- Update message log for uploaded files based on feature flag

## [1.2.22] - 2026-02-05
- Adjust new feature flag logic

## [1.2.21] - 2026-01-20
- Fix tool naming for uploaded search

## [1.2.20] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [1.2.19] - 2026-01-16
- Add unified type checking CI with basedpyright

## [1.2.18] - 2026-01-13
- Fix test suite: add missing `__init__.py`, mock fixtures, and `_message_step_logger` attribute

## [1.2.17] - 2026-01-13
- Removing unused parameters from config
- Activating multiple search string execution by default

## [1.2.16] - 2026-01-12
- Fix message logswith new ChatUI

## [1.2.15] - 2026-01-12
- Include feature flag to have message logs compatible with new ChatUI

## [1.2.14] - 2026-01-05
- Bump unique_toolkit version

## [1.2.13] - 2025-12-29
- Bump unique_sdk version to `0.10.58`

## [1.2.12] - 2025-12-01
- Fix of multiple search queries: 
  - `max_search_strings` must be at lest 1
  - Only executed queries are shown in the message logs

## [1.2.11] - 2025-11-28
- Parallel search execution using asyncio.gather()
- Automatic deduplication of duplicate search strings
- Configurable limit on search strings via `max_search_strings`

## [1.2.10] - 2025-11-24
- Cosmetic code cleanness change for steplogger print of tool title

## [1.2.9] - 2025-11-24
- Bugfix for message log messages

## [1.2.8] - 2025-11-20
- Update toolkit version

## [1.2.7] - 2025-11-20
- Include message log messages

## [1.2.6] - 2025-11-20
- Fix bug of handling properly uploaded files that are expired1

## [1.2.5] - 2025-11-20
- Bump tiktoken to 0.12.0

## [1.2.4] - 2025-11-17
- Fix bug in search method when `exclude_uploaded_files` is True

## [1.2.3] - 2025-11-14
- Move pytest to dev dependencies

## [1.2.2] - 2025-11-10
- Temporarily reverting the removal of the `get_tool_call_result_for_loop_history` function, as it is still required for the Investment Research Agent. 

## [1.2.1] - 2025-11-06
- Upload and chat system reminder cleanup

## [1.2.0] - 2025-11-04
- Include system reminder for upload and chat tool about it being a forced tool in UniqueAI

## [1.1.0] - 2025-10-30
- Add support for multiple search strings in a single tool call
- Search results from multiple queries are interleaved for better diversity
- Add automatic deduplication of chunks by `chunk_id` when using multiple search queries
  - Prevents duplicate content from appearing in results when multiple related queries return the same chunks
  - Preserves first occurrence and logs number of duplicates removed
- Add automatic parsing and cleaning of search query operators1
  - Removes QDF (QueryDeservedFreshness) operators: `--QDF=0` to `--QDF=5` (freshness ratings)
  - Removes boost operators: `+(term)` and `+(multi word phrase)` for query term boosting

## [1.0.4] - 2025-10-28
- Removing unused tool specific `get_tool_call_result_for_loop_history` function
- Removing unused config `source_format_config`

## [1.0.3] - 2025-10-25
- Fix appending of metadata to chunks

## [1.0.2] - 2025-10-17
- Remove print statements originating from tool refactor

## [1.0.1] - 2025-09-30
- Fix bug in metadata filter in the search method.

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates

## [0.0.7] - 2025-09-17
- Updated to latest toolkit

## [0.0.6] - 2025-09-15
- Fix Minor bug in transforming toolResponse to toolCallResult

## [0.0.5] - 2025-09-05
- Fixed a bug around metadata-filter assignment

## [0.0.4] - 2025-09-05
- Fixed a bug around metadata-filter deep-copy

## [0.0.3] - 2025-09-01
- Migrated the `uploaded_search` into this package.

## [0.0.2] - 2025-09-01
- Migrated the `internal_search`.

## [0.0.1] - 2025-08-18
- Initial release of `internal_search`.
