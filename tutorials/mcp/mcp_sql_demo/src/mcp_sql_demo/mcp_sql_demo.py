from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from fastmcp.dependencies import Depends
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from mcp_sql_demo.db_tool_pm.service import PMPositionsTool
from unique_mcp.server import create_unique_mcp_server
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
)
from unique_toolkit.app.unique_settings import UniqueContext
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
    bundle = create_unique_mcp_server("Demo 🚀")
    context_provider = bundle.context_provider

    custom_middleware = [
        Middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    @bundle.mcp.tool(
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
        context: UniqueContext = Depends(context_provider.get_context),
        userinfo: dict = Depends(context_provider.get_userinfo),
    ) -> str:
        """Search string to find relevant information on stocks and instruments. This will be converted to sql and run against the database."""
        user_id = context.auth.get_confidential_user_id()
        company_id = context.auth.get_confidential_company_id()

        email = userinfo.get("email", "alice@alphabet.example")

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

    @bundle.mcp.custom_route("/", methods=["GET"])
    async def get_status(request: Request):
        return JSONResponse({"server": "running"})

    @bundle.mcp.custom_route("/favicon.ico", methods=["GET"])
    async def favicon(request: Request):
        FAVICON_PATH = Path(__file__).parent / "favicon.ico"
        return FileResponse(FAVICON_PATH)

    bundle.mcp.run(
        transport=bundle.server_settings.transport_scheme,
        host=bundle.server_settings.local_base_url.host,
        port=bundle.server_settings.local_base_url.port,
        debug=True,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
