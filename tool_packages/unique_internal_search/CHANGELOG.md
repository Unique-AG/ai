# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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