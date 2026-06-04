# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-search-proxy-v2026.22.0...unique-search-proxy-v2026.24.0) (2026-06-04)


### Features

* **search-proxy:** UN-21527 CalVer container publish via package matrix ([#1785](https://github.com/Unique-AG/ai/issues/1785)) ([4abe85f](https://github.com/Unique-AG/ai/commit/4abe85f54f7a5f33ab77a07dc62c3da9e4138dca))


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))
* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))
* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))
* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [0.2.1] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [0.2.0] - 2026-04-14
- Refactor: replace `web/` directory with standard `unique_search_proxy/` package layout
- Refactor: update all internal imports to use fully-qualified `unique_search_proxy.*` paths
- Build: update Dockerfile to copy `unique_search_proxy/` package and standalone `entrypoint.sh`
- Build: update `entrypoint.sh` uvicorn target to `unique_search_proxy.app:app`

## [0.1.6] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Fix: use `--no-config` in Docker `uv pip install` to prevent `exclude-newer` from hiding lockfile-pinned versions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [0.1.5] - 2026-04-07
- Build: align Docker-installed uv with CI by passing `UV_VERSION` from `setup-uv` (`uv-version` output); default `ARG` remains for local `docker build`

## [0.1.4] - 2026-04-03
- Build: remove unused `lxml` constraint-dependency (no lxml in dependency tree)

## [0.1.3] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [0.1.2] - 2026-03-30
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [0.1.1] - 2026-03-06
- Build: migrate from Poetry to uv
- Test: add unit tests for schemas, search engines, response handler, and API endpoints

## [0.1.0] - 2025-12-2
- Introduces the **Unique Search Proxy**
