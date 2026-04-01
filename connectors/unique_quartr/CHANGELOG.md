# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.8] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [0.2.7] - 2026-03-31
- Docs: replace Poetry references with uv equivalents in README

## [0.2.6] - 2026-03-06
- Build: migrate from Poetry to uv
- Bump unique-toolkit to >=1.50.4

## [0.2.5] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [0.2.4] - 2026-01-16
- Add unified type checking CI with basedpyright

## [0.2.3] - 2026-01-13
- Add deptry to dev dependencies for CI dependency checks

## [0.2.2] - 2026-01-05
- Bump unique_toolkit version

## [0.2.1] - 2025-11-18
- Fix to use correct field (`query_params_dump_options`) for `model_params_dump_options`

## [0.2.0] - 2025-11-18

- Add `QuartrEarningsCallTranscript` class for parsing and exporting earnings call transcripts to markdown
- Add support for fetching events by `company_ids` as alternative to `ticker/exchange/country`
- Change `fetch_company_events()` to return `EventResults` object with `.data` attribute
- Change `fetch_event_documents()` to return `DocumentResults` object with `.data` attribute
- Change API credentials to require base64 encoding in environment variables
- Update to `unique-toolkit` v1.27.0 experimental endpoint builder
- Add `jinja2` dependency for template rendering
- Fix credential validation and datetime serialization

## [0.1.0] - 2025-08-18

- Initial release of `unique_quartr`
