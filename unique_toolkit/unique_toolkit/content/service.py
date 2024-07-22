import logging
from typing import Literal, Optional

import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.mapper import from_searches_to_content_chunks
from unique_toolkit.content.schemas import Content, ContentChunk
from unique_toolkit.performance.async_wrapper import async_warning, to_async


class SearchService:
    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)

    def search_content_chunks(
        self,
        search_string: str,
        search_type: Literal["VECTOR", "COMBINED"],
        limit: int,
        scope_ids: Optional[list[str]],
    ) -> list[ContentChunk]:
        """
        Performs a synchronous search in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (Literal["VECTOR", "COMBINED"]): The type of search to perform.
            limit (int): The maximum number of results to return.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to [].

        Returns:
            list[ContentChunk]: The search results.
        """
        return self._trigger_search_content_chunks(
            search_string,
            search_type,
            limit,
            scope_ids,
        )

    @to_async
    @async_warning
    def async_search_content_chunks(
        self,
        search_string: str,
        search_type: Literal["VECTOR", "COMBINED"],
        limit: int,
        scope_ids: Optional[list[str]],
    ):
        """
        Performs an asynchronous search in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (Literal["VECTOR", "COMBINED"]): The type of search to perform.
            limit (int): The maximum number of results to return.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to [].

        Returns:
            list[ContentChunk]: The search results.
        """
        return self._trigger_search_content_chunks(
            search_string,
            search_type,
            limit,
            scope_ids,
        )

    def _trigger_search_content_chunks(
        self,
        search_string: str,
        search_type: Literal["VECTOR", "COMBINED"],
        limit: int,
        scope_ids: Optional[list[str]],
    ) -> list[ContentChunk]:
        scope_ids = scope_ids or self.state.scope_ids or None

        if not scope_ids:
            self.logger.warn("No scope IDs provided for search.")

        search_results = unique_sdk.Search.create(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            chatId=self.state.chat_id,
            searchString=search_string,
            searchType=search_type,
            scopeIds=scope_ids,  # type: ignore
            limit=limit,
            chatOnly=self.state.chat_only,
        )

        return from_searches_to_content_chunks(search_results)  # type: ignore

    def search_contents(
        self,
        where: dict,
    ) -> list[Content]:
        """
        Performs a search in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """
        return self._trigger_search_contents(where)

    @to_async
    @async_warning
    def async_search_contents(
        self,
        where: dict,
    ) -> list[Content]:
        """
        Performs an asynchronous search in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """
        return self._trigger_search_contents(where)

    def _trigger_search_contents(
        self,
        where: dict,
    ) -> list[Content]:
        """
        Performs a search in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """

        def map_content_chunk(content_chunk):
            return ContentChunk(
                id=content_chunk["id"],
                text=content_chunk["text"],
                start_page=content_chunk["startPage"],
                end_page=content_chunk["endPage"],
                order=content_chunk["order"],
            )

        def map_content(content):
            return Content(
                id=content["id"],
                key=content["key"],
                title=content["title"],
                url=content["url"],
                chunks=[map_content_chunk(chunk) for chunk in content["chunks"]],
            )

        def map_contents(contents):
            return [map_content(content) for content in contents]

        contents = unique_sdk.Content.search(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            chatId=self.state.chat_id,
            where=where,
        )
        return map_contents(contents)
