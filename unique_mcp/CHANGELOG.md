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

## [0.1.4] - 2026-02-11
- Add docs
- Use properties in oauth and oidc proxies

## [0.1.3] - 2025-01-20
- Add oidc proxy
- Add persistance options for oidc and oauth proxies

## [0.1.2] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [0.1.1] - 2025-12-17
- Add server settings

## [0.1.0] - 2025-12-5
- Setup for mcp utils
