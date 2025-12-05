import json
from pathlib import Path
from typing import Annotated

import requests
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from mcp_search.zitadel_oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_toolkit import KnowledgeBaseService
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentSearchType

# Ensure the static directory exists and contains favicon.ico
FAVICON_PATH = Path(__file__).parent / "favicon.ico"


unique_settings = UniqueSettings.from_env_auto_with_sdk_init()
print(unique_settings._env_file)


zitadel_oauth_proxy_settings = ZitadelOAuthProxySettings()
# Pass the MCP server's base URL to the OAuth proxy for discovery endpoints
mcp_server_base_url = "http://localhost:8003"
auth = create_zitadel_oauth_proxy(mcp_server_base_url=mcp_server_base_url)


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
# mcp = FastMCP(name="Demo 🚀", auth=auth, debug=True, log_level="debug")
mcp = FastMCP(name="Demo 🚀", auth=auth, debug=True, log_level="debug")


class User(BaseModel):
    email: str
    user_id: str
    name: str
    company_id: str


def get_user() -> User:
    zitadel_user_info = None
    token = get_access_token()

    if token is None:
        raise Exception("Unable to retrieve access token for user retrieval")

    headers = {
        "Authorization": f"Bearer {token.token}",
    }
    response = requests.get(
        zitadel_oauth_proxy_settings.userinfo_endpoint(), headers=headers
    )
    zitadel_user_info = response.json()

    user = User(
        email=zitadel_user_info.get("email"),
        user_id=zitadel_user_info.get("sub"),
        name=zitadel_user_info.get("name"),
        company_id=zitadel_user_info.get("urn:zitadel:iam:user:resourceowner:id"),
    )

    return user


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
def identify(user_prompt: str) -> CallToolResult:
    """Identify the user"""
    user = get_user()
    return CallToolResult(
        content=[
            TextContent(
                type="text", text=json.dumps(user.model_dump()), _meta=user.model_dump()
            )
        ],
    )


@mcp.tool()
def search(
    search_string: str,
    search_type: ContentSearchType = ContentSearchType.COMBINED,
    limit: int = 10,
) -> CallToolResult:
    """Search in the knowledge base"""
    user = get_user()

    knowledge_base_service = KnowledgeBaseService(
        user_id=user.user_id,
        company_id=user.company_id,
    )

    content_chunks = knowledge_base_service.search_content_chunks(
        search_string=search_string,
        search_type=search_type,
        limit=limit,
        scope_ids=None,
    )

    return CallToolResult(
        content=[
            TextContent(type="text", text=chunk.text, _meta=chunk.model_dump())
            for chunk in content_chunks
        ],
    )


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
