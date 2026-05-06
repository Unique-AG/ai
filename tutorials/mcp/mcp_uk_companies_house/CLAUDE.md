# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

xMCP server for the Companies House API. Built with the xmcp framework (v0.6.4), Zod (v4) for schema validation, and TypeScript in strict mode. Requires Node.js >= 20. Strictly follows the [MCP specification (2025-03-26)](https://modelcontextprotocol.io/specification/2025-03-26).

## Commands

- `npm run dev`: Start xmcp development server
- `npm run build`: Compile TypeScript to dist/
- `npm start`: Run production HTTP server (node dist/http.js)

## Architecture

This is a file-based xMCP server. The framework auto-discovers components from directories configured in `xmcp.config.ts`:

- `src/tools/` — MCP tools (callable functions exposed to clients)
- `src/prompts/` — MCP prompt templates
- `src/resources/` — MCP resources (static and dynamic data endpoints)

**Routing conventions** (xmcp file-based discovery):
- `(folder)` parenthesized directories create path segments
- `[param]` bracketed directories create dynamic URI parameters

**Each component exports three things:**
1. `schema` — Zod schema defining input parameters
2. `metadata` — MCP metadata (name, description, annotations)
3. `default` function — The handler implementation

## Testing

All new tools, prompts, and resources must have comprehensive tests. Cover the happy path, edge cases, and error handling for each component.

## Documentation

Keep documentation up to date as you work. When adding or changing tools, prompts, or resources, update the relevant docs in the same change. Write documentation incrementally — start with what you know and refine it as the implementation evolves.

## Tools

6 MCP tools that map to 18 Companies House API endpoints, grouped by intent:

| Tool | API endpoints | Key params |
|------|--------------|------------|
| `search-companies` | `/search/companies`, `/advanced-search/companies` | `query`, optional filters for advanced search |
| `get-company` | `/company/{id}`, `/company/{id}/registered-office-address`, `/company/{id}/insolvency`, `/company/{id}/charges` | `companyNumber`, optional `include` to fetch sub-resources |
| `get-company-officers` | `/company/{id}/officers`, `/company/{id}/appointments/{appt_id}` | `companyNumber`, optional `appointmentId` |
| `search-officers` | `/search/officers`, `/officers/{id}/appointments` | `query` or `officerId` |
| `get-company-psc` | `/company/{id}/persons-with-significant-control`, `.../individual/{psc_id}`, `.../individual-beneficial-owner/{psc_id}`, `.../corporate-entity/{psc_id}`, `.../legal-person/{psc_id}`, `.../statements` | `companyNumber`, optional `pscId` + `type` |
| `get-filing-history` | `/company/{id}/filing-history`, `/company/{id}/filing-history/{txn_id}` | `companyNumber`, optional `transactionId` |

All tools are read-only (`readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`).

## Authentication

**MCP server**: OAuth 2.0 `client_credentials` flow. The middleware at `src/middleware.ts` (auto-discovered by xmcp) exports a `{ router, middleware }` pair. The router serves OAuth discovery endpoints (`/.well-known/oauth-protected-resource`, `/.well-known/oauth-authorization-server`) and a `POST /token` endpoint. Clients authenticate with `client_secret_basic` (HTTP Basic Auth on the token endpoint) using `MCP_CLIENT_ID` and `MCP_CLIENT_SECRET` env vars, receive a Bearer token, and use it for MCP requests. When these env vars are not set, auth is skipped (open access for local dev). Tokens are stored in-memory with 3-day expiry (`TOKEN_LIFETIME = 259200` seconds).

**Companies House API**: HTTP Basic Auth with the API key as username and empty password (`Authorization: Basic <base64(key:)>`). The key is stored in `COMPANIES_HOUSE_API_KEY` env var — never hardcode it. Public data only — all requests are read-only GET requests.

**Sandbox vs Live**: Set `COMPANIES_HOUSE_SANDBOX=true` to use the sandbox API (`https://api-sandbox.company-information.service.gov.uk`). When unset or any other value, the live API (`https://api.company-information.service.gov.uk`) is used. The base URL is resolved at request time via `getBaseUrl()` in `src/lib/companies-house-api.ts`.

## Code Style

- TypeScript strict mode, no `any` types
- Use named exports for schema and metadata; default export for handler
- NEVER commit .env files
