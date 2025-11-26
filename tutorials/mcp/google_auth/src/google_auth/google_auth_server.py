import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

BASE_PORT = 8003
BASE_HOST = "localhost"

BASE_URL = f"http://{BASE_HOST}:{BASE_PORT}"

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# The GoogleProvider handles Google's token format and validation
auth_provider = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,  # Your Google OAuth Client ID
    client_secret=GOOGLE_CLIENT_SECRET,  # Your Google OAuth Client Secret
    base_url=BASE_URL,  # Must match your OAuth configuration
    required_scopes=[  # Request user information
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    # redirect_path="/auth/callback"                  # Default value, customize if needed
)

mcp = FastMCP(name="Google Secured App", auth=auth_provider)


# Authentication is automatically configured from environment
custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]


# Add a protected tool to test authentication
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
