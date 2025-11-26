## 📌 Overview
This tutorial demonstrates building an HTTP-streamable MCP server that integrates with the Unique SDK to provide search functionality, **with a focus on demonstrating how unique credentials (`user_id` and `company_id`) can be passed and used by underlying tools for authenticated operations via the Unique SDK**. It includes:
- **Extracting unique credentials** (`user_id` and `company_id`) from authenticated tokens
- A `search` tool that queries a knowledge base using the Unique SDK with user-specific credentials
- An `identify` tool that retrieves the current user's profile (including `user_id` and `company_id`)
- Integration with Unique SDK for authenticated search operations using extracted credentials

> **Note**: For fundamental concepts about authentication, server setup, CORS, and deployment, see [MCP Fundamentals](mcp_fundamentals.md).

See the full example here: [https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/mcp_search](https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/mcp_search)

## 🔍 Search Tool
The main feature of this server is the `search` tool that demonstrates **how unique credentials are passed to the Unique SDK for authenticated operations**:
- Extracts user identity (`user_id`, `company_id`) from the authenticated token
- **Passes these credentials to the Unique SDK** for authenticated search operations
- Uses the Unique SDK to perform searches in the knowledge base with user-specific context
- Returns search results as JSON

### Unique SDK Configuration
The server requires these additional environment variables:
- `API_BASE`: Base URL for the Unique API (e.g., `https://gateway.qa.unique.app/public/chat-gen2`)
- `API_KEY`: API key for authentication
- `APP_ID`: Application ID

The SDK is configured before server initialization:
```python
unique_sdk.api_base = os.getenv("API_BASE", "https://gateway.qa.unique.app/public/chat-gen2")
unique_sdk.api_key = os.getenv("API_KEY", "default_api_key")
unique_sdk.app_id = os.getenv("APP_ID", "default_app_id")
```



## 📌 Implementation

This section provides code snippets for the search-specific implementation. For setup details on authentication, CORS, and server configuration, refer to [MCP Fundamentals](mcp_fundamentals.md).

### 🔧 Environment & Base URL
Load IdP endpoints, OAuth client, Unique SDK configuration, and the server's public base URL:

```python
from dotenv import load_dotenv
import os, sys
import unique_sdk

load_dotenv()

ZITADEL_URL = os.getenv("ZITADEL_URL", "http://localhost:10116")
UPSTREAM_CLIENT_ID = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
UPSTREAM_CLIENT_SECRET = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")
base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")

# Unique SDK configuration
unique_sdk.api_base = os.getenv("API_BASE", "https://gateway.qa.unique.app/public/chat-gen2")
unique_sdk.api_key = os.getenv("API_KEY", "default_api_key")
unique_sdk.app_id = os.getenv("APP_ID", "default_app_id")

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else base_url_env
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
        "urn:zitadel:iam:user:resourceowner",
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

### 👤 User Identification Helper
This implementation demonstrates **how to extract unique credentials from authenticated tokens**. It uses Zitadel's `/oidc/v1/userinfo` endpoint and extracts `company_id` from custom claims:

```python
import json, requests
from fastmcp.server.dependencies import get_access_token

def get_user():
    token = get_access_token()
    if token is not None:
        headers = {"Authorization": f"Bearer {token.token}"}
        response = requests.get(f"{ZITADEL_URL}/oidc/v1/userinfo", headers=headers)
    zitadel_user_info = response.json()
    user = {
        "email": zitadel_user_info.get("email"),
        "user_id": zitadel_user_info.get("sub"),
        "name": zitadel_user_info.get("name"),
        "company_id": zitadel_user_info.get("urn:zitadel:iam:user:resourceowner:id"),
    }
    return user

@mcp.tool
def identify(user_prompt: str) -> str:
    """Identify the user"""
    user = get_user()
    return json.dumps(user)
```

### 🔍 Search Tool
The main search tool that demonstrates **passing unique credentials to the Unique SDK for authenticated operations**:

```python
@mcp.tool
def search(query: str) -> str:
    """Search in the knowledge base"""
    user = get_user()
    # Pass user_id and company_id to Unique SDK for authenticated operations
    result = unique_sdk.Search.create(
        user_id=user.get("user_id"),
        company_id=user.get("company_id"),
        searchString=query,
        searchType="COMBINED",
    )
    return json.dumps(result)
```

### 🧩 Standard HTTP Routes
Custom routes for health checks and static assets:

```python
from fastapi.responses import FileResponse, JSONResponse
from starlette.requests import Request
from pathlib import Path

FAVICON_PATH = Path(__file__).parent / "favicon.ico"

@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running"})

@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    return FileResponse(FAVICON_PATH)
```

### 🚀 Running the Server
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