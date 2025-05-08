import logging
from pathlib import Path

import unique_sdk
from requests import Response
from typing_extensions import deprecated

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.content import DOMAIN_NAME
from unique_toolkit.content.constants import DEFAULT_SEARCH_LANGUAGE
from unique_toolkit.content.functions import (
    download_content,
    download_content_to_bytes,
    download_content_to_file_by_id,
    request_content_by_id,
    search_content_chunks,
    search_content_chunks_async,
    search_contents,
    search_contents_async,
    upload_content,
    upload_content_from_bytes,
)
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentRerankerConfig,
    ContentSearchType,
)

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


class ContentService:
    """
    Provides methods for searching, downloading and uploading content in the knowledge base.

    Attributes:
        event: BaseEvent | Event, this can be None ONLY if company_id and user_id are provided.
        company_id (str): The company ID.
        user_id (str): The user ID.
        chat_id (str): The chat ID. Defaults to None
        metadata_filter (dict | None): is only initialised from an Event(Deprecated) or ChatEvent.
    """

    def __init__(
        self,
        event: Event | BaseEvent | None = None,
        company_id: str | None = None,
        user_id: str | None = None,
        chat_id: str | None = None,
    ):
        self._event = event  # Changed to protected attribute
        self._metadata_filter = None
        if event:
            self._company_id = event.company_id
            self._user_id = event.user_id
            if isinstance(event, (ChatEvent, Event)):
                self._metadata_filter = event.payload.metadata_filter
                self._chat_id = event.payload.chat_id
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            self._company_id = company_id
            self._user_id = user_id
            self._chat_id = chat_id

    @property
    @deprecated(
        "The event property is deprecated and will be removed in a future version."
    )
    def event(self) -> Event | BaseEvent | None:
        """
        Get the event object (deprecated).

        Returns:
            Event | BaseEvent | None: The event object.
        """
        return self._event

    @property
    @deprecated(
        "The company_id property is deprecated and will be removed in a future version."
    )
    def company_id(self) -> str | None:
        """
        Get the company identifier (deprecated).

        Returns:
            str | None: The company identifier.
        """
        return self._company_id

    @company_id.setter
    @deprecated(
        "The company_id setter is deprecated and will be removed in a future version."
    )
    def company_id(self, value: str | None) -> None:
        """
        Set the company identifier (deprecated).

        Args:
            value (str | None): The company identifier.
        """
        self._company_id = value

    @property
    @deprecated(
        "The user_id property is deprecated and will be removed in a future version."
    )
    def user_id(self) -> str | None:
        """
        Get the user identifier (deprecated).

        Returns:
            str | None: The user identifier.
        """
        return self._user_id

    @user_id.setter
    @deprecated(
        "The user_id setter is deprecated and will be removed in a future version."
    )
    def user_id(self, value: str | None) -> None:
        """
        Set the user identifier (deprecated).

        Args:
            value (str | None): The user identifier.
        """
        self._user_id = value

    @property
    @deprecated(
        "The chat_id property is deprecated and will be removed in a future version."
    )
    def chat_id(self) -> str | None:
        """
        Get the chat identifier (deprecated).

        Returns:
            str | None: The chat identifier.
        """
        return self._chat_id

    @chat_id.setter
    @deprecated(
        "The chat_id setter is deprecated and will be removed in a future version."
    )
    def chat_id(self, value: str | None) -> None:
        """
        Set the chat identifier (deprecated).

        Args:
            value (str | None): The chat identifier.
        """
        self._chat_id = value

    @property
    @deprecated(
        "The metadata_filter property is deprecated and will be removed in a future version."
    )
    def metadata_filter(self) -> dict | None:
        """
        Get the metadata filter (deprecated).

        Returns:
            dict | None: The metadata filter.
        """
        return self._metadata_filter

    @metadata_filter.setter
    @deprecated(
        "The metadata_filter setter is deprecated and will be removed in a future version."
    )
    def metadata_filter(self, value: dict | None) -> None:
        """
        Set the metadata filter (deprecated).

        Args:
            value (dict | None): The metadata filter.
        """
        self._metadata_filter = value

    def search_content_chunks(
        self,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        chat_id: str = "",
        reranker_config: ContentRerankerConfig | None = None,
        scope_ids: list[str] | None = None,
        chat_only: bool | None = None,
        metadata_filter: dict | None = None,
        content_ids: list[str] | None = None,
    ) -> list[ContentChunk]:
        """
        Performs a synchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str, optional): The language for the full-text search. Defaults to "english".
            chat_id (str, optional): The chat ID for context. Defaults to empty string.
            reranker_config (ContentRerankerConfig | None, optional): The reranker configuration. Defaults to None.
            scope_ids (list[str] | None, optional): The scope IDs to filter by. Defaults to None.
            chat_only (bool | None, optional): Whether to search only in the current chat. Defaults to None.
            metadata_filter (dict | None, optional): UniqueQL metadata filter. If unspecified/None, it tries to use the metadata filter from the event. Defaults to None.
            content_ids (list[str] | None, optional): The content IDs to search within. Defaults to None.

        Returns:
            list[ContentChunk]: The search results.

        Raises:
            Exception: If there's an error during the search operation.
        """

        if metadata_filter is None:
            metadata_filter = self._metadata_filter

        chat_id = chat_id or self._chat_id  # type: ignore

        if chat_only and not chat_id:
            raise ValueError("Please provide chat_id when limiting with chat_only")

        try:
            searches = search_content_chunks(
                user_id=self._user_id,
                company_id=self._company_id,
                chat_id=chat_id,
                search_string=search_string,
                search_type=search_type,
                limit=limit,
                search_language=search_language,
                reranker_config=reranker_config,
                scope_ids=scope_ids,
                chat_only=chat_only,
                metadata_filter=metadata_filter,
                content_ids=content_ids,
            )
            return searches
        except Exception as e:
            logger.error(f"Error while searching content chunks: {e}")
            raise e

    async def search_content_chunks_async(
        self,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        chat_id: str = "",
        reranker_config: ContentRerankerConfig | None = None,
        scope_ids: list[str] | None = None,
        chat_only: bool | None = None,
        metadata_filter: dict | None = None,
        content_ids: list[str] | None = None,
    ):
        """
        Performs an asynchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str, optional): The language for the full-text search. Defaults to "english".
            chat_id (str, optional): The chat ID for context. Defaults to empty string.
            reranker_config (ContentRerankerConfig | None, optional): The reranker configuration. Defaults to None.
            scope_ids (list[str] | None, optional): The scope IDs to filter by. Defaults to None.
            chat_only (bool | None, optional): Whether to search only in the current chat. Defaults to None.
            metadata_filter (dict | None, optional): UniqueQL metadata filter. If unspecified/None, it tries to use the metadata filter from the event. Defaults to None.
            content_ids (list[str] | None, optional): The content IDs to search within. Defaults to None.

        Returns:
            list[ContentChunk]: The search results.

        Raises:
            Exception: If there's an error during the search operation.
        """
        if metadata_filter is None:
            metadata_filter = self._metadata_filter

        chat_id = chat_id or self._chat_id  # type: ignore

        if chat_only and not chat_id:
            raise ValueError("Please provide chat_id when limiting with chat_only.")

        try:
            searches = await search_content_chunks_async(
                user_id=self._user_id,
                company_id=self._company_id,
                chat_id=chat_id,
                search_string=search_string,
                search_type=search_type,
                limit=limit,
                search_language=search_language,
                reranker_config=reranker_config,
                scope_ids=scope_ids,
                chat_only=chat_only,
                metadata_filter=metadata_filter,
                content_ids=content_ids,
            )
            return searches
        except Exception as e:
            logger.error(f"Error while searching content chunks: {e}")
            raise e

    def search_contents(
        self,
        where: dict,
        chat_id: str = "",
    ) -> list[Content]:
        """
        Performs a search in the knowledge base by filter (and not a smilarity search)
        This function loads complete content of the files from the knowledge base in contrast to search_content_chunks.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """
        chat_id = chat_id or self._chat_id  # type: ignore

        return search_contents(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=chat_id,
            where=where,
        )

    async def search_contents_async(
        self,
        where: dict,
        chat_id: str = "",
    ) -> list[Content]:
        """
        Performs an asynchronous search for content files in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """
        chat_id = chat_id or self._chat_id  # type: ignore

        return await search_contents_async(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=chat_id,
            where=where,
        )

    def search_content_on_chat(self, chat_id: str) -> list[Content]:
        where = {"ownerId": {"equals": chat_id}}

        return self.search_contents(where, chat_id=chat_id)

    def upload_content_from_bytes(
        self,
        content: bytes,
        content_name: str,
        mime_type: str,
        scope_id: str | None = None,
        chat_id: str | None = None,
        skip_ingestion: bool = False,
        ingestion_config: unique_sdk.Content.IngestionConfig | None = None,
    ) -> Content:
        """
        Uploads content to the knowledge base.

        Args:
            content (bytes): The content to upload.
            content_name (str): The name of the content.
            mime_type (str): The MIME type of the content.
            scope_id (str | None): The scope ID. Defaults to None.
            chat_id (str | None): The chat ID. Defaults to None.
            skip_ingestion (bool): Whether to skip ingestion. Defaults to False.

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
            chat_id=chat_id,
            skip_ingestion=skip_ingestion,
            ingestion_config=ingestion_config,
        )

    def upload_content(
        self,
        path_to_content: str,
        content_name: str,
        mime_type: str,
        scope_id: str | None = None,
        chat_id: str | None = None,
        skip_ingestion: bool = False,
        ingestion_config: unique_sdk.Content.IngestionConfig | None = None,
    ):
        """
        Uploads content to the knowledge base.

        Args:
            path_to_content (str): The path to the content to upload.
            content_name (str): The name of the content.
            mime_type (str): The MIME type of the content.
            scope_id (str | None): The scope ID. Defaults to None.
            chat_id (str | None): The chat ID. Defaults to None.
            skip_ingestion (bool): Whether to skip ingestion. Defaults to False.

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
            chat_id=chat_id,
            skip_ingestion=skip_ingestion,
            ingestion_config=ingestion_config,
        )

    def request_content_by_id(
        self,
        content_id: str,
        chat_id: str | None = None,
    ) -> Response:
        """
        Sends a request to download content from a chat.

        Args:
            content_id (str): The ID of the content to download.
            chat_id (str): The ID of the chat from which to download the content. Defaults to None to download from knowledge base.

        Returns:
            requests.Response: The response object containing the downloaded content.

        """
        chat_id = chat_id or self._chat_id  # type: ignore

        return request_content_by_id(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            chat_id=chat_id,
        )

    def download_content_to_file_by_id(
        self,
        content_id: str,
        chat_id: str | None = None,
        filename: str | None = None,
        tmp_dir_path: str | Path | None = "/tmp",
    ):
        """
        Downloads content from a chat and saves it to a file.

        Args:
            content_id (str): The ID of the content to download.
            chat_id (str | None): The ID of the chat to download from. Defaults to None and the file is downloaded from the knowledge base.
            filename (str | None): The name of the file to save the content as. If not provided, the original filename will be used. Defaults to None.
            tmp_dir_path (str | Path | None): The path to the temporary directory where the content will be saved. Defaults to "/tmp".

        Returns:
            Path: The path to the downloaded file.

        Raises:
            Exception: If the download fails or the filename cannot be determined.
        """

        chat_id = chat_id or self._chat_id  # type: ignore

        return download_content_to_file_by_id(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            chat_id=chat_id,
            filename=filename,
            tmp_dir_path=tmp_dir_path,
        )

    # TODO: Discuss if we should deprecate this method due to unclear use by content_name
    def download_content(
        self,
        content_id: str,
        content_name: str,
        chat_id: str | None = None,
        dir_path: str | Path | None = "/tmp",
    ) -> Path:
        """
        Downloads content to temporary directory

        Args:
            content_id (str): The id of the uploaded content.
            content_name (str): The name of the uploaded content.
            chat_id (Optional[str]): The chat_id, defaults to None.
            dir_path (Optional[Union[str, Path]]): The directory path to download the content to, defaults to "/tmp". If not provided, the content will be downloaded to a random directory inside /tmp. Be aware that this directory won't be cleaned up automatically.

        Returns:
            content_path: The path to the downloaded content in the temporary directory.

        Raises:
            Exception: If the download fails.
        """

        chat_id = chat_id or self._chat_id  # type: ignore

        return download_content(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            content_name=content_name,
            chat_id=chat_id,
            dir_path=dir_path,
        )

    def download_content_to_bytes(
        self,
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
        chat_id = chat_id or self._chat_id  # type: ignore
        return download_content_to_bytes(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            chat_id=chat_id,
        )
