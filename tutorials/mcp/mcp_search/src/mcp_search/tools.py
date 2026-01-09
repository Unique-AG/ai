from copy import deepcopy
from enum import StrEnum
from textwrap import dedent
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
        ) -> CallToolResult:
            """Search in the knowledge base"""

            settings = self._get_unique_settings_for_request()

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

        @mcp.tool(
            name="list_files",
            description="This tool lists the files in the knowledge base",
            meta={
                "unique.app/icon": "file",
                "unique.app/system-prompt": "Choose this tool if you need to list the files in the knowledge base",
            },
        )
        def _list_files(
            user_confirmed: Annotated[
                bool,
                Field(
                    description="""Weather the user has confirmed that the tool should be used. 
                    You must have explicit confirmation from the user before using this tool."""
                ),
            ],
        ) -> CallToolResult:
            """List the files in the knowledge base"""

            if not user_confirmed:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="You must have explicit confirmation from the user before using this tool.",
                        )
                    ],
                )

            files = dedent("""
                        ├── src
                        │   └── mcp_search
                        │       ├── __init__.py
                        │       ├── favicon.ico
                        │       ├── mcp_client.py
                        │       ├── mcp_search_server.py
                        │       ├── routes.py
                        │       ├── tools.py
                        │       └── util.py
                        """)

            return CallToolResult(
                content=[TextContent(type="text", text=files)],
            )

        Filenames = StrEnum(
            "Filenames",
            {
                filename: filename
                for filename in [
                    "mcp_client.py",
                    "mcp_search_server.py",
                    "routes.py",
                    "tools.py",
                    "util.py",
                    "favicon.ico",
                    "pyproject.toml",
                    "README.md",
                    "LICENSE",
                ]
            },
        )

        @mcp.tool(
            name="find_file",
            description=dedent("""This tool finds a file in the knowledge base by name or a fuzzy search string.
            If you provide a fuzzy search string, the tool will return the files that match the search string.
            and the you should ask the user which file they want to use.
            If you provide a file name, the tool will return the file to download."""),
            meta={
                "unique.app/icon": "file",
                "unique.app/system-prompt": "Choose this tool if you need to find a file in the knowledge base by name",
            },
        )
        def _find_file(
            file_name_or_fuzzy_search_string: Annotated[
                Filenames | str,  # type: ignore
                Field(
                    description="""
                        The name of the file to find in the knowledge base or a fuzzy search string to find the file.
                        If you provide a fuzzy search string, the tool will return the files that match the search string.
                        and the you should ask the user which file they want to use.
                        If you provide a file name, the tool will return the file to download.
                        
                        """
                ),
            ] = None,
        ) -> CallToolResult:
            """Fuzzy search the files in the knowledge base"""

            if file_name_or_fuzzy_search_string in Filenames:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"The file {file_name_or_fuzzy_search_string} does exist",  # type: ignore
                        )
                    ],
                )
            else:
                files = [
                    file
                    for file in Filenames
                    if file_name_or_fuzzy_search_string in file
                ]

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="The following files match the search string: \n -"
                            + "\n - ".join(files),
                        )
                    ],
                )
