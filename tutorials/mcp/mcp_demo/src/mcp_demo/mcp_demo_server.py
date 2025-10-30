import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
import requests
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from starlette.requests import Request
import json
import sys
from typing import Annotated
from pydantic import Field


from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path


# Ensure the static directory exists and contains favicon.ico
FAVICON_PATH = Path(__file__).parent / "favicon.ico"


# Load environment variables from .env file
load_dotenv()

user_id = os.getenv("USER_ID", "default_user_id")
company_id = os.getenv("COMPANY_ID", "default_company_id")
ZITADEL_URL = os.getenv("ZITADEL_URL", "http://localhost:10116")


upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")

base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")


base_url_arg = sys.argv[1] if len(sys.argv) > 1 else base_url_env

print("base_url_arg", base_url_arg)


token_verifier = JWTVerifier(
    jwks_uri=f"{ZITADEL_URL}/oauth/v2/keys",
    issuer=f"{ZITADEL_URL}",
    algorithm=None,
    audience=None,
    # required_scopes=[],
)

auth = OAuthProxy(
    upstream_authorization_endpoint=f"{ZITADEL_URL}/oauth/v2/authorize",
    upstream_token_endpoint=f"{ZITADEL_URL}/oauth/v2/token",
    upstream_client_id=upstream_client_id,
    upstream_client_secret=upstream_client_secret,
    upstream_revocation_endpoint=f"{ZITADEL_URL}/oauth/v2/revoke",
    token_verifier=token_verifier,
    base_url=base_url_arg,
    redirect_path=None,
    issuer_url=None,
    service_documentation_url=None,
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


custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

# mcp = FastMCP.from_fastapi(app=app,auth=auth,debug=True,log_level="debug")
mcp = FastMCP("Demo 🚀", auth=auth, debug=True, log_level="debug")


def get_user():
    token = get_access_token()
    if token is not None:
        print("token", token)
        headers = {
            "Authorization": f"Bearer {token.token}",
        }

        response = requests.get(f"{ZITADEL_URL}/auth/v1/users/me", headers=headers)
    return response.json()


@mcp.tool(
    name="addition",  # Custom tool name for the LLM
    title="addition",  # Custom display name
    description="This tool does add two numbers",  # Custom description
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


@mcp.tool
def identify(user_prompt: str) -> str:
    """Identify the user"""
    user = get_user()
    data = json.dumps(user)
    print(data)
    return data


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running"})


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    return FileResponse(FAVICON_PATH)


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8003,
        log_level="debug",
        middleware=custom_middleware,
    )
