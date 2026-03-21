from typing import Any

from unique_sdk.api_resources._content import Content
from unique_sdk.api_resources._embedding import Embeddings
from unique_sdk.api_resources._search import Search
from unique_sdk.api_resources._search_string import SearchString

from .._base import BaseManager, DomainObject


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------


class ContentObject(DomainObject):
    """A knowledge-base content item with mutation methods."""

    async def update(self, **params: Any) -> "ContentObject":
        result = await Content.update_async(self._user_id, self._company_id, **params)
        self._update_raw(result)
        return self

    async def update_ingestion_state(self, **params: Any) -> "ContentObject":
        result = await Content.update_ingestion_state_async(
            self._user_id, self._company_id, **params
        )
        self._update_raw(result)
        return self

    async def delete(self, **params: Any) -> None:
        await Content.delete_async(self._user_id, self._company_id, **params)


class ContentManager(BaseManager):
    """Search, upsert and manage knowledge-base content."""

    async def search(self, **params: Any) -> list[ContentObject]:
        results = await Content.search_async(self._user_id, self._company_id, **params)
        return [ContentObject(self._user_id, self._company_id, r) for r in results]

    async def get_info(self, **params: Any) -> Any:
        return await Content.get_info_async(self._user_id, self._company_id, **params)

    async def get_infos(self, **params: Any) -> Any:
        return await Content.get_infos_async(self._user_id, self._company_id, **params)

    async def upsert(self, **params: Any) -> ContentObject:
        result = await Content.upsert_async(self._user_id, self._company_id, **params)
        return ContentObject(self._user_id, self._company_id, result)

    async def update(self, **params: Any) -> Any:
        return await Content.update_async(self._user_id, self._company_id, **params)

    async def update_ingestion_state(self, **params: Any) -> Any:
        return await Content.update_ingestion_state_async(
            self._user_id, self._company_id, **params
        )

    async def delete(self, **params: Any) -> Any:
        return await Content.delete_async(self._user_id, self._company_id, **params)

    async def ingest_magic_table_sheets(self, **params: Any) -> Any:
        return await Content.ingest_magic_table_sheets_async(
            self._user_id, self._company_id, **params
        )

    async def resolve_content_id(
        self,
        content_id: str | None = None,
        file_path: str | None = None,
    ) -> str | None:
        return Content.resolve_content_id_from_file_path(
            self._user_id, self._company_id, content_id=content_id, file_path=file_path
        )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchResult(DomainObject):
    """A single vector-search result."""


class SearchManager(BaseManager):
    """Vector search over the knowledge base."""

    async def create(self, **params: Any) -> list[SearchResult]:
        results = await Search.create_async(self._user_id, self._company_id, **params)
        return [SearchResult(self._user_id, self._company_id, r) for r in results]


# ---------------------------------------------------------------------------
# SearchString
# ---------------------------------------------------------------------------


class SearchStringResult(DomainObject):
    """A rewritten/optimised search query string."""


class SearchStringManager(BaseManager):
    """Generate optimised search query strings from chat history."""

    async def create(self, **params: Any) -> SearchStringResult:
        result = await SearchString.create_async(
            self._user_id, self._company_id, **params
        )
        return SearchStringResult(self._user_id, self._company_id, result)


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


class EmbeddingsResult(DomainObject):
    """Embedding vectors for a list of texts."""


class EmbeddingsManager(BaseManager):
    """Generate text embeddings via the Unique gateway."""

    async def create(self, **params: Any) -> EmbeddingsResult:
        result = await Embeddings.create_async(
            self._user_id, self._company_id, **params
        )
        return EmbeddingsResult(self._user_id, self._company_id, result)
