## 📌 Overview
This document describes a HTTP-streamable MCP server built with FastMCP. It focuses on:
- Authentication and authorization via OAuth2/JWT (using Zitadel as IAM, swappable to other IdPs)
- FastMCP setup (tools, identify, metadata)
- Combining MCP with standard HTTP routes (FastAPI/Starlette-style)
- Running with CORS for browser-based inspectors (e.g., MCP Inspector) and clients (e.g., Unique AI)

Key point: this is an HTTP MCP server, not a local MCP. Web clients (like Unique AI) cannot use local MCP; HTTP + OAuth ensures user identity, avoids local installs, and enables secure access.

## 🔐 Auth & Identity
### What’s used
- JWT verification via `JWTVerifier` against IdP JWKS
- OAuth2 flow via `OAuthProxy` (auth endpoint, token endpoint, revocation)
- Scopes: `mcp:tools`, `mcp:prompts`, `mcp:resources`, `mcp:resource-templates`, `email`, `openid`, `profile`

### Why it matters
- Ensures the caller is a real, authorized user
- Enables user-level actions and auditing
- Works with web clients and MCP Inspector

### Environment variables
- `ZITADEL_URL`: Base URL of the IdP (Zitadel in the example)
- `UPSTREAM_CLIENT_ID` / `UPSTREAM_CLIENT_SECRET`: OAuth client credentials
- `BASE_URL_ENV`: Public base URL of your MCP server (reachable on the internet)
- Optional app-specific: `USER_ID`, `COMPANY_ID` (if you need them downstream)

### Token verification and user lookup
- Access token is extracted via `get_access_token()`
- The example calls `GET {ZITADEL_URL}/auth/v1/users/me` to retrieve the current user (email, profile, etc.)
- You can adapt this to your IdP’s “me” endpoint or map to your internal user store

## ⚙️ FastMCP Setup
### Server initialization
- `FastMCP(\"Demo 🚀\", auth=auth, debug=True, log_level=\"debug\")`
- Transport: `http` (streamable over HTTP)
- CORS middleware enabled for browser-based tools

### Tools
- `addition` tool:
  - Name/title/description are customizable
  - Metadata supports Unique AI-specific hints:
    - `unique.app/icon`: e.g., `calculator`
    - `unique.app/system-prompt`: guidance for the LLM to select the tool
  - Uses Pydantic/typing annotations (`Annotated[int, Field(...)]`) for precise parameter schema, improving LLM and MCP client selection

- `identify` tool:
  - Retrieves current user via the access token, returns JSON of user profile
  - Useful to confirm identity and personalize behavior

## 🧩 Standard Routes + MCP
You can define classic HTTP routes alongside MCP tools:
- Custom route `/` returns a simple JSON health/status
- Custom route `/favicon.ico` serves a static file
- These behave like FastAPI/Starlette routes and are useful for:
  - Health checks
  - Static assets (favicon)
  - Simple non-MCP endpoints

## 🌐 CORS & Inspectors
- CORS is required when testing via MCP Inspector running on localhost or using browser-based clients
- The provided `CORSMiddleware` allows all origins/headers/methods for simplicity

## 🚀 Running the Server
- Ensure your server is reachable at a public `BASE_URL` (e.g., via ngrok, a domain, or a reverse proxy)
- Pass the base URL either via env `BASE_URL_ENV` or CLI arg
- Start with:
  - Transport: `http`
  - Host/Port: e.g., `127.0.0.1:8003`
  - Middleware: include CORS middleware

## 🔄 Swapping IdP (Zitadel → Entra, etc.)
- Replace:
  - `jwks_uri`, `issuer`, and OAuth endpoints with your provider’s values
- Keep scopes aligned with your provider:
  - Always include `openid`, `email`, `profile` where available
  - MCP-specific scopes (`mcp:*`) are app-side conventions; ensure your IdP client is configured to issue them or adjust your app logic accordingly
- If your IdP supports a different flow (e.g., implicit/hybrid), consult FastMCP docs and adapt the `OAuthProxy` parameters



## 📌 Code details
Got it. I’ve added concise code snippets for the key parts:
- Environment and base URL loading
- OAuth2/JWT setup (OAuthProxy + JWTVerifier)
- MCP tool definition (addition tool)
- Identify tool using access token
- Custom routes (health, favicon)
- Server run config with HTTP transport and CORS

Each snippet is minimal and self-contained so developers can copy-paste.

## 🔧 Environment & Base URL
Why: Load IdP endpoints, OAuth client, and the server’s public base URL (needed by the OAuth proxy and web clients).

