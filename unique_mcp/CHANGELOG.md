# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2026.32.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.30.0...unique-mcp-v2026.32.0) (2026-07-24)


### Features

* **unique_mcp:** async per-request identity resolver, OIDC scope advertisement ([#2123](https://github.com/Unique-AG/ai/issues/2123)) ([6434827](https://github.com/Unique-AG/ai/commit/643482760aacdffb270082b8a1d0b091985731d6))


### Miscellaneous

* arm release 2026.32.0 ([6084f04](https://github.com/Unique-AG/ai/commit/6084f0413c8611f1493a00288e4b69797198c3cd))

## [2026.30.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.28.0...unique-mcp-v2026.30.0) (2026-07-17)


### Bug Fixes

* **chat:** resolve namespace-package KeyError for unique_toolkit.chat.deprecated ([#1862](https://github.com/Unique-AG/ai/issues/1862)) ([262723f](https://github.com/Unique-AG/ai/commit/262723fa54e3ef9148f4d7067b6ff1000b8a59ce))


### Miscellaneous

* arm release 2026.30.0 ([94e018f](https://github.com/Unique-AG/ai/commit/94e018fa010fb5a0ffd8f449cf078c604b7c12ee))

## [2026.28.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.26.0...unique-mcp-v2026.28.0) (2026-07-03)


### Miscellaneous

* arm release 2026.28.0 ([e890f5e](https://github.com/Unique-AG/ai/commit/e890f5ecc6217d885dbdb4a3d6f093237320e1bd))

## [2026.26.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.24.0...unique-mcp-v2026.26.0) (2026-06-22)


### Miscellaneous

* arm release 2026.26.0 ([d3c79b3](https://github.com/Unique-AG/ai/commit/d3c79b385f2714ab9c6237a545da21dea0cfb34a))

## [2026.24.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.22.0...unique-mcp-v2026.24.0) (2026-06-04)


### Miscellaneous

* arm release 2026.24.0 ([2b3ff5d](https://github.com/Unique-AG/ai/commit/2b3ff5d2e13c4c98cd0012f0306db10f980aa886))

## [2026.22.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.20.0...unique-mcp-v2026.22.0) (2026-05-21)


### Features

* **mcp-search:** rewrite tutorial using InternalSearchService + search_mode switcher ([#1623](https://github.com/Unique-AG/ai/issues/1623)) ([d60b1b8](https://github.com/Unique-AG/ai/commit/d60b1b8c933f0911ceaaeb76247711c9e4ee41a6))
* **unique-mcp:** add UniqueAIToolMeta and ContextRequirements meta parts ([#1690](https://github.com/Unique-AG/ai/issues/1690)) ([6958951](https://github.com/Unique-AG/ai/commit/6958951ca4298c46a875a831625f3f8cc3b29902))


### Miscellaneous

* arm release 2026.22.0 ([3fe07bd](https://github.com/Unique-AG/ai/commit/3fe07bdafc85a45f8275a18b72f6ebe766c15464))

## [2026.20.0](https://github.com/Unique-AG/ai/compare/unique-mcp-v2026.18.0...unique-mcp-v2026.20.0) (2026-05-08)


### Miscellaneous

* arm release 2026.20.0 ([#1506](https://github.com/Unique-AG/ai/issues/1506)) ([0820dc9](https://github.com/Unique-AG/ai/commit/0820dc9a1c661470c2ef44ed2eed6830b508ca8d))

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
