# MCP SQL Demo

A demonstration of an MCP (Model Context Protocol) server that enables natural language queries against a PostgreSQL database. This demo showcases a Portfolio Manager (PM) positions tool that allows users to query investment portfolio data using plain English.

## Overview

This MCP server exposes a tool called `PM_Positions` that:

1. Accepts natural language queries about portfolio positions
2. Uses an LLM (GPT-4o) to convert the query into a valid SQL WHERE clause
3. Executes the query against a PostgreSQL database
4. Returns the results filtered by the authenticated user's email

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │────▶│   PostgreSQL    │
│  (Unique AI)    │     │   (FastMCP)     │     │   Database      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    Zitadel      │
                        │  (OAuth2/OIDC)  │
                        └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Unique AI     │
                        │   Gateway       │
                        │  (LLM Access)   │
                        └─────────────────┘
```

## Database

### PostgreSQL 16

The demo uses **PostgreSQL 16** running in a Docker container. The database stores portfolio manager position data in a table called `pm_positions`.

**Connection Details (Default):**
- Host: `localhost`
- Port: `10100`
- Database: `testdb`
- User: `postgres`
- Password: `postgres`

### Table Schema: `pm_positions`

| Column        | Type          | Description                                                                 |
|---------------|---------------|-----------------------------------------------------------------------------|
| `row_num`     | INT           | Primary key                                                                 |
| `sleeve`      | TEXT          | Internal strategy bucket (e.g., Rates, Equity L/S) for risk budgeting      |
| `ticker`      | VARCHAR(10)   | Tradable symbol (e.g., MSFT, IEF)                                           |
| `instrument`  | TEXT          | Type of security (e.g., equity, ETF, swap)                                  |
| `direction`   | VARCHAR(5)    | Long (price up benefits) or Short (price down benefits)                     |
| `target_weight`| NUMERIC(8,5) | Intended portfolio allocation (Target MV / Portfolio NAV)                   |
| `position_mm` | INT           | Current position size in millions                                           |
| `email`       | TEXT          | User email for row-level access control                                     |

### Sample Data

The demo includes sample portfolio positions for various asset classes:

- **Equity Long**: MSFT, JNJ, UNH, JPM, CVX
- **Equity Beta**: SPY (S&P 500 ETF)
- **Equity Short**: QQQ, RSP
- **Rates**: IEF (7-10Y U.S. Treasuries)
- **Credit**: LQD (Investment Grade Credit)
- **Alternatives**: GLD (Gold), DBC (Broad Commodities)

## Authentication

### Zitadel OAuth2/OIDC

The MCP server uses **Zitadel** as the OAuth2/OIDC identity provider for authentication. This provides:

1. **JWT Verification**: Tokens are verified using Zitadel's JWKS endpoint
2. **OAuth2 Proxy**: The server acts as an OAuth2 proxy for seamless authentication flow
3. **User Identity**: The authenticated user's email is extracted from the OIDC userinfo endpoint

### Authentication Flow

1. Client initiates OAuth2 authorization with Zitadel
2. User authenticates and grants permissions
3. MCP server receives and verifies the JWT token
4. User email is extracted from `{ZITADEL_URL}/oidc/v1/userinfo`
5. All database queries are filtered by the user's email (row-level security)

### Required Scopes

- `mcp:tools` - Access to MCP tools
- `mcp:prompts` - Access to MCP prompts
- `mcp:resources` - Access to MCP resources
- `mcp:resource-templates` - Access to resource templates
- `email` - Access to user's email
- `openid` - OpenID Connect scope
- `profile` - Access to user profile

## Unique AI Integration

### Authentication with Unique AI

The server authenticates with the Unique AI gateway to access language models. This requires:

| Environment Variable    | Description                                          |
|------------------------|------------------------------------------------------|
| `UNIQUE_SDK_API_BASE`  | Unique AI gateway URL (default: QA environment)     |
| `UNIQUE_SDK_API_KEY`   | Your Unique AI API key                               |
| `UNIQUE_SDK_APP_ID`    | Your Unique AI application ID                        |

### LLM-Powered SQL Generation

The tool uses **Azure GPT-4o (2024-11-20)** via the Unique AI gateway to:

1. Analyze the database schema (columns, types, constraints)
2. Retrieve distinct values for categorical columns (sleeve, ticker, direction)
3. Generate a valid PostgreSQL WHERE clause from natural language
4. Ensure safe, read-only queries (no INSERT/UPDATE/DELETE)

## Setup

### 1. Start PostgreSQL

```bash
docker compose -f docker_compose.yaml up -d
```

### 2. Create the Database and Table

Connect to PostgreSQL and run the setup script:

```bash
psql -h localhost -p 10100 -U postgres -f create_table.sql
```

### 3. Configure Environment Variables

Create a `.env` file with:

```bash
# PostgreSQL
PGHOST=localhost
PGPORT=10100
PGDATABASE=testdb
PGUSER=postgres
PGPASSWORD=postgres

# Zitadel
ZITADEL_URL=https://your-zitadel-instance.com
UPSTREAM_CLIENT_ID=your-client-id
UPSTREAM_CLIENT_SECRET=your-client-secret

# Unique AI
UNIQUE_SDK_API_BASE=https://gateway.unique.app/public/chat-gen2
UNIQUE_SDK_API_KEY=your-api-key
UNIQUE_SDK_APP_ID=your-app-id

# Server
BASE_URL_ENV=https://your-public-url.ngrok-free.app
USER_ID=your-user-id
COMPANY_ID=your-company-id
```

### 4. Install Dependencies

```bash
uv sync
```

### 5. Run the Server

```bash
uv run python src/mcp_sql_demo/mcp_sql_demo.py
```

The server will start on `http://127.0.0.1:8002`.

## Usage Examples

Once connected via an MCP client, you can ask natural language questions like:

- "What are my long equity positions?"
- "Show me all positions in the Rates sleeve"
- "What stocks have a target weight above 5%?"
- "List my short positions"
- "What is my exposure to technology stocks?"

The tool will convert these queries to SQL and return formatted results.

## How the Query Flow Works

1. **User Query**: "What are my long positions with weight > 5%?"

2. **LLM Processing**: The query is sent to GPT-4o with the database schema context

3. **SQL Generation**: LLM generates: `WHERE direction = 'Long' AND target_weight > 0.05`

4. **Query Execution**: 
   ```sql
   SELECT * FROM (SELECT * FROM pm_positions WHERE email = 'user@example.com') AS tmp 
   WHERE direction = 'Long' AND target_weight > 0.05
   ```

5. **Response**: Results are returned and formatted as a markdown table

## Dependencies

- `fastmcp>=2.13.0` - FastMCP server framework
- `psycopg2>=2.9.11` - PostgreSQL adapter
- `unique-toolkit>=1.20.0` - Unique AI toolkit
- `fastapi>=0.120.2` - Web framework
- `pydantic>=2.12.3` - Data validation
