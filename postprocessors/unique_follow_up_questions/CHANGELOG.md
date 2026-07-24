# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.30.0...unique-follow-up-questions-v2026.32.0) (2026-07-24)


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.28.0...unique-follow-up-questions-v2026.30.0) (2026-07-17)


### Features

* **unique_follow_up_questions:** report per-invocation LLM usage [UN-20907] ([#2077](https://github.com/Unique-AG/ai/issues/2077)) ([7bd0275](https://github.com/Unique-AG/ai/commit/7bd02753e71bd7aee7b9f7e1b7ae0536c944d5a8))


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.26.0...unique-follow-up-questions-v2026.28.0) (2026-07-03)


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.24.0...unique-follow-up-questions-v2026.26.0) (2026-06-22)


### Miscellaneous

* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.22.0...unique-follow-up-questions-v2026.24.0) (2026-06-04)


### Features

* **unique_orchestrator:** RJSF textarea tags for agent prompt config ([#1780](https://github.com/Unique-AG/ai/issues/1780)) ([96691f0](https://github.com/Unique-AG/ai/commit/96691f0a1beae47529b6eb0d09d6f8358ab99b81))


### Bug Fixes

* **deps:** resolve open Dependabot alerts via constraint-dependencies ([#1751](https://github.com/Unique-AG/ai/issues/1751)) ([f92b9f5](https://github.com/Unique-AG/ai/commit/f92b9f5d1c9d2145316d2bf1f9b91b8b359c2324))


### Miscellaneous

* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [2026.22.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.20.0...unique-follow-up-questions-v2026.22.0) (2026-05-21)


### Miscellaneous

* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v2026.18.0...unique-follow-up-questions-v2026.20.0) (2026-05-08)


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-follow-up-questions-v1.1.19...unique-follow-up-questions-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [1.1.19] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [1.1.18] - 2026-04-14
- Chore: migrate pytest config from `pytest.ini` to `pyproject.toml` with `importlib` import mode
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [1.1.17] - 2026-04-05
- Fix: use async `complete_async()` instead of sync `complete()` in follow-up question generation to avoid blocking the event loop and starving concurrent postprocessors
- Fix: handle `None` message text in `apply_postprocessing_to_response` to prevent TypeError

## [1.1.16] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [1.1.15] - 2026-03-30
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [1.1.14] - 2026-03-05
- Build: migrate from Poetry to uv
- Bump unique-toolkit to >=1.50.4

## [1.1.13] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [1.1.12] - 2026-01-16
- Add unified type checking CI with basedpyright

## [1.1.11] - 2026-01-15
- Add `pytest-cov` dev dependency for coverage testing

## [1.1.10] - 2026-01-13
- Add missing `pytest-asyncio` dev dependency

## [1.1.9] - 2026-01-13
- Fix test imports and update tests for GPT-4o structured output support

## [1.1.8] - 2026-01-05
- Bump unique_toolkit version

## [1.1.7] - 2025-12-29
- Bump unique_sdk version to `0.10.58`

## [1.1.6] - 2025-11-24
- Move jinja template helpers to unique_toolkit

## [1.1.5] - 2025-11-12
- Move pytest to dev dependencies

## [1.1.4] - 2025-10-13
- Remove image_url from history for follow-up question generation

## [1.1.3] - 2025-10-13
- Update alias for number_of_questions

## [1.1.2] - 2025-10-09
- Update loading path of `DEFAULT_GPT_4o` from `unique_toolkit`
- Include alias for number_of_questions

## [1.1.1] - 2025-10-06
- Switch default model used from `GPT-3.5-turbo (0125)` to `GPT-4o (1120)`

## [1.1.0] - 2025-10-01
- Include history in follow-up question generation

## [1.0.0] - 2025-09-18
- Bump toolkit version to allow for both patch and minor updates

## [0.0.4] - 2025-09-17
- Updated to latest toolkit
- Moved to to postprocessor location.

## [0.0.3] - 2025-08-22
- bugs fixed

## [0.0.2] - 2025-08-21
- bugs fixed

## [0.0.1] - 2025-08-18
- Initial release of `follow_up_questions`.
