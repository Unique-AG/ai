# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.30.0...unique-internal-search-v2026.32.0) (2026-07-24)


### Features

* Token count analytics ([#2112](https://github.com/Unique-AG/ai/issues/2112)) ([f475dc4](https://github.com/Unique-AG/ai/commit/f475dc4606dd723e0fecfcdd09ace2f9c329e960))


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.28.0...unique-internal-search-v2026.30.0) (2026-07-17)


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.26.0...unique-internal-search-v2026.28.0) (2026-07-03)


### ⚠ BREAKING CHANGES

* **unique_toolkit:** MagicTableEvent no longer subclasses ChatEvent—use AssistantWebhookEvent for the shared envelope; get_initial_debug_info is ChatEvent-only (AttributeError otherwise). MagicTableBasePayload no longer carries stub user_message/assistant_message defaults.

### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))
* **unique_toolkit:** split ChatEvent and MagicTableEvent webhook types ([#1937](https://github.com/Unique-AG/ai/issues/1937)) ([ec75cda](https://github.com/Unique-AG/ai/commit/ec75cda5b3d79c74342f468ed3a9c61a639c76d9))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.24.0...unique-internal-search-v2026.26.0) (2026-06-22)


### Miscellaneous

* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.22.0...unique-internal-search-v2026.24.0) (2026-06-04)


### Bug Fixes

* **deps:** resolve open Dependabot alerts via constraint-dependencies ([#1751](https://github.com/Unique-AG/ai/issues/1751)) ([f92b9f5](https://github.com/Unique-AG/ai/commit/f92b9f5d1c9d2145316d2bf1f9b91b8b359c2324))


### Miscellaneous

* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [2026.22.0](https://github.com/Unique-AG/ai/compare/unique-internal-search-v2026.20.0...unique-internal-search-v2026.22.0) (2026-05-21)


### Features

* **unique_internal_search:** Allow agent to search inside specific files ([#1720](https://github.com/Unique-AG/ai/issues/1720)) ([ce1911a](https://github.com/Unique-AG/ai/commit/ce1911a06e1de69e495e285157385e4244da43be))
* **unique_orchestrator:** Allow configuration of UploadedSearch Tool ([#1674](https://github.com/Unique-AG/ai/issues/1674)) ([1e41209](https://github.com/Unique-AG/ai/commit/1e412094a97b574ef1dac422ed62793667a34c8d))


### Miscellaneous

* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))

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
