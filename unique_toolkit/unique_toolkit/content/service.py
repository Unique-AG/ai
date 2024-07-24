import logging
from typing import Optional, cast

import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import Content, ContentChunk, ContentSearchType
from unique_toolkit.performance.async_wrapper import async_warning, to_async


class ContentService:
    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)

    def search_content_chunks(
        self,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        scope_ids: Optional[list[str]] = None,
    ) -> list[ContentChunk]:
        """
        Performs a synchronous search in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to None.

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
        search_type: ContentSearchType,
        limit: int,
        scope_ids: Optional[list[str]],
    ):
        """
        Performs an asynchronous search in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
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
        search_type: ContentSearchType,
        limit: int,
        scope_ids: Optional[list[str]],
    ) -> list[ContentChunk]:
        scope_ids = scope_ids or self.state.scope_ids or []

        if not scope_ids:
            self.logger.warning("No scope IDs provided for search.")

        try:
            searches = unique_sdk.Search.create(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
                searchString=search_string,
                searchType=search_type.name,
                scopeIds=scope_ids,
                limit=limit,
                chatOnly=self.state.chat_only,
            )
        except Exception as e:
            self.logger.error(f"Error while searching content chunks: {e}")
            raise e

        def map_to_content_chunks(searches: list[unique_sdk.Search]):
            return [ContentChunk(**search) for search in searches]

        # TODO change return type in sdk from Search to list[Search]
        searches = cast(list[unique_sdk.Search], searches)
        return map_to_content_chunks(searches)

    def search_contents(
        self,
        where: dict,
    ) -> list[Content]:
        """
        Performs a search in the knowledge base by filter (and not a smilarity search)
        This function loads complete content of the files from the knowledge base in contrast to search_content_chunks.

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
            where (dict): The search criteria, see unique_sdk.

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

        try:
            contents = unique_sdk.Content.search(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
                # TODO add type parameter
                where=where,  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Error while searching contents: {e}")
            raise e

        return map_contents(contents)

    # TODO implement, see unique_sdk.utils.file_io.py
    def upload_content(self):
        raise NotImplementedError(
            "Not implemented yet. Please use unique_sdk.utils.file_io.py for now."
        )

    # TODO implement, see unique_sdk.utils.file_io.py
    def download_content(self):
        raise NotImplementedError(
            "Not implemented yet. Please use unique_sdk.utils.file_io.py for now."
        )
