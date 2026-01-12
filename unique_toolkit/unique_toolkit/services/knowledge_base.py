import asyncio
import logging
import mimetypes
from dataclasses import dataclass, field
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Any, Callable, overload

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
    get_content_info_async,
    get_folder_info,
    get_folder_info_async,
    search_content_chunks,
    search_content_chunks_async,
    search_contents,
    search_contents_async,
    update_content,
    upload_content,
    upload_content_from_bytes,
    upload_content_from_bytes_async,
)
from unique_toolkit.content.schemas import (
    BaseFolderInfo,
    Content,
    ContentChunk,
    ContentInfo,
    ContentRerankerConfig,
    ContentSearchType,
    DeleteContentResponse,
    FolderInfo,
    PaginatedContentInfos,
)
from unique_toolkit.content.smart_rules import Operator, Statement

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

    # Content Search
    # ------------------------------------------------------------------------------------------------

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
        include_failed_content: bool = False,
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
            include_failed_content=include_failed_content,
        )

    async def search_contents_async(
        self,
        *,
        where: dict,
        include_failed_content: bool = False,
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
            include_failed_content=include_failed_content,
        )

    # Content Management
    # ------------------------------------------------------------------------------------------------

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

    async def upload_content_from_bytes_async(
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

        return await upload_content_from_bytes_async(
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
    ) -> Content:
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
    ) -> Path:
        """
        Downloads content from a chat and saves it to a file.

        Args:
            content_id (str): The ID of the content to download.
            output_filename (str | None): The name of the file to save the content as. If not provided, the original filename will be used. Defaults to None.
            output_dir_path (str | Path | None): The path to the temporary directory where the content will be saved. Defaults to "/tmp".

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

    def batch_file_upload(
        self,
        *,
        local_files: list[Path],
        remote_folders: list[PurePath],
        overwrite: bool = False,
        metadata_generator: Callable[[Path, PurePath], dict[str, Any]] | None = None,
    ) -> None:
        """
        Upload files to the knowledge base into corresponding folders

        Args:
            local_files (list[Path]): The local files to upload
            remote_folders (list[PurePath]): The remote folders to upload the files to
            overwrite (bool): Whether to overwrite existing files
            metadata_generator (Callable[[Path, PurePath], dict[str, Any]] | None): The metadata generator function

        Returns:
            None
        """

        if len(local_files) != len(remote_folders):
            raise ValueError(
                "The number of local files and remote folders must be the same"
            )

        creation_result = self.create_folders(paths=remote_folders)

        folders_path_to_scope_id = {
            folder_path: result.id
            for folder_path, result in zip(remote_folders, creation_result)
        }

        _old_scope_id = None
        _existing_file_names: list[str] = []

        for remote_folder_path, local_file_path in zip(remote_folders, local_files):
            scope_id = folders_path_to_scope_id[remote_folder_path]
            mime_type = mimetypes.guess_type(local_file_path.name)[0]

            if mime_type is None:
                _LOGGER.warning(
                    f"No mime type found for file {local_file_path.name}, skipping"
                )
                continue

            if not overwrite:
                if _old_scope_id is None or _old_scope_id != scope_id:
                    _LOGGER.debug(f"Switching to new folder {scope_id}")
                    _old_scope_id = scope_id
                    _existing_file_names = self.get_file_names_in_folder(
                        scope_id=scope_id
                    )

                if local_file_path.name in _existing_file_names:
                    _LOGGER.warning(
                        f"File {local_file_path.name} already exists in folder {scope_id}, skipping"
                    )
                    continue

            metadata = None
            if metadata_generator is not None:
                metadata = metadata_generator(local_file_path, remote_folder_path)

            self.upload_content(
                path_to_content=str(local_file_path),
                content_name=local_file_path.name,
                mime_type=mime_type,
                scope_id=scope_id,
                metadata=metadata,
            )

    # Content Information
    # ------------------------------------------------------------------------------------------------
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

    async def get_paginated_content_infos_async(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
        skip: int | None = None,
        take: int | None = None,
        file_path: str | None = None,
    ) -> PaginatedContentInfos:
        return await get_content_info_async(
            user_id=self._user_id,
            company_id=self._company_id,
            metadata_filter=metadata_filter,
            skip=skip,
            take=take,
            file_path=file_path,
        )

    def get_file_names_in_folder(self, *, scope_id: str) -> list[str]:
        """
        Get the list of file names in a knowledge base folder

        Args:
            scope_id (str): The scope id of the folder

        Returns:
            list[str]: The list of file names in the folder
        """
        smart_rule = Statement(
            operator=Operator.EQUALS, value=scope_id, path=["folderId"]
        )
        infos = self.get_paginated_content_infos(
            metadata_filter=smart_rule.model_dump(mode="json")
        )
        return [i.key for i in infos.content_infos]

    # Folder Management
    # ------------------------------------------------------------------------------------------------

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

    async def get_folder_info_async(
        self,
        *,
        scope_id: str,
    ) -> FolderInfo:
        return await get_folder_info_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
        )

    async def _translate_scope_ids_to_folder_name_async(
        self, scope_ids: set[str]
    ) -> dict[str, str]:
        async def translation(scope_id: str) -> tuple[str, str]:
            folder_info = await self.get_folder_info_async(scope_id=scope_id)
            return (scope_id, folder_info.name)

        return dict(await asyncio.gather(*[translation(sid) for sid in scope_ids]))

    @staticmethod
    def extract_folder_metadata_from_content_infos(
        content_infos: list[ContentInfo],
    ) -> tuple[set[str], set[str], set[str]]:
        """
        Extracts folder metadata from content infos.

        This extracts three types of folder information:
        - scope_ids: Individual IDs extracted from `folderIdPath` that need to be translated via API
        - folder_id_paths: Raw `folderIdPath` values (e.g., `uniquepathid://abc/def`)
        - known_folder_paths: Already resolved paths from `{FullPath}` metadata

        Args:
            content_infos (list[ContentInfo]): The list of content infos to extract from.

        Returns:
            tuple[set[str], set[str], set[str]]: A tuple of (scope_ids, folder_id_paths, known_folder_paths).
        """
        scope_ids: set[str] = set()
        folder_id_paths: set[str] = set()
        known_folder_paths: set[str] = set()

        for content_info in content_infos:
            if content_info.metadata is None:
                continue

            # Check for already resolved {FullPath}
            if content_info.metadata.get(r"{FullPath}") is not None:
                known_folder_paths.add(str(content_info.metadata.get(r"{FullPath}")))
                continue

            # Extract scope IDs from folderIdPath
            if content_info.metadata.get("folderIdPath") is not None:
                folder_id_path = str(content_info.metadata.get("folderIdPath"))
                folder_id_paths.add(folder_id_path)
                scope_ids_list = folder_id_path.replace("uniquepathid://", "").split(
                    "/"
                )
                scope_ids.update(scope_ids_list)

        return scope_ids, folder_id_paths, known_folder_paths

    async def get_content_infos_async(
        self, *, metadata_filter: dict[str, Any] | None = None
    ) -> list[ContentInfo]:
        """It is not possible to fetch all content infos at once, so we need to fetch them in chunks.
        We fetch the total count of content infos first, and then fetch them in chunks.
        We do this because the API has a limit (100) on the number of content infos that can be fetched at once.
        """

        info_for_count_of_total_content = await self.get_paginated_content_infos_async(
            metadata_filter=metadata_filter,
            take=1,
        )

        total_count = info_for_count_of_total_content.total_count

        step_size = 100

        results: list[PaginatedContentInfos | BaseException] = await asyncio.gather(
            *[
                self.get_paginated_content_infos_async(
                    metadata_filter=metadata_filter,
                    skip=i,
                    take=step_size,
                )
                for i in range(0, total_count, step_size)
            ],
            return_exceptions=True,
        )

        # Log any exceptions that occurred during parallel fetching
        for result in results:
            if isinstance(result, BaseException):
                _LOGGER.error(f"Error fetching paginated content infos: {result}")

        return [
            content_info
            for result in results
            if not isinstance(result, BaseException)
            for content_info in result.content_infos
        ]

    async def resolve_visible_folder_tree_async(
        self, *, metadata_filter: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Resolves the visible file tree for the knowledge base for the current user including files in a hierarchical folder tree strcture.

        Args:
            metadata_filter (dict[str, Any] | None): The metadata filter to use. Defaults to None.

        Returns:
            dict[str, Any]: The visible file tree.


        """

        content_infos: list[ContentInfo] = await self.get_content_infos_async(
            metadata_filter=metadata_filter
        )

        # collect all scope ids
        scope_ids, _, _ = self.extract_folder_metadata_from_content_infos(content_infos)

        scope_id_to_folder_name: dict[
            str, str
        ] = await self._translate_scope_ids_to_folder_name_async(scope_ids)

        @dataclass
        class Folder:
            files: list[str] = field(default_factory=list)
            folders: dict[str, "Folder"] = field(default_factory=dict)

            def to_dict(self) -> dict:
                return {
                    "files": self.files,
                    "folders": {
                        name: folder.to_dict() for name, folder in self.folders.items()
                    },
                }

        tree = Folder()

        for content_info in content_infos:
            current = tree
            metadata = content_info.metadata
            path: list[str]
            if metadata and (full_path := metadata.get(r"{FullPath}")) is not None:
                path = str(full_path).split("/")
            elif (
                metadata
                and (folder_id_path := metadata.get("folderIdPath")) is not None
            ):
                scope_ids_list = (
                    str(folder_id_path).replace("uniquepathid://", "").split("/")
                )
                path = [
                    scope_id_to_folder_name[scope_id] for scope_id in scope_ids_list
                ]
            else:
                continue
            for folder_name in path:
                if not folder_name:  # Skip empty folder names (e.g., from leading "/")
                    continue
                current = current.folders.setdefault(folder_name, Folder())
            current.files.append(content_info.key)

        return tree.to_dict()

    async def resolve_visible_files_async(
        self, *, metadata_filter: dict[str, Any] | None = None
    ) -> list[str]:
        """
        Resolves all visible file names in the knowledge base for the current user.

        Args:
            metadata_filter (dict[str, Any] | None): The metadata filter to use. Defaults to None.

        Returns:
            list[str]: List of file names (keys) visible to the user.
        """
        content_infos: list[ContentInfo] = await self.get_content_infos_async(
            metadata_filter=metadata_filter
        )
        return [content_info.key for content_info in content_infos]

    async def resolve_visible_folder_paths_async(
        self, *, metadata_filter: dict[str, Any] | None = None
    ) -> list[str]:
        """
        Resolves the visible file tree structure (only the folder paths - excluding files)
        for the knowledge base of the current user.

        Args:
            metadata_filter (dict[str, Any] | None): The metadata filter to use. Defaults to None.

        Returns:
            list[str]: List of folder paths visible to the user.
        """

        content_infos: list[ContentInfo] = await self.get_content_infos_async(
            metadata_filter=metadata_filter
        )

        scope_ids, folder_id_paths, known_folder_paths = (
            self.extract_folder_metadata_from_content_infos(content_infos)
        )

        scope_id_to_folder_name: dict[
            str, str
        ] = await self._translate_scope_ids_to_folder_name_async(scope_ids)

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

    def create_folders(self, *, paths: list[PurePath]) -> list[BaseFolderInfo]:
        """
        Create folders in the knowledge base if the path does not exists.

        Args:
            paths (list[PurePath]): The paths to create the folders at

        Returns:
            list[BaseFolderInfo]: The information about the created folders or existing folders
        """
        result = unique_sdk.Folder.create_paths(
            user_id=self._user_id,
            company_id=self._company_id,
            paths=[path.as_posix() for path in paths],
        )
        return [
            BaseFolderInfo.model_validate(folder, by_alias=True, by_name=True)
            for folder in result["createdFolders"]
        ]

        # Metadata

    # Metadata Management
    # ------------------------------------------------------------------------------------------------

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

    # Delete
    # ------------------------------------------------------------------------------------------------

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

    def _get_knowledge_base_location(
        self, *, scope_id: str
    ) -> tuple[PurePath, list[str]]:
        """
        Get the path of a folder from a scope id.

        Args:
            scope_id (str): The scope id of the folder.

        Returns:
            PurePath: The path of the folder.
            list[str]: The list of scope ids from root to the folder.
        """

        list_of_folder_names: list[str] = []
        list_of_scope_ids: list[str] = []
        folder_info = self.get_folder_info(scope_id=scope_id)
        list_of_scope_ids.append(folder_info.id)
        if folder_info.parent_id is not None:
            list_of_folder_names.append(folder_info.name)
        else:
            return PurePath("/" + folder_info.name), list_of_scope_ids

        while folder_info.parent_id is not None:
            folder_info = self.get_folder_info(scope_id=folder_info.parent_id)
            list_of_folder_names.append(folder_info.name)

        list_of_scope_ids.reverse()
        return PurePath("/" + "/".join(list_of_folder_names[::-1])), list_of_scope_ids

    # Utility Functions
    # ------------------------------------------------------------------------------------------------

    def get_folder_path(self, *, scope_id: str) -> PurePath:
        """
        Get the path of a folder from a scope id.
        Args:
            scope_id (str): The scope id of the folder.

        Returns:
            PurePath: The path of the folder.
        """
        folder_path, _ = self._get_knowledge_base_location(scope_id=scope_id)
        return folder_path

    def get_scope_id_path(self, *, scope_id: str) -> list[str]:
        """
        Get the path of a folder from a scope id.
        Args:
            scope_id (str): The scope id of the folder.

        Returns:
            list[str]: The list of scope ids from root to the folder.
        """
        _, list_of_scope_ids = self._get_knowledge_base_location(scope_id=scope_id)
        return list_of_scope_ids


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
