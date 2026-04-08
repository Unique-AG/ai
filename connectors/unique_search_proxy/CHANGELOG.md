# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-08
- Refactor: replace `web/` directory with standard `unique_search_proxy/` package layout
- Refactor: update all internal imports to use fully-qualified `unique_search_proxy.*` paths
- Build: update Dockerfile to copy `unique_search_proxy/` package and standalone `entrypoint.sh`
- Build: update `entrypoint.sh` uvicorn target to `unique_search_proxy.app:app`

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
