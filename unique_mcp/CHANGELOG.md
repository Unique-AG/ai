# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

