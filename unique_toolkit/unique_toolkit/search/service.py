from typing import Literal

import unique_sdk
from unique_sdk import Content

from unique_toolkit.chat.state import ChatState
from unique_toolkit.performance.async_wrapper import to_async


class SearchService:
    def __init__(self, state: ChatState):
        self.state = state

    def search(
        self,
        *,
        search_string: str,
        search_type: Literal["VECTOR", "COMBINED"],
        limit: int,
        scope_ids: list[str] = [],
    ):
        """
        Performs a synchronous search in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (Literal["VECTOR", "COMBINED"]): The type of search to perform.
            limit (int): The maximum number of results to return.

        Returns:
            The search results.
        """
        return self._trigger_search(search_string, search_type, limit, scope_ids)

    @to_async
    def async_search(
        self,
        *,
        search_string: str,
        search_type: Literal["VECTOR", "COMBINED"],
        limit: int,
        scope_ids: list[str] = [],
    ):
        """
        Performs an asynchronous search in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (Literal["VECTOR", "COMBINED"]): The type of search to perform.
            limit (int): The maximum number of results to return.

        Returns:
            The search results.
        """
        return self._trigger_search(search_string, search_type, limit, scope_ids)

    def _trigger_search(
        self,
        search_string: str,
        search_type: Literal["VECTOR", "COMBINED"],
        limit: int,
        scope_ids: list[str] = [],
    ):
        scope_ids = scope_ids or self.state.scope_ids or []
        return unique_sdk.Search.create(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            chatId=self.state.chat_id,
            searchString=search_string,
            searchType=search_type,
            scopeIds=scope_ids,
            limit=limit,
            chatOnly=self.state.chat_only,
        )

    def search_content(
        self,
        *,
        where: dict,
    ) -> list[Content]:
        """
        Performs a search in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            The search results.
        """
        return self._trigger_search_content(where)

    @to_async
    def async_search_content(
        self,
        *,
        where: dict,
    ) -> list[Content]:
        """
        Performs an asynchronous search in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            The search results.
        """
        return self._trigger_search_content(where)

    def _trigger_search_content(
        self,
        where: dict,
    ) -> list[Content]:
        return unique_sdk.Content.search(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            chatId=self.state.chat_id,
            where=where,  # type: ignore
        )
