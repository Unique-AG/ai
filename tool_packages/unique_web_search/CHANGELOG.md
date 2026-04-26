# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-web-search-v2026.18.0...unique-web-search-v2026.20.0) (2026-04-26)


### Bug Fixes

* **web-search:** correct "triggerd" typo to "triggered" in elicitation messages ([#1526](https://github.com/Unique-AG/ai/issues/1526)) ([dc3c1cc](https://github.com/Unique-AG/ai/commit/dc3c1ccd8fd8b69bf320d35178ced2977a900afc))


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-web-search-v1.17.0...unique-web-search-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [1.17.0] - 2026-04-16
### Changed
- **Grounding search layout:** Bing and VertexAI helpers now live under `utils/grounding/`. Shared Pydantic models (`GroundingSearchResults`, `ResultItem`, prompts) sit in `grounding/models.py`; shared parsing (`ResponseParser`, `JsonConversionStrategy`, `LLMParserStrategy`, `convert_response_to_search_results`) lives in `grounding/response_parsing.py`. Bing-specific code is in `grounding/bing/`; Vertex client, Gemini call, config, and citation handling are in `grounding/vertexai/`. Legacy `utils/bing/` and duplicate `utils/vertexai/` were removed; import from `utils.grounding.vertexai` instead.
- **VertexAI search flow:** A single grounded `generate_content` call produces the raw response; citations are applied with `add_citations`, then the same strategy pipeline as Bing (`JsonConversionStrategy` then `LLMParserStrategy`) turns the text into `WebSearchResult` list. Structured-output recovery no longer uses a second Gemini call; the toolkit language model handles fallback parsing, which avoids an extra Vertex round-trip and should be faster. `VertexAI` now receives `language_model_service` from the search engine factory (same pattern as Bing).
- **VertexAI config:** Model id field is `vertexai_model_name` (default `gemini-3-flash-preview`); fallback parser LLM is `fallback_language_model`. Removed the separate grounding-system-instruction field in favor of `generation_instructions` plus the shared `RESPONSE_RULE` schema block.

## [1.16.5] - 2026-04-16
- Fix CodeQL `py/incomplete-url-substring-sanitization` warnings in test assertions

## [1.16.4] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [1.16.3] - 2026-04-14
- Minor fixes for brave search engine

## [1.16.2] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [1.16.1] - 2026-04-12
### Fixed
- Validate `--parallel` crawl option to reject zero and negative values that caused silent data loss or cryptic `range()` errors

## [1.16.0] - 2026-04-11
### Added
- **`unique-websearch` CLI** with two-phase architecture for AI-assisted web search:
  - **`search` subcommand** — queries the configured search engine and returns URLs with snippets; supports `--json` for machine-readable output and `--fetch-size/-n` to control result count
  - **`crawl` subcommand** — fetches full page content for a list of URLs with configurable parallelism (`--parallel/-p`, default 10); accepts URLs as arguments or via `--stdin` for piping
  - Engine and crawler auto-selected from `ACTIVE_SEARCH_ENGINES` / `ACTIVE_INHOUSE_CRAWLERS` environment variables
  - Optional JSON config file (`~/.unique-websearch.json`) for non-secret overrides
  - Agent skill documentation (`SKILL.md`) for AI-assisted two-phase workflow
- `click` dependency for CLI framework

## [1.15.5] - 2026-04-10
- Mark v3 as experimental

## [1.15.4] - 2026-04-09
### Changed
- Depend on `unique-toolkit[monitoring]>=1.69.6` so `prometheus_client` is installed transitively and metrics instrumentation always resolves
- `[tool.uv.sources]`: resolve `unique-toolkit` via `{ workspace = true }` like other workspace members (required for root `uv lock`)

### Added
- Tests for Prometheus metric definitions and `metric_scope` integration with package histograms (including `llm_errors` with `error_type` on exception)

### Fixed
- `llm_errors_total`: add `error_type` label so `metric_scope` error recording matches Prometheus label set (avoids `ValueError` masking real LLM failures)
- `search_total`: increment inside the search `metric_scope` so attempts are counted when the search API raises
- Remove unused `llm_token_usage_total` metric until token usage is wired

## [1.15.3] - 2026-04-07
### Changed
- VertexAI client now falls back to Application Default Credentials (ADC) when no explicit service account credentials are configured, enabling Workload Identity and other ambient credential flows

### Added
- Dedicated test suite for VertexAI client credential dispatch, ADC fallback, and error handling

## [1.15.2] - 2026-04-03
- Style: apply ruff formatting to test_executors.py

## [1.15.1] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [1.15.0] - 2026-03-30
### Added
- **Argument Screening**: LLM-based screening agent that inspects tool call arguments for sensitive information (PII, credentials, financial data, health info) before execution, raising `ArgumentScreeningException` to block unsafe calls
- `ArgumentScreeningService` with structured output (`ArgumentScreeningResult`) and configurable Jinja2 prompt templates (system, user, guidelines)
- `ArgumentScreeningConfig` under `ExperimentalFeatures` with `enabled` flag (default off), customizable `guidelines`, `system_prompt`, and `user_prompt_template`
- Comprehensive test suite for argument screening config, result model, exception, and service behavior
## [1.14.4] - 2026-03-30
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [1.14.3] - 2026-03-25
### Fixed
- Replace direct `UserAgent` usage in crawlers with `get_random_user_agent()` utility that appends a randomized email to the Chrome user agent, reducing the likelihood of crawl requests being blocked

## [1.14.2] - 2026-03-25
### Added
- Experimental **Tool Response Reminder**: `enable_system_reminder` (default off) and `system_reminder_prompt` (defaults to the standard source citation template) under Experimental Features.
- Explicit V3 prompts

## [1.14.1] - 2026-03-19
### Added
- `WebSearchV3Executor` for snippet-based relevance filtering before crawling.


## [1.14.0] - 2026-03-19
### Added
- **LLM Guard Judge** (`LLMGuardJudge`): dedicated GDPR Art. 9 compliance judge with four sanitization pipeline modes — Always Sanitize, Judge Only, Judge and Sanitize, and Judge then Sanitize — each with its own structured-output response model and Jinja2 prompt template
- **Keyword Redact mode** (`LLMKeywordRedact`): new sanitization strategy that extracts sensitive phrases via LLM and applies local two-pass redaction (exact regex + fuzzy sliding-window via `rapidfuzz`) without summarization, preserving original page structure
- **`SanitizeMode` enum**: configurable pipeline mode selector (`always_sanitize`, `judge_only`, `judge_and_sanitize`, `judge_then_sanitize`, `keyword_redact`) with human-readable UI labels
- **Character sanitization** (`CharacterSanitize`): new cleaning strategy that strips null bytes, control characters, and Unicode non-characters from web page content and snippets before downstream processing
- New Jinja2 prompt templates: `judge_prompt.j2`, `judge_and_sanitize_prompt.j2`, `keyword_extract_prompt.j2`, `page_context.j2`
- `PrivacyFilterConfig` and `PromptConfig` sub-models on `LLMProcessorConfig` for structured, granular configuration of privacy filtering and prompt templates
- `ProcessingStrategiesSettings` (`settings.py`): typed Pydantic-settings model replacing raw JSON dict parsing for the `LLM_PROCESS_CONFIG` env var, with nested `PrivacyFilterEnvConfig` and `PromptEnvConfig` sub-models
- Comprehensive test suites: `test_character_sanitize.py` (character sanitizer), `test_prompt_rendering.py` (765-line Jinja2 template rendering and response model field ordering tests)
- `rapidfuzz` dependency for fuzzy keyword redaction matching

### Changed
- Refactored `LLMProcessorConfig`: flat `sanitize`, `sanitize_rules`, `system_prompt`, `user_prompt` fields replaced with nested `PrivacyFilterConfig` and `PromptConfig` sub-models
- Replaced `_DEFAULTS` dict / `_get_from_env` helper with typed `LLMProcessorEnvConfig` Pydantic model; `_merge_config_with_env` now uses recursive deep-merge (`_deep_merge`) for correct nested override semantics
- `LLMProcessorResponse` and `LLMGuardResponse` extracted to dedicated `schema.py` and `llm_guard_judge.py` modules; `LLMGuardResponse` no longer inherits from `LLMProcessorResponse`
- `LLMProcess.__call__` now dispatches to `_run_summarize`, `_run_guard_judge`, or `_run_keyword_redact` based on `sanitize_mode`
- `ProcessingStrategyKwargs.query` changed from `NotRequired` to required
- Cleaning strategies now run on both `page.content` and `page.snippet`
- Web page chunk rendering switched from inline XML tags to a Jinja2 `_PLACEHOLDER_CONTENT_TEMPLATE` for structured `<WebPageChunk>` output
- Simplified `system_prompt.j2` and `user_prompt.j2`: removed `redaction_map` section, replaced `snippet`/`summary` output fields with `sanitized_content`, moved sanitize reminder to top of user prompt
- Updated `test_llm_process_env_config.py` to cover new typed config models, nested merge semantics, and structure-matching assertions


## [1.13.1] - 2026-03-17
### Fixed
- Use `AsyncioRequestsTransport` with `certifi` SSL verification for both `WorkloadIdentityCredential` and `AIProjectClient` when `use_unique_private_endpoint_transport` is enabled, fixing certificate validation failures in private endpoint environments


## [1.13.0] - 2026-02-27
### Added
- Environment-based LLM processor config override (`LLM_PROCESS_CONFIG` env var): when set to valid JSON, all `LLMProcessorConfig` fields are frozen from the environment and UI editing is disabled via `ui:disabled` RJSF tags
- `_DEFAULTS` dict and `_get_from_env` helper for resolving LLM processor defaults from env with snake_case/camelCase key fallback
- `_merge_config_with_env` to merge space-admin config with env overrides at runtime
- Bing `agent_id` and `endpoint` fields now default from `env_settings.azure_ai_assistant_id` and `env_settings.azure_ai_project_endpoint`
- `get_or_create_agent_id` short-circuits when `azure_ai_assistant_id` is set in env, skipping agent discovery/creation
- New settings fields: `azure_ai_assistant_id`, `llm_process_config` (with JSON validation)

### Changed
- `BingSearch` now accepts `LanguageModelService` directly and constructs response parsers (`JsonConversionStrategy`, `LLMParserStrategy`) internally instead of receiving them from the factory
- Renamed `azure_ai_bing_ressource_connection_string` to `azure_ai_bing_resource_connection_string` (typo fix)
- Default `azure_ai_bing_agent_model` changed from `gpt-4o` to `gpt-4o-deployment`

## [1.12.1] - 2026-02-23
### Changed
- Improved LLM Guard accuracy through prompt restructuring, query-level refusal for Art. 9 sensitive queries, and more precise structured output field descriptions

## [1.12.0] - 2026-02-23
### Added
- LLM-based content processing strategy (`LLMProcess`) that summarizes web page content using an AI model before injecting it into the prompt context
- Privacy filtering (sanitization) mode for the LLM processor: when enabled, instructs the AI to redact GDPR Art. 9 sensitive personal data from web search content
- Configurable Jinja2 prompt templates for the LLM content processor (system, user, and sanitization guidelines)
- `Truncate` strategy as a standalone, configurable processing step with its own `TruncateConfig`
- Content cleaning pipeline with separate `LineRemoval` and `MarkdownTransform` strategies, each independently configurable

### Changed
- Refactored `ContentProcessor` into a strategy-based architecture: cleaning strategies run first, then processing strategies (`Truncate`, `LLMProcess`) are applied sequentially
- `ContentProcessorConfig` replaced monolithic fields (`strategy`, `language_model`, `max_tokens`, `summarization_prompt`) with composable sub-configs (`CleaningConfig`, `ProcessingStrategiesConfig`)
- Improved all config field descriptions and titles across V1/V2 configs for better UI readability

## [1.11.4] - 2026-02-16
- Messagelog alignment

## [1.11.3] - 2026-02-13
- method `_create_agent_run_with_agent_id` in `runner.py` shouldn't use model from settings

## [1.11.2] - 2026-02-13
- Purely Cosmetic Change to improve Search Engine names in the UI
- MessageLog get updated at the end of the the execution of websearch
- Query Elicitation disabled by default

## [1.11.1] - 2026-02-13
- `agent_id` and `endpoint` fields on `BingSearchConfig` to allow using a pre-configured agent and project endpoint from config instead of relying solely on auto-provisioning
- Citation replacement in Bing agent responses: `MessageTextUrlCitationAnnotation` placeholders are now converted to readable markdown links
- `validate_custom_web_search_api_method` field validator on settings to gracefully coerce invalid method values to `None` instead of failing at startup
- Migrated Bing client and runner to fully async Azure SDK (`azure.ai.projects.aio`, `azure.identity.aio`), eliminating thread-blocking synchronous calls
- `get_project_client` now accepts an `endpoint` parameter with fallback: environment variable takes precedence, then config value
- `create_and_process_run` now branches on `agent_id`: when provided, uses the existing agent directly; when empty, auto-provisions via `get_or_create_agent_id`
- `LLMParserStrategy` now uses `GroundingWithBingResults` as its structured output model instead of `WebSearchResults`
- `ResultItem` and `GroundingWithBingResults` models now enforce `extra="forbid"` to reject unexpected fields

## [1.11.0] - 2026-02-12
- Automatic Bing grounding agent creation and discovery via Azure AI Agents SDK
- `BingGroundingTool` integration for native Bing search within agent runs
- Strategy-pattern response parsing: `JsonConversionStrategy` with `LLMParserStrategy` fallback
- Configurable `generation_instructions` field on `BingSearchConfig`
- Refactored Bing client: merged `identity.py` and `project.py` into `client.py`
- Removed manual `agent_id` and `endpoint` config fields (now auto-managed)
- New env settings: `azure_ai_bing_agent_model`, `azure_ai_project_endpoint`, `azure_ai_bing_ressource_connection_string`

## [1.10.1] - 2026-02-09
- Migrate to model-specific token counting from unique_toolkit 1.46.1
- Add optional `language_model_orchestrator` parameter to use orchestrator's LLM for token counting

## [1.10.0] - 2026-02-05

### Added
- **Query Elicitation**: New `QueryElicitationService` for user approval of search queries before execution
  - Users can review and modify proposed queries through an interactive form
  - Configurable timeout and enable/disable options
  - Support for handling declined, cancelled, expired, or failed elicitations
  - Query Elicitation is behind a feature flag
- **Message Logging Service**: New `WebSearchMessageLogger` for improved progress tracking and state management

### Changed
- Refactored executor architecture to use dependency injection with context objects
- Updated feature flag from `is_new_answers_ui_enabled` to `enable_new_answers_ui_un_14411.is_enabled`

## [1.9.1] - 2026-01-30
- Raise error for failed Custom API search engine requests

## [1.9.0] - 2026-01-29
- Add language model config option to bing search

## [1.8.3] - 2026-01-28
- Add setting params to pass configuration to async_client in custom_api search engine

## [1.8.2] - 2026-01-19
- Parse mode "v2 (beta)" as "v2" for search mode

## [1.8.1] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [1.8.0] - 2026-01-16
- Make V2 mode as default search mode

## [1.7.8] - 2026-01-16
- Add unified type checking CI with basedpyright

## [1.7.7] - 2026-01-15
- Add `pytest-cov` dev dependency for coverage testing

## [1.7.6] - 2026-01-13
- Cleanup configuration

## [1.7.5] - 2026-01-12
- Include feature flag to have message logs compatible with new ChatUI

## [1.7.4] - 2025-12-29
- Switch from poetry to uv and introduce lowest-direct version testing and deptry for transitive dependency usage errors and detection
of unused dependencies

## [1.7.3] - 2025-12-17
- Bump unique_toolkit version to `1.38.3`

## [1.7.2] - 2025-12-17
- Update failsafe execution import path

## [1.7.1] - 2025-12-03
- Use strings instead of dict to configure payload to ensure better integration with current frontend

## [1.7.0] - 2025-12-01
- Added full VertexAI search engine integration (Gemini + Google grounding) with service-account authentication and redirect resolution.
- Introduced the pluggable Custom API search engine so customers can register any compliant web-search backend via simple GET/POST specs.

## [1.6.1] - 2025-11-20
- Cleaner call of tool name with display name in logger tool.

## [1.6.0] - 2025-11-20
- Include message log messages

## [1.5.4] - 2025-11-12
- Move pytest and pytest-asyncio to dev dependencies

## [1.5.3] - 2025-11-10
- Use SkipJsonSchema for mode under WebSearchMode config to prevent displaying an editable field

## [1.5.2] - 2025-11-10
- Separate the configuration of modes to prevent breaking the frontend

## [1.5.1] - 2025-11-10
- Flag V2 mode and Advanced Query Refinement as Beta

## [1.5.0] - 2025-11-10
- Add support for private endpoint transport (for Workload identity authentication)

## [1.4.0] - 2025-11-10
- Expose Search Mode Configuration

## [1.3.6] - 2025-10-29
- Fix minor notification display issue and remove unnecssary log

## [1.3.5] - 2025-10-29
- Upgrading azure-ai-projects to 1.0.0 version (relevant for bing search)

## [1.3.4] - 2025-10-28
- Removing unused tool specific `get_tool_call_result_for_loop_history` function

## [1.3.3] - 2025-10-14
- Fix bug in selecting the refine query mode

## [1.3.2] - 2025-10-10
- Add possibility to switch proxy auth protocol (http or https)

## [1.3.1] - 2025-10-09
- Update loading path of `DEFAULT_GPT_4o` from `unique_toolkit` 

## [1.3.0] - 2025-10-06
- **Proxy Authentication Support**: Route search engine and crawler requests through proxies with multiple authentication methods:
  - Username/Password authentication
  - Client Certificate authentication
- **Active Crawlers**: Dynamic crawler activation system allowing selective enablement of crawling services:
  - **In-house crawlers**: Control activation via environment variables for internal crawlers (Basic, Crawl4AI.)
  - **External crawlers**: Auto-activate when API keys are configured (Firecrawl, Jina, Tavily)
- **Test Coverage**: Added comprehensive tests to ensure web search tool stability and reliability

## [1.2.0] - 2025-09-29
- Mark new crawlers as experimental

## [1.1.0] - 2025-09-24
- Set active search engine through `active_search_engines` env variable

## [1.0.3] - 2025-09-23
- Add field to track execution time of the excutors

## [1.0.2] - 2025-09-23
- Paralellize steps execution for V2 mode.

## [1.0.1] - 2025-09-23
- Add octet-stream to blacklisted content-types and allow to change the unwanted-types from config

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates

### [0.2.0] - 2025-09-17
- Add support for Brave and Grounding by Bing through azure

## [0.1.4] - 2025-09-17
- Updated to latest toolkit

### [0.1.3] - 2025-09-17
- Add content utf8 cleanup logic when processing content

### [0.1.2] - 2025-09-15
- Fix Minor bug in transforming toolResponse to toolCallResult

## [0.1.1] - 2025-09-15
### Added
- **WebSearchV2Executor**: New step-based execution model supporting both search and direct URL reading operations
- **BaseWebSearchExecutor**: Abstract base class providing common functionality between executor versions
- **Enhanced Schema**: New model `WebSearchPlan` for structured web search planning
- **Flexible Step Execution**: Support for mixed search and URL reading operations in a single plan

### Changed
- **Architecture Refactor**: Improved executor structure with better separation of concerns
- **Configuration Enhancement**: Added experimental features flag to switch between V1 and V2 modes
- **Progress Reporting**: Enhanced with step-specific notifications and better user feedback

### Maintained
- **Backward Compatibility**: Existing V1 executor functionality preserved
- **API Consistency**: No breaking changes to existing tool interfaces

## [0.1.0] - 2025-09-12
- Code simplification
- Enable new crawlers
- Default cleaning of search results
- Refactor of code structure and crawler location

## [0.0.6] - 2025-09-05
- Updated unique_web_search README.

## [0.0.5] - 2025-09-04
- Path change of loading local .env.

## [0.0.4] - 2025-09-01
- Reduce default crawler timeout to 10s.

## [0.0.3] - 2025-08-18
- Auto-register Tool in Factory.

## [0.0.2] - 2025-08-18
- Moved out of private repo to public repo.

## [0.0.1] - 2025-08-18
- Initial release of `web_search`.
