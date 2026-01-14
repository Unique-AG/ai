from copy import deepcopy
from typing import Annotated

from fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from mcp_search.util import get_unique_auth_from_zitadel_user
from unique_mcp.provider import BaseProvider
from unique_toolkit import KnowledgeBaseService
from unique_toolkit.app.unique_settings import UniqueAuth, UniqueSettings
from unique_toolkit.content.schemas import ContentSearchType


class UniqueKnowledgeBaseTools(BaseProvider):
    def __init__(self, unique_settings: UniqueSettings | None = None) -> None:
        super().__init__()
        self._unique_settings = (
            unique_settings or UniqueSettings.from_env_auto_with_sdk_init()
        )

    def _get_unique_settings_for_request(
        self, unique_auth: UniqueAuth | None = None
    ) -> UniqueSettings:
        """
        Create a unique settings object for the current request. This is necessary
        """
        settings = deepcopy(self._unique_settings)
        if unique_auth is not None:
            settings.auth = unique_auth
        else:
            settings.auth = get_unique_auth_from_zitadel_user()

        return settings

    def register(self, *, mcp: FastMCP) -> None:
        @mcp.tool(
            name="search",
            description="This tool does search in the knowledge base for the given search string and search type and returns the search results",
            meta={
                "unique.app/icon": "search",
                "unique.app/system-prompt": "Choose this tool if you need to search in the knowledge base",
            },
            exclude_args=["unique_auth"],
        )
        def _search(
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
            unique_auth: UniqueAuth | None = None,
        ) -> CallToolResult:
            """Search in the knowledge base"""

            settings = self._get_unique_settings_for_request(unique_auth=unique_auth)

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
