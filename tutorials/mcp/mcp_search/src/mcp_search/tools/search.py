from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from unique_mcp import get_unique_service_factory
from unique_toolkit.content.schemas import ContentSearchType
from unique_toolkit.services.factory import UniqueServiceFactory


@tool(
    name="search",
    description="This tool does search in the knowledge base for the given search string and search type and returns the search results",
    meta={
        "unique.app/icon": "search",
        "unique.app/system-prompt": "Choose this tool if you need to search in the knowledge base",
    },
)
async def search(
    search_string: Annotated[
        str,
        Field(
            description="The search string that will be used to do the search in the knowledge base"
        ),
    ],
    search_type: Annotated[
        ContentSearchType,
        Field(
            default=ContentSearchType.VECTOR,
            description="The search type that will be used to do the search in the knowledge base",
        ),
    ] = ContentSearchType.VECTOR,
    limit: Annotated[
        int,
        Field(
            description="The limit for the number of search results",
            default=10,
        ),
    ] = 10,
    service_factory: UniqueServiceFactory = Depends(get_unique_service_factory),
) -> CallToolResult:
    """Search in the knowledge base"""

    content_chunks = service_factory.knowledge_base_service().search_content_chunks(
        search_string=search_string,
        search_type=search_type,
        limit=limit,
        scope_ids=None,  # type: ignore
    )

    return CallToolResult(
        content=[
            TextContent(type="text", text=chunk.text, _meta=chunk.model_dump())
            for chunk in content_chunks
        ],
    )


@tool
def show_env() -> dict:
    import os

    return {
        "UNIQUE_AUTH_USER_ID": os.getenv("UNIQUE_AUTH_USER_ID"),
        "UNIQUE_AUTH_COMPANY_ID": os.getenv("UNIQUE_AUTH_COMPANY_ID"),
    }
