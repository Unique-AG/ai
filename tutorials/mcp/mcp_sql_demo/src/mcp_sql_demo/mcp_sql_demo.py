from pathlib import Path
from typing import Annotated

import httpx
from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from mcp_sql_demo.db_tool_pm.service import PMPositionsTool
from unique_mcp.auth.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_mcp.provider import UniqueContextProvider
from unique_mcp.settings import ServerSettings
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.language_model.schemas import LanguageModelFunction

# Load environment variables from .env file
load_dotenv()

print("position", PMPositionsTool.name)

# Module-level tool object for decorator metadata only.
# User identity does not affect tool name/description, so a placeholder event is fine here.
_PLACEHOLDER_EVENT = ChatEvent(
    event="user_message_created",
    id="event_id",
    user_id="placeholder",
    company_id="placeholder",
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
_METADATA_TOOL = ToolFactory.build_tool("PM_Positions", {}, _PLACEHOLDER_EVENT)


def main() -> None:
    _unique_settings = UniqueSettings.from_env_auto_with_sdk_init()

    server_settings = ServerSettings()  # type: ignore
    zitadel_settings = ZitadelOAuthProxySettings()

    context_provider = UniqueContextProvider(
        settings=_unique_settings,
        zitadel_settings=zitadel_settings,
    )

    zitadel_oauth_proxy = create_zitadel_oauth_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oauth_proxy_settings=zitadel_settings,
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

    mcp = FastMCP("Demo 🚀", debug=True, log_level="debug")

    @mcp.tool(
        name=_METADATA_TOOL.name,
        title=_METADATA_TOOL.display_name(),
        description=_METADATA_TOOL.tool_description().description,
        meta={
            "unique.app/icon": "database-backup",
            "unique.app/system-prompt": _METADATA_TOOL.tool_description_for_system_prompt()
            + "\n\n"
            + _METADATA_TOOL.tool_format_information_for_system_prompt(),
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
        context = await context_provider.get_context()
        user_id = context.auth.get_confidential_user_id()
        company_id = context.auth.get_confidential_company_id()

        # Email is not provided by UniqueContextProvider — fetch from Zitadel userinfo directly.
        token = get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                zitadel_settings.userinfo_endpoint,
                headers={"Authorization": f"Bearer {token.token}"},
            )
        response.raise_for_status()
        email = response.json().get("email", "alice@alphabet.example")

        per_request_event = ChatEvent(
            event="user_message_created",
            id="event_id",
            user_id=user_id,
            company_id=company_id,
            payload=_PLACEHOLDER_EVENT.payload,
        )  # type: ignore
        tool = ToolFactory.build_tool("PM_Positions", {}, per_request_event)

        tool_call = LanguageModelFunction(
            id="unique_id",  # type: ignore
            name=tool.name,
            arguments={"search_string": query, "email": email},  # type: ignore
        )

        result = await tool.run(tool_call)
        return result.content

    @mcp.custom_route("/", methods=["GET"])
    async def get_status(request: Request):
        return JSONResponse({"server": "running"})

    @mcp.custom_route("/favicon.ico", methods=["GET"])
    async def favicon(request: Request):
        FAVICON_PATH = Path(__file__).parent / "favicon.ico"
        return FileResponse(FAVICON_PATH)

    mcp.auth = zitadel_oauth_proxy

    mcp.run(
        transport=server_settings.transport_scheme,
        host=server_settings.local_base_url.host,
        port=server_settings.local_base_url.port,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
