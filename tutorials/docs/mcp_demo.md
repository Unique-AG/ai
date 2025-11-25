## 📌 Overview
This tutorial demonstrates building a simple HTTP-streamable MCP server with FastMCP. It includes:
- A basic `addition` tool that adds two numbers
- An `identify` tool that retrieves the current user's profile
- Custom HTTP routes for health checks and static assets

> **Note**: For fundamental concepts about authentication, server setup, CORS, and deployment, see [MCP Fundamentals](mcp_fundamentals.md).

See the full example here: [https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/mcp_demo](https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/mcp_demo)



## 📌 Implementation

This section provides code snippets for the demo-specific implementation. For setup details on authentication, CORS, and server configuration, refer to [MCP Fundamentals](mcp_fundamentals.md).

### 🔧 Environment & Base URL
Load IdP endpoints, OAuth client, and the server's public base URL:

```python
from dotenv import load_dotenv
import os, sys

load_dotenv()

ZITADEL_URL = os.getenv("ZITADEL_URL", "http://localhost:10116")
UPSTREAM_CLIENT_ID = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
UPSTREAM_CLIENT_SECRET = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")

base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")
BASE_URL = sys.argv if len(sys.argv) > 1 else base_url_env
```

### 🔐 Auth: OAuth Proxy + JWT Verifier
Set up authentication (see [MCP Fundamentals](mcp_fundamentals.md) for details):

```python
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy

token_verifier = JWTVerifier(
    jwks_uri=f"{ZITADEL_URL}/oauth/v2/keys",
    issuer=f"{ZITADEL_URL}",
    algorithm=None,
    audience=None,
)

auth = OAuthProxy(
    upstream_authorization_endpoint=f"{ZITADEL_URL}/oauth/v2/authorize",
    upstream_token_endpoint=f"{ZITADEL_URL}/oauth/v2/token",
    upstream_client_id=UPSTREAM_CLIENT_ID,
    upstream_client_secret=UPSTREAM_CLIENT_SECRET,
    upstream_revocation_endpoint=f"{ZITADEL_URL}/oauth/v2/revoke",
    token_verifier=token_verifier,
    base_url=BASE_URL,
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
)
```

### 🌐 CORS Middleware
Enable CORS for browser-based clients:

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

### ⚙️ FastMCP Server Init
Create the MCP server:

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
Example tool showing name/title/description, metadata for Unique AI, and typed parameters for better schema:

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
Demonstrates reading the bearer token and calling IdP's "me" endpoint to identify the user:

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
Combine classic routes (health, favicon) with MCP tools—like you would with FastAPI/Starlette:

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

## 🚀 Running the Server
Run the server with HTTP transport and CORS middleware:

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

For deployment considerations and configuration details, see [MCP Fundamentals](mcp_fundamentals.md).