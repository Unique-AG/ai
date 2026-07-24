# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.30.0...unique-six-v2026.32.0) (2026-07-24)


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.28.0...unique-six-v2026.30.0) (2026-07-17)


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.26.0...unique-six-v2026.28.0) (2026-07-03)


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.24.0...unique-six-v2026.26.0) (2026-06-22)


### Miscellaneous

* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.22.0...unique-six-v2026.24.0) (2026-06-04)


### Bug Fixes

* **deps:** resolve open Dependabot alerts via constraint-dependencies ([#1751](https://github.com/Unique-AG/ai/issues/1751)) ([f92b9f5](https://github.com/Unique-AG/ai/commit/f92b9f5d1c9d2145316d2bf1f9b91b8b359c2324))


### Miscellaneous

* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [2026.22.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.20.0...unique-six-v2026.22.0) (2026-05-21)


### Bug Fixes

* **security:** address Dependabot pillow alerts and CodeQL finding ([#1617](https://github.com/Unique-AG/ai/issues/1617)) ([6e49fcb](https://github.com/Unique-AG/ai/commit/6e49fcbf59fd6e93e36326869038b1f89f4c23d0))


### Miscellaneous

* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-six-v2026.18.0...unique-six-v2026.20.0) (2026-05-08)


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-six-v0.1.8...unique-six-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [0.1.8] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [0.1.7] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [0.1.6] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [0.1.5] - 2026-04-01
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [0.1.4] - 2026-03-31
- Docs: replace Poetry references with uv equivalents in README

## [0.1.3] - 2026-03-06
- Build: migrate from Poetry to uv
- Bump unique-toolkit to >=1.50.4
- Test: add unit tests for client, exceptions, and cert chain handling

## [0.1.2] - 2026-02-18

- Bump `cryptography` to `^46.0.5` to fix CVE-2026-26007

## [0.1.1] - 2026-01-08

- Fix unresolved import of get six client

## [0.1.0] - 2026-01-06

- Initial release of `unique_six`
