# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [1.9.1] - 2025-01-30
- Raise error for failed Custom API search engine requests

## [1.9.0] - 2025-01-29
- Add language model config option to bing search

## [1.8.3] - 2025-01-28
- Add setting params to pass configuration to async_client in custom_api search engine

## [1.8.2] - 2025-01-19
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