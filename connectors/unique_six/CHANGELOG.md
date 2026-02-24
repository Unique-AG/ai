# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- Add your changelog entry below. Use a bump indicator to specify the version increment:
     +   YYYY-MM-DD  → patch (bug fixes, small changes)
     ++  YYYY-MM-DD  → minor (new features, backwards-compatible)
     +++ YYYY-MM-DD  → major (breaking changes)

  Example:
     + 2026-02-25
     - Fix token counting for streaming responses

  CI will automatically set the version number on merge. Do NOT edit the version in pyproject.toml. -->

<!-- CHANGELOG-BOUNDARY -->

## [0.1.2] - 2026-02-18

- Bump `cryptography` to `^46.0.5` to fix CVE-2026-26007

## [0.1.1] - 2026-01-08

- Fix unresolved import of get six client

## [0.1.0] - 2026-01-06

- Initial release of `unique_six`
