import sys
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from starlette.requests import Request
from fastmcp.server.dependencies import get_access_token
from fastapi.responses import FileResponse
import requests
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventPayload,
    ChatEventUserMessage,
    ChatEventAssistantMessage,
)


from unique_toolkit.agentic.tools.factory import ToolFactory

from unique_toolkit.language_model.schemas import LanguageModelFunction
import unique_sdk
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from typing import Annotated
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv
from db_tool_pm.service import PMPositionsTool
import os


# Load environment variables from .env file
load_dotenv()

user_id = os.getenv("USER_ID", "default_user_id")
company_id = os.getenv("COMPANY_ID", "default_company_id")
ZITADEL_URL = os.getenv("ZITADEL_URL", "http://localhost:10116")
unique_sdk.api_base = os.getenv(
    "UNIQUE_SDK_API_BASE", "https://gateway.qa.unique.app/public/chat-gen2"
)
unique_sdk.api_key = os.getenv("UNIQUE_SDK_API_KEY", "default_api_key")
unique_sdk.app_id = os.getenv("UNIQUE_SDK_APP_ID", "default_app_id")

upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")

base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")


base_url_arg = sys.argv[1] if len(sys.argv) > 1 else base_url_env

print("base_url_arg", base_url_arg)

print("position", PMPositionsTool.name)

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


chatEvent = ChatEvent(
    event="user_message_created",
    id="event_id",
    user_id=user_id,
    company_id=company_id,
    payload=ChatEventPayload(
        assistant_id="assistant_xkpx89hstyjqrudl4dftiryc",
        chat_id="chat_id",
        user_message=ChatEventUserMessage(
            id="id",
            text="user_message_text",
            created_at="created_at",
            language="en",
            original_text="original_text",
        ),
        assistant_message=ChatEventAssistantMessage(id="id", created_at="created_at"),
        name="name",
        description="description",
        configuration={},
    ),
)  # type: ignore

tool = ToolFactory.build_tool("PM_Positions", {}, chatEvent)

mcp = FastMCP("Demo 🚀", auth=auth, debug=True, log_level="debug")


def get_user():
    token = get_access_token()
    if token is not None:
        headers = {
            "Authorization": f"Bearer {token.token}",
        }

        response = requests.get(f"{ZITADEL_URL}/oidc/v1/userinfo", headers=headers)
    return response.json()


@mcp.tool(
    name=tool.name,  # Custom tool name for the LLM
    title=tool.display_name(),  # Custom display name
    description=tool.tool_description().description,  # Custom description
    meta={
        "unique.app/icon": "database-backup",
        "unique.app/system-prompt": tool.tool_description_for_system_prompt()
        + "\n\n"
        + tool.tool_format_information_for_system_prompt(),
    },
)
async def search_in_database(
    query: Annotated[
        str,
        Field(
            description="Search string to find relevant information on stocks and instruments it can include exposure. This will be converted to sql and run against the database."
        ),
    ],
) -> str:
    """Search string to find relevant information on stocks and instruments. This will be converted to sql and run against the database."""
    user = get_user()
    print("user", user)
    email = user.get("email", "alice@alphabet.example")

    tool_call: LanguageModelFunction = LanguageModelFunction(
        id="unique_id",  # type: ignore
        name=tool.name,
        arguments={"search_string": query, "email": email},  # type: ignore
    )

    result = await tool.run(
        tool_call,
    )  # type: ignore
    return result.content


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running"})


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    FAVICON_PATH = Path(__file__).parent / "favicon.ico"
    return FileResponse(FAVICON_PATH)


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8002,
        log_level="debug",
        middleware=custom_middleware,
    )
