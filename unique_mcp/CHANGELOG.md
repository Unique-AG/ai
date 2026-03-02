# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.5] - 2026-03-02
- Security: upgrade fastmcp 2.13.3 → 3.0.2 (direct dep)
- Security: upgrade mcp 1.22.0 → 1.26.0 (indirect dep via fastmcp)
- Security: upgrade authlib 1.6.5 → 1.6.9 (indirect dep)
- Security: upgrade urllib3 2.5.0 → 2.6.3 (indirect dep)

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

