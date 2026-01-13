# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.4] - 2026-01-13
- Clean up dependencies and add deptry configuration for CI compliance

## [1.1.3] - 2026-01-05
- Prevent Pipeline from crashing if any of the agentic steps fail

## [1.1.2] - 2026-01-05
- Bump unique_toolkit version

## [1.1.1] - 2025-12-18
- Early return if report is empty.

## [1.1.0] - 2025-12-17
### Added
- Protocol-based orchestration architecture with dependency injection
  - `StepNotifier` protocol for progress notifications
  - `SourceCollector`, `SourceSelector`, `SourceIterator` protocols for source management
  - `SourceRegistry` protocol for content tracking
  - `ReportingAgent` protocol for generation
- Agentic generation system with flexible execution strategies
  - `GenerationAgent` for SWOT component generation
  - `AgenticPlanExecutor` supporting sequential and concurrent execution modes
  - Configurable `max_concurrent_tasks` for parallel processing
- Intelligent source management pipeline
  - `SourceSelectionAgent`: LLM-based filtering to identify relevant sources
  - `SourceIterationAgent`: LLM-based prioritization and ordering of sources
  - Graceful handling of missed or irrelevant documents
- Enhanced citation infrastructure
  - `ContentChunkRegistry` with memory persistence
  - Unique ID generation with collision detection
  - Registry initialization from cached state
- `SummarizationAgent` for executive summary generation
  - Reference remapping and citation management
  - Integration with chat service for streaming responses

### Changed
- Orchestration flow now uses protocol-based dependency injection for better testability and modularity
- Source processing pipeline: collect → iterate → select → generate (vs. previous direct processing)
- Generation flow simplified with operation-based processing (GENERATE, MODIFY, NOT_REQUESTED)
- Notification system decoupled through `StepNotifier` protocol
- Memory service abstracted for state persistence across components

### Improved
- Comprehensive test suite with 100% coverage of new architecture
  - Component-level tests with all external dependencies mocked
  - Tests for orchestration, generation, source management, and delivery
  - Async testing patterns with proper mock handling

## [1.0.0] - 2025-12-08
### Added
- Orchestrator-driven SWOT workflow that chains source collection, LLM-based source selection, extraction, and progressive reporting with shared memory.
- Source management layer with date-relevancy iterator, configurable earnings call DOCX rendering, and revamped prompts/models for each SWOT component.
- Progressive reporting agent and consolidated report models that stream citations and render markdown/DOCX outputs.

### Changed
- Configuration regrouped under source management/extraction/report generation to match the new architecture; package version bumped to 1.0.0.

### Fixed
- Prevent duplicate earnings call ingestion and fall back gracefully when source filenames lack date metadata.
- Structured output generation now retries on parsing failures to reduce extraction/reporting errors.

## [0.2.4] - 2025-11-24
- Add session state tracking (RUNNING, COMPLETED, FAILED) with `SessionState` enum
- Add `render_session_info()` method to display session details in progress messages
- Add `ingest_docx_report` configuration field to control DOCX ingestion (defaults to True)
- Update method signatures to use `session_config` instead of `company_name`
- set completed at issue at the swot.

## [0.2.3] - 2025-11-24
- Remove Knowledge Base Service dependency

## [0.2.2] - 2025-11-20
- Remove chat service dependency from docx generator (following upgrade of toolkit)

## [0.2.1] - 2025-11-19
- Fix bug caused by the Session Config that was loaded during the initialization

## [0.2.0] - 2025-11-18

### Added
- **Earnings Call Integration**: Full support for collecting and analyzing earnings call transcripts via Quartr API
  - Async earnings call collection with automatic ingestion into knowledge base
  - DOCX generation from earnings call transcripts
  - Content caching to prevent duplicate ingestion
  - Configurable date range for earnings call collection
- **Visual Progress Bar**: Temporary progress tracking with emoji indicators and real-time status messages
- **Component-Specific Prompts**: New extraction and summarization prompts for each SWOT dimension (Strengths, Weaknesses, Opportunities, Threats)
- **Session Schema**: New configuration schemas for company listings and session management
- **Citation Footer**: Jinja2 template for citation appendix in DOCX reports
- **Utils Module**: Shared utility functions for content conversion

### Changed
- **Citation System Refactor**: Simplified inline citations to document-level references
  - Removed complex multi-pass citation processing
  - Improved citation placement and formatting
  - Better reference deduplication
- **Progress Tracking Overhaul**: Replaced message execution system with custom progress bar
  - Visual progress indicators (⚪️ → 🟡 → 🟢/🔴)
  - Step-by-step progress messages
  - Better failure state handling
- **Collection Context**: Enhanced with company information, earnings call settings, and date ranges
- **Async/Await Improvements**: Better async handling throughout collection and ingestion workflows
- **Report Delivery**: Enhanced with company name in report titles and improved formatting

### Dependencies
- Added `unique_quartr` for earnings call integration

## [0.1.1] - 2025-11-12
- Move ruff to dev dependencies

## [0.1.0] - 2025-08-18
- Initial release of `unique_swot`.
