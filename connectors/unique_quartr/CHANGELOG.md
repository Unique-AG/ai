# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2025-12-16
- chore(deps): Bump urllib3 from 2.5.0 to 2.6.2

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
