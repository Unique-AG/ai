# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2025-11-20
- Update `unique_toolkit` to 1.28.9

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