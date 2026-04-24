# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.18.2](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.18.1...unique-mcp-v2026.18.2) (2026-04-24)


### Miscellaneous

* **unique-mcp:** Synchronize ai versions

## [2026.18.1](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.18.0...unique-mcp-v2026.18.1) (2026-04-24)


### Miscellaneous

* **unique-mcp:** Synchronize ai versions

## [2026.18.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v0.3.3...unique-mcp-v2026.18.0) (2026-04-23)


### Miscellaneous

* arm release 2026.18.0 ([#1493](https://github.com/Unique-AG/ai/issues/1493)) ([bc435b2](https://github.com/Unique-AG/ai/commit/bc435b2c5838a9e16484fb054beb277b8262c136))

## [0.3.3] - 2026-04-22
- Add `MetaKeys` StrEnum (`unique.app/auth/*`, `unique.app/chat/*`) and `META_FLAT_ALIASES` for FF-gated camelCase fallback
- Add `ContextRequirements` + `merge_tool_meta` for tools to declare required `_meta` keys
- Add `get_request_meta` injector for tools that need raw `_meta` access beyond auth/chat context
- Refactor `get_unique_settings` to compose auth/chat context from `_meta` using `MetaKeys`

## [0.3.2] - 2026-04-20
- Add `[tool.uv.exclude-newer-package]` entry exempting `unique-toolkit` from the root workspace `exclude-newer` cutoff so recent workspace releases resolve correctly under `UV_NO_SOURCES=1`

## [0.3.1] - 2026-04-16
- Remove stale per-package `[tool.uv]` config and tracked `uv.lock` — unique_mcp uses the workspace root lockfile
- Move `lxml>=5.0.0` constraint to root `pyproject.toml`

## [0.3.0] - 2026-04-15

### Added
- Add `get_unique_settings()`, `get_unique_service_factory()`, and `get_unique_userinfo()` functional injectors for per-request auth resolution
- Add `UniqueUserInfo` model with `user_id`, `company_id`, and optional `email`
- Export new injectors from `unique_mcp` package `__init__`

### Removed
- Remove `UniqueContextProvider` class (`provider/context_provider`)
- Remove `create_unique_mcp_server()` factory and `UniqueMCPServerBundle` (`server`)

### Changed
- Replace class-based context provider with standalone functions backed by `UniqueServiceFactory`
- Auth priority unchanged: `_meta` > JWT claims > env variables

## [0.2.6] - 2026-04-15
- Chore: standardize pytest configuration across workspace packages

## [0.2.5] - 2026-04-14
- Chore: add `importlib` import mode to pytest config to prevent namespace collisions
- Chore: update `exclude-newer-package` timestamps and lockfile refresh

## [0.2.4] - 2026-04-03
- Build: add `lxml>=5.0.0` constraint-dependency for transitive lxml via docxtpl

## [0.2.3] - 2026-04-02
- Chore: migrate to uv workspace; switch local dependency sources from path-based to workspace references

## [0.2.2] - 2026-03-30
- Chore: uv `exclude-newer` (2 weeks) and lockfile refresh

## [0.2.1] - 2026-03-26
- Fix `zitadel.env.example` variable names (`ZITADEL_BASE_URL`, `ZITADEL_CLIENT_ID`, `ZITADEL_CLIENT_SECRET`)
- Fix README auth flow diagrams to correctly show token swap pattern

## [0.2.0] - 2026-03-24
- Add `UniqueContextProvider`: per-request auth from FastMCP token (`_meta` > JWT claims > Zitadel userinfo)
- Add `create_unique_mcp_server()` factory returning `UniqueMCPServerBundle` (FastMCP + Zitadel OAuth + context provider)
- Add `BaseProvider` protocol for registering tools and routes with a FastMCP server
- Fix `userinfo_endpoint` used as property instead of method call in `mcp_search`

## [0.1.4] - 2026-02-11
- Add docs
- Use properties in oauth and oidc proxies

## [0.1.3] - 2026-01-20
- Add oidc proxy
- Add persistance options for oidc and oauth proxies

## [0.1.2] - 2026-01-16
- Add local CI testing commands via poethepoet (poe lint, poe test, poe ci-typecheck, etc.)

## [0.1.1] - 2025-12-17
- Add server settings

## [0.1.0] - 2025-12-5
- Setup for mcp utils