```python
from dotenv import load_dotenv
import os, sys

load_dotenv()

ZITADEL_URL = os.getenv("ZITADEL_URL", "http://localhost:10116")
UPSTREAM_CLIENT_ID = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
UPSTREAM_CLIENT_SECRET = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")

base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")
BASE_URL = sys.argv if len(sys.argv) > 1 else base_url_env

print("BASE_URL", BASE_URL)
```

## 🔐 Auth: OAuth Proxy + JWT Verifier
Why: Turn your MCP into an HTTP-authenticated server using your IdP (Zitadel here; swap endpoints for other IdPs).

```python
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy

token_verifier = JWTVerifier(
    jwks_uri=f"{ZITADEL_URL}/oauth/v2/keys",
    issuer=f"{ZITADEL_URL}",
    algorithm=None,   # Let library infer from JWKS; set explicitly if your IdP requires
    audience=None,    # Set if you validate audience
    # required_scopes=[]  # Optionally enforce here
)

auth = OAuthProxy(
    upstream_authorization_endpoint=f"{ZITADEL_URL}/oauth/v2/authorize",
    upstream_token_endpoint=f"{ZITADEL_URL}/oauth/v2/token",
    upstream_client_id=UPSTREAM_CLIENT_ID,
    upstream_client_secret=UPSTREAM_CLIENT_SECRET,
    upstream_revocation_endpoint=f"{ZITADEL_URL}/oauth/v2/revoke",
    token_verifier=token_verifier,
    base_url=BASE_URL,
    redirect_path=None,                 # Use default or specify
    issuer_url=None,                    # Optional override
    service_documentation_url=None,     # Optional
    allowed_client_redirect_uris=None,  
    valid_scopes=[
        "mcp:tools",
        "mcp:prompts",
        "mcp:resources",
        "mcp:resource-templates",
        "email",
        "openid",
        "profile",
    ],
    forward_pkce=True,
    token_endpoint_auth_method="client_secret_post",
    extra_authorize_params=None,
    extra_token_params=None,
)
```

## 🌐 CORS Middleware (for Inspectors/Browsers)
Why: Allow browser-based clients like MCP Inspector to call your server during development.

```python
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],   
        allow_methods=["*"],
        allow_headers=["*"],
    )
]
```

## ⚙️ FastMCP Server Init
Why: Create an HTTP-streamable MCP server (not local), with auth attached.

```python
from fastmcp import FastMCP

mcp = FastMCP(
    "Demo 🚀",
    auth=auth,
    debug=True,
    log_level="debug"
)
```

## 🛠️ MCP Tool: Addition
Why: Example tool showing name/title/description, metadata for Unique AI, and typed parameters for better schema.

```python
from typing import Annotated
from pydantic import Field

@mcp.tool(
    name="addition",
    title="addition",
    description="This tool adds two numbers",
    meta={
        "unique.app/icon": "calculator",
        "unique.app/system-prompt": "Choose this tool if you need to add two numbers together",
    },
)
def add(
    a: Annotated[int, Field(description="First number to add", default=0)],
    b: Annotated[int, Field(description="Second number to add", default=0)],
) -> int:
    """Add two numbers"""
    return a + b
```

## 👤 Identify Tool (User Info via Access Token)
Why: Demonstrates reading the bearer token and calling IdP’s “me” endpoint to identify the user.

```python
import json, requests
from fastmcp.server.dependencies import get_access_token

def _get_user(ZITADEL_URL: str):
    token = get_access_token()
    if not token:
        return {"error": "no access token"}
    headers = {"Authorization": f"Bearer {token.token}"}
    resp = requests.get(f"{ZITADEL_URL}/auth/v1/users/me", headers=headers)
    resp.raise_for_status()
    return resp.json()

@mcp.tool
def identify(user_prompt: str) -> str:
    """Identify the user"""
    data = _get_user(ZITADEL_URL)
    return json.dumps(data)
```

## 🧩 Standard HTTP Routes + MCP
Why: Combine classic routes (health, favicon) with MCP tools—like you would with FastAPI/Starlette.

```python
from fastapi.responses import FileResponse, JSONResponse
from starlette.requests import Request
from pathlib import Path

FAVICON_PATH = Path(__file__).parent / "favicon.ico"

@mcp.custom_route("/", methods=["GET"])
async def health(request: Request):
    return JSONResponse({"server": "running"})

@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    return FileResponse(FAVICON_PATH)
```

## 🚀 Run: HTTP Transport + CORS
Why: Expose an HTTP MCP endpoint, ready for OAuth and browser clients.

```python
if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8003,
        log_level="debug",
        middleware=custom_middleware,
    )
```

## ✅ Quick Notes
- This is an HTTP-streamable MCP server (not local) so web clients can authenticate and call tools.
- Keep `openid`, `email`, `profile` in scopes; adjust or register `mcp:*` scopes in your IdP as needed.


## Zitadel Setup

In order to have a 
