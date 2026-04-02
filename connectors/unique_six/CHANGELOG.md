# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-03-31
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
