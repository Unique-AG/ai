# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-10-21
- Add automatic parsing and cleaning of search query operators
  - Removes QDF (QueryDeservedFreshness) operators: `--QDF=0` to `--QDF=5` (freshness ratings)
  - Removes boost operators: `+(term)` and `+(multi word phrase)` for query term boosting
  - Search strings are automatically cleaned before execution for cleaner search queries
- Update system prompts to be more concise and GPT-5 optimized
  - Freshness rating and boosting operator are now demanded in the prompt but parsed later
  - Modernized instruction format with clearer query splitting guidelines

## [1.1.0] - 2025-10-21
- Add support for multiple search strings in a single tool call
- Search results from multiple queries are now interleaved for better diversity
- Updated tool parameter from `search_string` to `search_strings` (accepts both string and list)
- **BREAKING (with backwards compatibility):** Renamed parameter `search_string` to `search_strings` in search method
  - Old `search_string` parameter still works with deprecation warning for backwards compatibility
  - Config parameter `param_description_search_string` renamed to `param_description_search_strings` (old name still supported)
- Add automatic deduplication of chunks by `chunk_id` when using multiple search queries
  - Prevents duplicate content from appearing in results when multiple related queries return the same chunks
  - Preserves first occurrence and logs number of duplicates removed

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