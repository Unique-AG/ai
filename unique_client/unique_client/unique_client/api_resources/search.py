"""
Search API resource for the Unique SDK v2.
"""

from pydantic import RootModel

from unique_client.core import APIResource
from unique_client.unique_client.api_resources.api_dtos import (
    ListObjectDto,
    PublicCreateSearchDto,
    SearchResultDto,
)


# TODO: Check if you can use this instead of ListObjectDto
class PublicSearchResultListDto(RootModel):
    """List wrapper for search results."""

    root: list[SearchResultDto]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)


class Search(APIResource):
    """
    Search API resource for managing search operations.

    This class provides both sync and async methods for performing content searches
    using the /public/search/search endpoint.

    All methods use the intrinsic RequestContextProtocol for automatic header and URL handling.
    """

    OBJECT_NAME = "search"

    # Synchronous methods
    # ==================

    def search(self, params: PublicCreateSearchDto) -> ListObjectDto:
        """Perform search using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/search/search",
            model_class=ListObjectDto,
            params=params,
        )

    # Asynchronous methods
    # ===================

    async def search_async(self, params: PublicCreateSearchDto) -> ListObjectDto:
        """Perform search asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/search/search",
            model_class=ListObjectDto,
            params=params,
        )
