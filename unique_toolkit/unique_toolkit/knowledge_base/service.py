import logging
from pathlib import Path
from typing import Any

import unique_sdk

from unique_toolkit._common.utils.files import is_file_content, is_image_content
from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.constants import DEFAULT_SEARCH_LANGUAGE
from unique_toolkit.content.functions import (
    download_content,
    download_content_to_bytes,
    download_content_to_file_by_id,
    get_content_info,
    search_content_chunks,
    search_content_chunks_async,
    search_contents,
    search_contents_async,
    update_content,
    upload_content,
    upload_content_from_bytes,
)
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentInfo,
    ContentRerankerConfig,
    ContentSearchType,
    PaginatedContentInfo,
)

_LOGGER = logging.getLogger(f"toolkit.knowledge_base.{__name__}")


class KnowledgeBaseService:
    """
    Provides methods for searching, downloading and uploading content in the knowledge base.
    """

    def __init__(
        self,
        company_id: str,
        user_id: str,
        metadata_filter: dict | None = None,
    ):
        """
        Initialize the ContentService with a company_id, user_id and chat_id.
        """

        self._metadata_filter = None
        [company_id, user_id] = validate_required_values([company_id, user_id])
        self._company_id = company_id
        self._user_id = user_id
        self._metadata_filter = metadata_filter

    @classmethod
    def from_event(cls, event: BaseEvent):
        """
        Initialize the ContentService with an event.
        """
        metadata_filter = None

        if isinstance(event, (ChatEvent | Event)):
            metadata_filter = event.payload.metadata_filter

        return cls(
            company_id=event.company_id,
            user_id=event.user_id,
            metadata_filter=metadata_filter,
        )

    @classmethod
    def from_settings(
        cls,
        settings: UniqueSettings | str | None = None,
        metadata_filter: dict | None = None,
    ):
        """
        Initialize the ContentService with a settings object and metadata filter.
        """

        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        elif isinstance(settings, str):
            settings = UniqueSettings.from_env_auto_with_sdk_init(filename=settings)

        return cls(
            company_id=settings.auth.company_id.get_secret_value(),
            user_id=settings.auth.user_id.get_secret_value(),
            metadata_filter=metadata_filter,
        )

    def search_content_chunks(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
        scope_ids: list[str] | None = None,
        metadata_filter: dict | None = None,
        content_ids: list[str] | None = None,
        score_threshold: float | None = None,
    ) -> list[ContentChunk]:
        """
        Performs a synchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str, optional): The language for the full-text search. Defaults to "english".
            reranker_config (ContentRerankerConfig | None, optional): The reranker configuration. Defaults to None.
            scope_ids (list[str] | None, optional): The scope IDs to filter by. Defaults to None.
            metadata_filter (dict | None, optional): UniqueQL metadata filter. If unspecified/None, it tries to use the metadata filter from the event. Defaults to None.
            content_ids (list[str] | None, optional): The content IDs to search within. Defaults to None.
            score_threshold (float | None, optional): Sets the minimum similarity score for search results to be considered. Defaults to 0.

        Returns:
            list[ContentChunk]: The search results.

        Raises:
            Exception: If there's an error during the search operation.
        """

        if metadata_filter is None:
            metadata_filter = self._metadata_filter

        try:
            searches = search_content_chunks(
                user_id=self._user_id,
                company_id=self._company_id,
                chat_id="",
                search_string=search_string,
                search_type=search_type,
                limit=limit,
                search_language=search_language,
                reranker_config=reranker_config,
                scope_ids=scope_ids,
                chat_only=False,
                metadata_filter=metadata_filter,
                content_ids=content_ids,
                score_threshold=score_threshold,
            )
            return searches
        except Exception as e:
            _LOGGER.error(f"Error while searching content chunks: {e}")
            raise e

    async def search_content_chunks_async(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
        scope_ids: list[str] | None = None,
        metadata_filter: dict | None = None,
        content_ids: list[str] | None = None,
        score_threshold: float | None = None,
    ):
        """
        Performs an asynchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str, optional): The language for the full-text search. Defaults to "english".
            reranker_config (ContentRerankerConfig | None, optional): The reranker configuration. Defaults to None.
            scope_ids (list[str] | None, optional): The scope IDs to filter by. Defaults to None.
            metadata_filter (dict | None, optional): UniqueQL metadata filter. If unspecified/None, it tries to use the metadata filter from the event. Defaults to None.
            content_ids (list[str] | None, optional): The content IDs to search within. Defaults to None.
            score_threshold (float | None, optional): Sets the minimum similarity score for search results to be considered. Defaults to 0.

        Returns:
            list[ContentChunk]: The search results.

        Raises:
            Exception: If there's an error during the search operation.
        """
        if metadata_filter is None:
            metadata_filter = self._metadata_filter

        try:
            searches = await search_content_chunks_async(
                user_id=self._user_id,
                company_id=self._company_id,
                chat_id="",
                search_string=search_string,
                search_type=search_type,
                limit=limit,
                search_language=search_language,
                reranker_config=reranker_config,
                scope_ids=scope_ids,
                chat_only=False,
                metadata_filter=metadata_filter,
                content_ids=content_ids,
                score_threshold=score_threshold,
            )
            return searches
        except Exception as e:
            _LOGGER.error(f"Error while searching content chunks: {e}")
            raise e

    def search_contents(
        self,
        *,
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

        return search_contents(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id="",
            where=where,
        )

    async def search_contents_async(
        self,
        *,
        where: dict,
    ) -> list[Content]:
        """
        Performs an asynchronous search for content files in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """

        return await search_contents_async(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id="",
            where=where,
        )

    def upload_content_from_bytes(
        self,
        content: bytes,
        *,
        content_name: str,
        mime_type: str,
        scope_id: str | None = None,
        skip_ingestion: bool = False,
        ingestion_config: unique_sdk.Content.IngestionConfig | None = None,
        metadata: dict | None = None,
    ) -> Content:
        """
        Uploads content to the knowledge base.

        Args:
            content (bytes): The content to upload.
            content_name (str): The name of the content.
            mime_type (str): The MIME type of the content.
            scope_id (str | None): The scope ID. Defaults to None.
            skip_ingestion (bool): Whether to skip ingestion. Defaults to False.
            skip_excel_ingestion (bool): Whether to skip excel ingestion. Defaults to False.
            ingestion_config (unique_sdk.Content.IngestionConfig | None): The ingestion configuration. Defaults to None.
            metadata (dict | None): The metadata to associate with the content. Defaults to None.

        Returns:
            Content: The uploaded content.
        """

        return upload_content_from_bytes(
            user_id=self._user_id,
            company_id=self._company_id,
            content=content,
            content_name=content_name,
            mime_type=mime_type,
            scope_id=scope_id,
            chat_id="",
            skip_ingestion=skip_ingestion,
            ingestion_config=ingestion_config,
            metadata=metadata,
        )

    def upload_content(
        self,
        path_to_content: str,
        content_name: str,
        mime_type: str,
        scope_id: str | None = None,
        skip_ingestion: bool = False,
        skip_excel_ingestion: bool = False,
        ingestion_config: unique_sdk.Content.IngestionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Uploads content to the knowledge base.

        Args:
            path_to_content (str): The path to the content to upload.
            content_name (str): The name of the content.
            mime_type (str): The MIME type of the content.
            scope_id (str | None): The scope ID. Defaults to None.
            skip_ingestion (bool): Whether to skip ingestion. Defaults to False.
            skip_excel_ingestion (bool): Whether to skip excel ingestion. Defaults to False.
            ingestion_config (unique_sdk.Content.IngestionConfig | None): The ingestion configuration. Defaults to None.
            metadata (dict[str, Any] | None): The metadata to associate with the content. Defaults to None.

        Returns:
            Content: The uploaded content.
        """

        return upload_content(
            user_id=self._user_id,
            company_id=self._company_id,
            path_to_content=path_to_content,
            content_name=content_name,
            mime_type=mime_type,
            scope_id=scope_id,
            chat_id="",
            skip_ingestion=skip_ingestion,
            skip_excel_ingestion=skip_excel_ingestion,
            ingestion_config=ingestion_config,
            metadata=metadata,
        )

    def download_content_to_file_by_id(
        self,
        *,
        content_id: str,
        filename: str | None = None,
        tmp_dir_path: str | Path | None = "/tmp",
    ):
        """
        Downloads content from a chat and saves it to a file.

        Args:
            content_id (str): The ID of the content to download.
            filename (str | None): The name of the file to save the content as. If not provided, the original filename will be used. Defaults to None.
            tmp_dir_path (str | Path | None): The path to the temporary directory where the content will be saved. Defaults to "/tmp".

        Returns:
            Path: The path to the downloaded file.

        Raises:
            Exception: If the download fails or the filename cannot be determined.
        """

        return download_content_to_file_by_id(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            chat_id="",
            filename=filename,
            tmp_dir_path=tmp_dir_path,
        )

    # TODO: Discuss if we should deprecate this method due to unclear use by content_name
    def download_content(
        self,
        *,
        content_id: str,
        content_name: str,
        dir_path: str | Path | None = "/tmp",
    ) -> Path:
        """
        Downloads content to temporary directory

        Args:
            content_id (str): The id of the uploaded content.
            content_name (str): The name of the uploaded content.
            dir_path (Optional[Union[str, Path]]): The directory path to download the content to, defaults to "/tmp". If not provided, the content will be downloaded to a random directory inside /tmp. Be aware that this directory won't be cleaned up automatically.

        Returns:
            content_path: The path to the downloaded content in the temporary directory.

        Raises:
            Exception: If the download fails.
        """

        return download_content(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            content_name=content_name,
            chat_id="",
            dir_path=dir_path,
        )

    def download_content_to_bytes(
        self,
        *,
        content_id: str,
        chat_id: str | None = None,
    ) -> bytes:
        """
        Downloads content to memory

        Args:
            content_id (str): The id of the uploaded content.
            chat_id (Optional[str]): The chat_id, defaults to None.

        Returns:
            bytes: The downloaded content.

        Raises:
            Exception: If the download fails.
        """

        return download_content_to_bytes(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            chat_id="",
        )

    def is_file_content(self, filename: str) -> bool:
        return is_file_content(filename=filename)

    def is_image_content(self, filename: str) -> bool:
        return is_image_content(filename=filename)

    def get_paginated_content_infos(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        skip: int | None = None,
        take: int | None = None,
        file_path: str | None = None,
    ) -> PaginatedContentInfo:
        return get_content_info(
            user_id=self._user_id,
            company_id=self._company_id,
            metadata_filter=metadata_filter,
            skip=skip,
            take=take,
            file_path=file_path,
        )

    def replace_content_metadata(
        self,
        *,
        content_id: str,
        metadata: dict[str, Any],
    ) -> ContentInfo:
        return update_content(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            metadata=metadata,
        )
