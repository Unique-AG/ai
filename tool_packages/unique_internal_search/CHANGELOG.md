# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-10-14
- Add support for multiple search strings in a single tool call
- Search results from multiple queries are now interleaved for better diversity
- Updated tool parameter from `search_string` to `search_strings` (list)

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