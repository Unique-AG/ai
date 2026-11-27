# MCP Companies House

An MCP server that provides read-only tools for querying the [Companies House API](https://developer-specs.company-information.service.gov.uk/) public data. Built with [xmcp](https://xmcp.dev/docs), following the [MCP specification (2025-03-26)](https://modelcontextprotocol.io/specification/2025-03-26).

MCP clients authenticate via OAuth 2.0 `client_credentials` flow. The Companies House API key is managed server-side via environment variable.

## Prerequisites

- Node.js >= 26
- A Companies House API key (get one at https://developer.company-information.service.gov.uk/)

## Setup

```bash
npm install
```

Create a `.env` file (or export the variables) with your configuration:

```bash
# Required — your Companies House API key
COMPANIES_HOUSE_API_KEY=your_api_key_here

# Optional — OAuth 2.0 client credentials for MCP server authentication
# When both are set, clients must POST to /token with client_secret_basic
# (HTTP Basic Auth on the token endpoint) to get a Bearer token for MCP requests.
# When unset, the server allows unauthenticated access (for local dev)
MCP_CLIENT_ID=your_client_id
MCP_CLIENT_SECRET=your_client_secret

# Optional — set to "true" to use the sandbox API (default: live)
# Sandbox URL: https://api-sandbox.company-information.service.gov.uk
# Live URL:    https://api.company-information.service.gov.uk
COMPANIES_HOUSE_SANDBOX=true
```

> **Tip:** Use `COMPANIES_HOUSE_SANDBOX=true` with a [sandbox API key](https://developer.company-information.service.gov.uk/) during development and testing. Remove it (or set to `false`) for production.

## Development

```bash
npm run dev
```

Starts the xmcp development server with hot reload.

## Production

```bash
npm run build
npm start          # HTTP transport (node dist/http.js)
```

## Testing

```bash
npm test
```

Runs all test files under `src/**/__tests__/**/*.test.ts` using Node's built-in test runner with `tsx`.

## Tools

All tools are read-only and hit the Companies House public API. Each tool file lives in `src/tools/` and is auto-discovered by xmcp.

### `get-company`

Get detailed information about a specific UK company by its company number. Returns the core company profile (name, status, type, SIC codes, registered address, etc.). Optionally include sub-resources:

- `registered-office-address` — full address details
- `insolvency` — insolvency case details
- `charges` — company charges/mortgages

### `get-company-officers`

Get officer information for a company. Two modes:

1. **List** — provide `companyNumber` with optional pagination, filtering by `registerType`, and `orderBy`.
2. **Single appointment** — provide `companyNumber` and `appointmentId`.

### `get-company-psc`

Get Persons with Significant Control (PSC) data. Three modes:

1. **List all PSCs** — provide `companyNumber` only.
2. **Single PSC** — provide `companyNumber`, `pscId`, and `type` (`individual`, `individual-beneficial-owner`, `corporate-entity`, or `legal-person`).
3. **PSC statements** — provide `companyNumber` and set `statements=true`.

### `get-filing-history`

Get filing history for a company. Two modes:

1. **List filings** — provide `companyNumber` with optional `category` filter and pagination.
2. **Single filing** — provide `companyNumber` and `transactionId`.

### `search-companies`

Search for UK companies. Two modes:

1. **Basic search** — provide `query` to search by company name.
2. **Advanced search** — omit `query` and use filters: `companyNameIncludes`, `companyNameExcludes`, `companyStatus`, `companyType`, `companySubtype`, `location`, `sicCodes`, `incorporatedFrom`/`To`, `dissolvedFrom`/`To`.

### `search-officers`

Search for officers or retrieve appointment history. Two modes:

1. **Search** — provide `query` to search officers by name.
2. **Appointments** — provide `officerId` to list all of that officer's appointments across companies.

## Project Structure

```
src/
├── middleware.ts                 # HTTP Basic Auth middleware (auto-discovered by xmcp)
├── lib/
│   ├── companies-house-api.ts   # Shared API client (auth, GET requests, error handling)
│   └── __tests__/
├── tools/                       # MCP tools — auto-discovered by xmcp
│   ├── get-company.ts
│   ├── get-company-officers.ts
│   ├── get-company-psc.ts
│   ├── get-filing-history.ts
│   ├── search-companies.ts
│   ├── search-officers.ts
│   └── __tests__/
├── prompts/                     # MCP prompt templates
└── resources/                   # MCP resources — static and dynamic data endpoints
```

Auto-discovery paths are configured in `xmcp.config.ts`.

### Adding a tool

Create a new `.ts` file in `src/tools/`:

```typescript
import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";

export const schema = {
  companyNumber: z.string().describe("The Companies House company number"),
};

export const metadata: ToolMetadata = {
  name: "my-new-tool",
  description: "Description of what this tool does",
  annotations: {
    title: "My New Tool",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function myNewTool({ companyNumber }: InferSchema<typeof schema>) {
  const result = await companiesHouseGet(`/company/${companyNumber}/some-endpoint`);
  return formatResult(result);
}
```

### Adding a resource

Create a file in `src/resources/` using folder conventions for URI routing:

- `(segment)` — parenthesized directories create path segments
- `[param]` — bracketed directories create dynamic URI parameters

Example: `src/resources/(companies)/[companyNumber]/index.ts` → `companies://{companyNumber}`

### Adding a prompt

Create a new `.ts` file in `src/prompts/` exporting `schema`, `metadata`, and a default function returning the prompt text.

## Deployment

### Docker

Build and run the container locally:

```bash
docker build -t companies-house-mcp .
docker run -p 3001:3001 \
  -e COMPANIES_HOUSE_API_KEY=your_key \
  -e MCP_CLIENT_ID=your_id \
  -e MCP_CLIENT_SECRET=your_secret \
  companies-house-mcp
```

The MCP endpoint will be available at `http://localhost:3001/mcp`.

### Azure Container Apps

The included `deploy.sh` script deploys to Azure App Service using Azure Container Registry.

Add the following to your `.env`:

```bash
AZURE_SUBSCRIPTION_ID=your_subscription_id
```

Then run:

```bash
./deploy.sh
```

This will create (or update) an ACR, build the image in Azure, provision an App Service on a B1 plan, and configure the app settings from your `.env` values.

## Learn More

- [xmcp Documentation](https://xmcp.dev/docs)
- [Companies House API Reference](https://developer-specs.company-information.service.gov.uk/)
