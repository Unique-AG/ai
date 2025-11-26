## 📌 Overview
This tutorial demonstrates building an HTTP-streamable MCP server with FastMCP, **with a focus on demonstrating how to authenticate with Google OAuth**. It includes:
- **Google OAuth authentication** using the GoogleProvider
- A `get_user_info` tool that retrieves the authenticated Google user's information
- Automatic token validation and user data extraction from Google tokens
- A complete uv project structure with `pyproject.toml` for dependency management

> **Note**: For fundamental concepts about authentication, server setup, CORS, and deployment, see [MCP Fundamentals](mcp_fundamentals.md).

See the full example here: [https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/google_auth](https://github.com/Unique-AG/ai/tree/main/tutorials/mcp/google_auth)

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   cd tutorials/mcp/google_auth
   uv sync
   ```

2. **Configure environment variables:**
   Create a `.env` file with your Google OAuth credentials:
   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

3. **Run the server:**
   ```bash
   uv run python -m google_auth.google_auth_server
   ```

## 📌 Implementation

This section provides code snippets for the Google authentication-specific implementation. The project follows a standard uv project structure with the main server code in `src/google_auth/google_auth_server.py`. For setup details on authentication, CORS, and server configuration, refer to [MCP Fundamentals](mcp_fundamentals.md).

### 📁 Project Structure
The project is structured as a uv-managed Python package:
```
google_auth/
├── pyproject.toml          # Project configuration and dependencies
├── README.md               # Project documentation
├── .python-version         # Python version specification (3.12)
└── src/
    └── google_auth/
        ├── __init__.py     # Package initialization
        └── google_auth_server.py  # Main server implementation
```

### 🔧 Environment Configuration
Load Google OAuth credentials from environment variables:

```python
import os
from dotenv import load_dotenv

BASE_PORT = 8003
BASE_HOST = "localhost"
BASE_URL = f"http://{BASE_HOST}:{BASE_PORT}"

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
```

### 🔐 Auth: Google Provider
This example demonstrates **Google OAuth authentication** using the GoogleProvider. The GoogleProvider handles Google's token format and validation automatically:

```python
from fastmcp.server.auth.providers.google import GoogleProvider

# The GoogleProvider handles Google's token format and validation
auth_provider = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,  # Your Google OAuth Client ID
    client_secret=GOOGLE_CLIENT_SECRET,  # Your Google OAuth Client Secret
    base_url=BASE_URL,  # Must match your OAuth configuration
    required_scopes=[  # Request user information
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    # redirect_path="/auth/callback"  # Default value, customize if needed
)
```

### ⚙️ FastMCP Server Init
Create the MCP server with Google authentication:

```python
from fastmcp import FastMCP

mcp = FastMCP(name="Google Secured App", auth=auth_provider)
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

## 👤 Get User Info Tool
Demonstrates accessing authenticated Google user information from token claims:

```python
@mcp.tool(
    name="get_user_info",  # Custom tool name for the LLM
    title="Get User Info",  # Custom display name
    description="Returns information about the authenticated Google user.",  # Custom description
    meta={
        "unique.app/icon": "database-backup",
        "unique.app/system-prompt": "Returns information about the authenticated Google user.",
    },
)
async def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()

    if token is None:
        return {
            "error": "No token found",
        }

    # The GoogleProvider stores user data in token claims
    return {
        "google_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
        "locale": token.claims.get("locale"),
    }
```

**Key Points:**
- The `get_access_token()` dependency provides access to the authenticated token
- The GoogleProvider automatically extracts and stores user information in `token.claims`
- User data includes Google ID, email, name, picture, and locale

## 🚀 Running the Server

The server includes a `main()` function that can be called programmatically or run directly:

```python
def main():
    """Main entry point for running the server."""
    mcp.run(
        transport="http",
        host=BASE_HOST,
        port=BASE_PORT,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
```

**Running the server:**

1. **Using uv run (recommended):**
   ```bash
   uv run python -m google_auth.google_auth_server
   ```

2. **Using the installed script (after `uv sync`):**
   ```bash
   google-auth-mcp
   ```

3. **Direct Python execution:**
   ```bash
   python -m google_auth.google_auth_server
   ```

## 🔑 Google OAuth Setup

To use this example, you need to:

1. **Create a Google OAuth Client:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google+ API
   - Go to "Credentials" and create an OAuth 2.0 Client ID
   - Set authorized redirect URIs to match your `BASE_URL` (e.g., `http://localhost:8003/auth/callback`)

2. **Configure Environment Variables:**
   Create a `.env` file in the project root with:
   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

3. **Required Scopes:**
   - `openid`: Required for OpenID Connect authentication
   - `https://www.googleapis.com/auth/userinfo.email`: Required to access user email information

## 📦 Dependencies

The project uses the following dependencies (managed via `pyproject.toml`):
- `fastapi>=0.120.2` - Web framework
- `fastmcp>=2.13.0.2` - FastMCP server framework
- `pydantic>=2.12.3` - Data validation
- `python-dotenv>=1.0.0` - Environment variable management

Install all dependencies with:
```bash
uv sync
```

For deployment considerations and configuration details, see [MCP Fundamentals](mcp_fundamentals.md).

