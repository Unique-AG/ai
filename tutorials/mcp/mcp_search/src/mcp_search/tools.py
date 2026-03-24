from typing import Annotated

from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from unique_mcp.provider import BaseProvider, UniqueContextProvider
from unique_toolkit import KnowledgeBaseService
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentSearchType


class UniqueKnowledgeBaseTools(BaseProvider):
    def __init__(self, context_provider: UniqueContextProvider) -> None:
        self._context_provider = context_provider

    def register(self, *, mcp: FastMCP) -> None:
        @mcp.tool(
            name="search",
            description="This tool does search in the knowledge base for the given search string and search type and returns the search results",
            meta={
                "unique.app/icon": "search",
                "unique.app/system-prompt": "Choose this tool if you need to search in the knowledge base",
            },
        )
        async def _search(
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
            settings: UniqueSettings = Depends(self._context_provider.get_settings),
        ) -> CallToolResult:
            """Search in the knowledge base"""

            knowledge_base_service = KnowledgeBaseService.from_settings(settings)

            content_chunks = knowledge_base_service.search_content_chunks(
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
