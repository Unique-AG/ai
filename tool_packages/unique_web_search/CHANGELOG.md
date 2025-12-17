# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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