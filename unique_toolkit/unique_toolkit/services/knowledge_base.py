import asyncio
import logging
from pathlib import Path
from typing import Any, overload

import humps
import unique_sdk

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.constants import (
    DEFAULT_SEARCH_LANGUAGE,
)
from unique_toolkit.content.functions import (
    delete_content,
    delete_content_async,
    download_content_to_bytes,
    download_content_to_file_by_id,
    get_content_info,
    get_folder_info,
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
    DeleteContentResponse,
    FolderInfo,
    PaginatedContentInfos,
)

_LOGGER = logging.getLogger(f"toolkit.knowledge_base.{__name__}")

_DEFAULT_SCORE_THRESHOLD: float = 0.5


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

    @overload
    def search_content_chunks(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        scope_ids: list[str],
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
    ) -> list[ContentChunk]: ...

    @overload
    def search_content_chunks(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        metadata_filter: dict,
        scope_ids: list[str] | None = None,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
    ) -> list[ContentChunk]: ...

    @overload
    def search_content_chunks(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        metadata_filter: dict,
        content_ids: list[str],
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
    ) -> list[ContentChunk]: ...

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

    @overload
    async def search_content_chunks_async(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        scope_ids: list[str],
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
    ) -> list[ContentChunk]: ...

    @overload
    async def search_content_chunks_async(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        metadata_filter: dict,
        scope_ids: list[str] | None = None,
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
    ) -> list[ContentChunk]: ...

    @overload
    async def search_content_chunks_async(
        self,
        *,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        metadata_filter: dict,
        content_ids: list[str],
        score_threshold: float = _DEFAULT_SCORE_THRESHOLD,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: ContentRerankerConfig | None = None,
    ) -> list[ContentChunk]: ...

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
        scope_id: str,
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
        scope_id: str,
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

    def download_content_to_file(
        self,
        *,
        content_id: str,
        output_dir_path: Path | None = None,
        output_filename: str | None = None,
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
            filename=output_filename,
            tmp_dir_path=output_dir_path,
        )

    def download_content_to_bytes(
        self,
        *,
        content_id: str,
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
            chat_id=None,
        )

    def get_paginated_content_infos(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        skip: int | None = None,
        take: int | None = None,
        file_path: str | None = None,
    ) -> PaginatedContentInfos:
        return get_content_info(
            user_id=self._user_id,
            company_id=self._company_id,
            metadata_filter=metadata_filter,
            skip=skip,
            take=take,
            file_path=file_path,
        )

    def get_folder_info(
        self,
        *,
        scope_id: str,
    ) -> FolderInfo:
        return get_folder_info(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
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

    def _resolve_visible_file_tree(self, content_infos: list[ContentInfo]) -> list[str]:
        # collect all scope ids
        folder_id_paths: set[str] = set()
        known_folder_paths: set[str] = set()
        for content_info in content_infos:
            if (
                content_info.metadata
                and content_info.metadata.get(r"{FullPath}") is not None
            ):
                known_folder_paths.add(str(content_info.metadata.get(r"{FullPath}")))
                continue

            if (
                content_info.metadata
                and content_info.metadata.get("folderIdPath") is not None
            ):
                folder_id_paths.add(str(content_info.metadata.get("folderIdPath")))

        scope_ids: set[str] = set()
        for fp in folder_id_paths:
            scope_ids_list = set(fp.replace("uniquepathid://", "").split("/"))
            scope_ids.update(scope_ids_list)

        scope_id_to_folder_name: dict[str, str] = {}
        for scope_id in scope_ids:
            folder_info = self.get_folder_info(
                scope_id=scope_id,
            )
            scope_id_to_folder_name[scope_id] = folder_info.name

        folder_paths: set[str] = set()
        for folder_id_path in folder_id_paths:
            scope_ids_list = folder_id_path.replace("uniquepathid://", "").split("/")

            if all(scope_id in scope_id_to_folder_name for scope_id in scope_ids_list):
                folder_path = [
                    scope_id_to_folder_name[scope_id] for scope_id in scope_ids_list
                ]
                folder_paths.add("/".join(folder_path))

        return [
            p if p.startswith("/") else f"/{p}"
            for p in folder_paths.union(known_folder_paths)
        ]

    def resolve_visible_file_tree(
        self, *, metadata_filter: dict[str, Any] | None = None
    ) -> list[str]:
        """
        Resolves the visible file tree for the knowledge base for the current user.

        Args:
            metadata_filter (dict[str, Any] | None): The metadata filter to use. Defaults to None.

        Returns:
            list[str]: The visible file tree.



        """
        info = self.get_paginated_content_infos(
            metadata_filter=metadata_filter,
        )

        return self._resolve_visible_file_tree(content_infos=info.content_infos)

    def _pop_forbidden_metadata_keys(self, metadata: dict[str, Any]) -> dict[str, Any]:
        forbidden_keys = [
            "key",
            "url",
            "title",
            "folderId",
            "mimeType",
            "companyId",
            "contentId",
            "folderIdPath",
            "externalFileOwner",
        ]
        for key in forbidden_keys:
            metadata.pop(key, None)
        return metadata

    def update_content_metadata(
        self,
        *,
        content_info: ContentInfo,
        additional_metadata: dict[str, Any],
    ) -> ContentInfo:
        camelized_additional_metadata = humps.camelize(additional_metadata)
        camelized_additional_metadata = self._pop_forbidden_metadata_keys(
            camelized_additional_metadata
        )

        if content_info.metadata is not None:
            content_info.metadata.update(camelized_additional_metadata)
        else:
            content_info.metadata = camelized_additional_metadata

        return update_content(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_info.id,
            metadata=content_info.metadata,
        )

    def remove_content_metadata(
        self,
        *,
        content_info: ContentInfo,
        keys_to_remove: list[str],
    ) -> ContentInfo:
        """
        Removes the specified keys irreversibly from the content metadata.

        Note: Keys are camelized before being removed as metadata keys are stored in camelCase.
        """

        if content_info.metadata is None:
            _LOGGER.warning(f"Content metadata is None for content {content_info.id}")
            return content_info

        for key in keys_to_remove:
            content_info.metadata[humps.camelize(key)] = None

        return update_content(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_info.id,
            metadata=content_info.metadata or {},
        )

    @overload
    def update_contents_metadata(
        self,
        *,
        additional_metadata: dict[str, Any],
        content_infos: list[ContentInfo],
    ) -> list[ContentInfo]: ...

    @overload
    def update_contents_metadata(
        self, *, additional_metadata: dict[str, Any], metadata_filter: dict[str, Any]
    ) -> list[ContentInfo]: ...

    def update_contents_metadata(
        self,
        *,
        additional_metadata: dict[str, Any],
        metadata_filter: dict[str, Any] | None = None,
        content_infos: list[ContentInfo] | None = None,
    ) -> list[ContentInfo]:
        """Update the metadata of the contents matching the metadata filter.

        Note: Keys are camelized before being updated as metadata keys are stored in camelCase.
        """

        additional_metadata_camelized = humps.camelize(additional_metadata)
        additional_metadata_camelized = self._pop_forbidden_metadata_keys(
            additional_metadata_camelized
        )

        if content_infos is None:
            content_infos = self.get_paginated_content_infos(
                metadata_filter=metadata_filter,
            ).content_infos

        for info in content_infos:
            self.update_content_metadata(
                content_info=info, additional_metadata=additional_metadata_camelized
            )

        return content_infos

    @overload
    def remove_contents_metadata(
        self,
        *,
        keys_to_remove: list[str],
        content_infos: list[ContentInfo],
    ) -> list[ContentInfo]: ...

    @overload
    def remove_contents_metadata(
        self, *, keys_to_remove: list[str], metadata_filter: dict[str, Any]
    ) -> list[ContentInfo]: ...

    def remove_contents_metadata(
        self,
        *,
        keys_to_remove: list[str],
        metadata_filter: dict[str, Any] | None = None,
        content_infos: list[ContentInfo] | None = None,
    ) -> list[ContentInfo]:
        """Remove the specified keys irreversibly from the content metadata.

        Note: Keys are camelized before being removed as metadata keys are stored in camelCase.

        """

        if content_infos is None:
            content_infos = self.get_paginated_content_infos(
                metadata_filter=metadata_filter,
            ).content_infos

        for info in content_infos:
            self.remove_content_metadata(
                content_info=info, keys_to_remove=keys_to_remove
            )

        return content_infos

    @overload
    def delete_content(
        self,
        *,
        content_id: str,
    ) -> DeleteContentResponse: ...

    """Delete content by id"""

    @overload
    def delete_content(
        self,
        *,
        file_path: str,
    ) -> DeleteContentResponse: ...

    """Delete all content matching the file path"""

    def delete_content(
        self,
        *,
        content_id: str | None = None,
        file_path: str | None = None,
    ) -> DeleteContentResponse:
        """Delete content by id, file path or metadata filter"""

        return delete_content(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            file_path=file_path,
        )

    def delete_contents(
        self,
        *,
        metadata_filter: dict[str, Any],
    ) -> list[DeleteContentResponse]:
        """Delete all content matching the metadata filter"""
        resp: list[DeleteContentResponse] = []

        if metadata_filter:
            infos = self.get_paginated_content_infos(
                metadata_filter=metadata_filter,
            )

            for info in infos.content_infos:
                resp.append(
                    delete_content(
                        user_id=self._user_id,
                        company_id=self._company_id,
                        content_id=info.id,
                    )
                )

        return resp

    @overload
    async def delete_content_async(
        self,
        *,
        content_id: str,
    ) -> DeleteContentResponse: ...

    @overload
    async def delete_content_async(
        self,
        *,
        file_path: str,
    ) -> DeleteContentResponse: ...

    async def delete_content_async(
        self,
        *,
        content_id: str | None = None,
        file_path: str | None = None,
    ) -> DeleteContentResponse:
        return await delete_content_async(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            file_path=file_path,
        )

    async def delete_contents_async(
        self,
        *,
        metadata_filter: dict[str, Any],
    ) -> list[DeleteContentResponse]:
        """Delete all content matching the metadata filter"""
        if not metadata_filter:
            return []

        infos = self.get_paginated_content_infos(
            metadata_filter=metadata_filter,
        )

        # Create all delete tasks without awaiting them
        delete_tasks = [
            delete_content_async(
                user_id=self._user_id,
                company_id=self._company_id,
                content_id=info.id,
            )
            for info in infos.content_infos
        ]

        # Await all delete operations concurrently
        resp = await asyncio.gather(*delete_tasks)

        return list(resp)


if __name__ == "__main__":
    kb_service = KnowledgeBaseService.from_settings()

    kb_service.search_contents(where={"metadata.key": "123"})
    kb_service.search_content_chunks(
        search_string="test",
        search_type=ContentSearchType.VECTOR,
        limit=10,
        scope_ids=["123"],
        metadata_filter={"key": "123"},
    )
