# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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