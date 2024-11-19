import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Union, cast

import requests
import unique_sdk

from unique_toolkit._common._base_service import BaseService
from unique_toolkit.app.schemas import Event
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentRerankerConfig,
    ContentSearchType,
)


class ContentService(BaseService):
    """
    Provides methods for searching, downloading and uploading content in the knowledge base.

    Attributes:
        event (Event): The Event object.
        logger (Optional[logging.Logger]): The logger. Defaults to None.
    """

    def __init__(self, event: Event, logger: Optional[logging.Logger] = None):
        super().__init__(event, logger)

    DEFAULT_SEARCH_LANGUAGE = "english"

    def search_content_chunks(
        self,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: Optional[ContentRerankerConfig] = None,
        scope_ids: Optional[list[str]] = None,
        chat_only: Optional[bool] = None,
        metadata_filter: Optional[dict] = None,
    ) -> list[ContentChunk]:
        """
        Performs a synchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str): The language for the full-text search. Defaults to "english".
            reranker_config (Optional[ContentRerankerConfig]): The reranker configuration. Defaults to None.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to None.
            chat_only (Optional[bool]): Whether to search only in the current chat. Defaults to None.
            metadata_filter (Optional[dict]): UniqueQL metadata filter. Defaults to None.

        Returns:
            list[ContentChunk]: The search results.
        """
        if not scope_ids:
            self.logger.warning("No scope IDs provided for search.")

        try:
            searches = unique_sdk.Search.create(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                chatId=self.event.payload.chat_id,
                searchString=search_string,
                searchType=search_type.name,
                scopeIds=scope_ids,
                limit=limit,
                reranker=(
                    reranker_config.model_dump(by_alias=True)
                    if reranker_config
                    else None
                ),
                language=search_language,
                chatOnly=chat_only,
                metaDataFilter=metadata_filter,
            )
        except Exception as e:
            self.logger.error(f"Error while searching content chunks: {e}")
            raise e

        def map_to_content_chunks(searches: list[unique_sdk.Search]):
            return [ContentChunk(**search) for search in searches]

        # TODO change return type in sdk from Search to list[Search]
        searches = cast(list[unique_sdk.Search], searches)
        return map_to_content_chunks(searches)

    async def search_content_chunks_async(
        self,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: Optional[ContentRerankerConfig] = None,
        scope_ids: Optional[list[str]] = None,
        chat_only: Optional[bool] = None,
        metadata_filter: Optional[dict] = None,
    ):
        """
        Performs an asynchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str): The language for the full-text search. Defaults to "english".
            reranker_config (Optional[ContentRerankerConfig]): The reranker configuration. Defaults to None.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to None.
            chat_only (Optional[bool]): Whether to search only in the current chat. Defaults to None.
            metadata_filter (Optional[dict]): UniqueQL metadata filter. Defaults to None.

        Returns:
            list[ContentChunk]: The search results.
        """
        if not scope_ids:
            self.logger.warning("No scope IDs provided for search.")

        try:
            searches = await unique_sdk.Search.create_async(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                chatId=self.event.payload.chat_id,
                searchString=search_string,
                searchType=search_type.name,
                scopeIds=scope_ids,
                limit=limit,
                reranker=(
                    reranker_config.model_dump(by_alias=True)
                    if reranker_config
                    else None
                ),
                language=search_language,
                chatOnly=chat_only,
                metaDataFilter=metadata_filter,
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
        try:
            contents = unique_sdk.Content.search(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                chatId=self.event.payload.chat_id,
                # TODO add type parameter
                where=where,  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Error while searching contents: {e}")
            raise e

        return self._map_contents(contents)

    async def search_contents_async(
        self,
        where: dict,
    ) -> list[Content]:
        """
        Performs an asynchronous search for content files in the knowledge base by filter.

        Args:
            where (dict): The search criteria.

        Returns:
            list[Content]: The search results.
        """
        try:
            contents = await unique_sdk.Content.search_async(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                chatId=self.event.payload.chat_id,
                # TODO add type parameter
                where=where,  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Error while searching contents: {e}")
            raise e

        return self._map_contents(contents)

    def search_content_on_chat(
        self,
    ) -> list[Content]:
        where = {"ownerId": {"equals": self.event.payload.chat_id}}

        return self.search_contents(where)

    @staticmethod
    def _map_content_chunk(content_chunk: dict):
        return ContentChunk(
            id=content_chunk["id"],
            text=content_chunk["text"],
            start_page=content_chunk["startPage"],
            end_page=content_chunk["endPage"],
            order=content_chunk["order"],
        )

    def _map_content(self, content: dict):
        return Content(
            id=content["id"],
            key=content["key"],
            title=content["title"],
            url=content["url"],
            chunks=[self._map_content_chunk(chunk) for chunk in content["chunks"]],
            created_at=content["createdAt"],
            updated_at=content["updatedAt"],
        )

    def _map_contents(self, contents):
        return [self._map_content(content) for content in contents]

    def upload_content(
        self,
        path_to_content: str,
        content_name: str,
        mime_type: str,
        scope_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        skip_ingestion: Optional[bool] = False,
    ):
        """
        Uploads content to the knowledge base.

        Args:
            path_to_content (str): The path to the content to upload.
            content_name (str): The name of the content.
            mime_type (str): The MIME type of the content.
            scope_id (Optional[str]): The scope ID. Defaults to None.
            chat_id (Optional[str]): The chat ID. Defaults to None.

        Returns:
            Content: The uploaded content.
        """

        try:
            return self._trigger_upload_content(
                path_to_content=path_to_content,
                content_name=content_name,
                mime_type=mime_type,
                scope_id=scope_id,
                chat_id=chat_id,
                skip_ingestion=skip_ingestion,
            )
        except Exception as e:
            self.logger.error(f"Error while uploading content: {e}")
            raise e

    def _trigger_upload_content(
        self,
        path_to_content: str,
        content_name: str,
        mime_type: str,
        scope_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        skip_ingestion: Optional[bool] = False,
    ):
        if not chat_id and not scope_id:
            raise ValueError("chat_id or scope_id must be provided")

        byte_size = os.path.getsize(path_to_content)
        created_content = unique_sdk.Content.upsert(
            user_id=self.event.user_id,
            company_id=self.event.company_id,
            input={
                "key": content_name,
                "title": content_name,
                "mimeType": mime_type,
            },
            scopeId=scope_id,
            chatId=chat_id,
        )  # type: ignore

        write_url = created_content["writeUrl"]

        if not write_url:
            error_msg = "Write url for uploaded content is missing"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # upload to azure blob storage SAS url uploadUrl the pdf file translatedFile make sure it is treated as a application/pdf
        with open(path_to_content, "rb") as file:
            requests.put(
                url=write_url,
                data=file,
                headers={
                    "X-Ms-Blob-Content-Type": mime_type,
                    "X-Ms-Blob-Type": "BlockBlob",
                },
            )

        read_url = created_content["readUrl"]

        if not read_url:
            error_msg = "Read url for uploaded content is missing"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        input_dict = {
            "key": content_name,
            "title": content_name,
            "mimeType": mime_type,
            "byteSize": byte_size,
        }

        if skip_ingestion:
            input_dict["ingestionConfig"] = {"uniqueIngestionMode": "SKIP_INGESTION"}

        if chat_id:
            unique_sdk.Content.upsert(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                input=input_dict,
                fileUrl=read_url,
                chatId=chat_id,
            )  # type: ignore
        else:
            unique_sdk.Content.upsert(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                input=input_dict,
                fileUrl=read_url,
                scopeId=scope_id,
            )  # type: ignore

        return Content(**created_content)

    def request_content_by_id(
        self, content_id: str, chat_id: str | None
    ) -> requests.Response:
        """
        Sends a request to download content from a chat.

        Args:
            content_id (str): The ID of the content to download.
            chat_id (str): The ID of the chat from which to download the content. Defaults to None to download from knowledge base.

        Returns:
            requests.Response: The response object containing the downloaded content.

        """
        url = f"{unique_sdk.api_base}/content/{content_id}/file"
        if chat_id:
            url = f"{url}?chatId={chat_id}"

        # Download the file and save it to the random directory
        headers = {
            "x-api-version": unique_sdk.api_version,
            "x-app-id": unique_sdk.app_id,
            "x-user-id": self.event.user_id,
            "x-company-id": self.event.company_id,
            "Authorization": "Bearer %s" % (unique_sdk.api_key,),
        }

        return requests.get(url, headers=headers)

    def download_content_to_file_by_id(
        self,
        content_id: str,
        chat_id: Optional[str] = None,
        filename: str | None = None,
        tmp_dir_path: Optional[Union[str, Path]] = "/tmp",
    ):
        """
        Downloads content from a chat and saves it to a file.

        Args:
            content_id (str): The ID of the content to download.
            chat_id (Optional[str]): The ID of the chat to download from. Defaults to None and the file is downloaded from the knowledge base.
            filename (str | None): The name of the file to save the content as. If not provided, the original filename will be used. Defaults to None.
            tmp_dir_path (Optional[Union[str, Path]]): The path to the temporary directory where the content will be saved. Defaults to "/tmp".

        Returns:
            Path: The path to the downloaded file.

        Raises:
            Exception: If the download fails or the filename cannot be determined.
        """

        response = self.request_content_by_id(content_id, chat_id)
        random_dir = tempfile.mkdtemp(dir=tmp_dir_path)

        if response.status_code == 200:
            if filename:
                content_path = Path(random_dir) / filename
            else:
                pattern = r'filename="([^"]+)"'
                match = re.search(
                    pattern, response.headers.get("Content-Disposition", "")
                )
                if match:
                    content_path = Path(random_dir) / match.group(1)
                else:
                    error_msg = (
                        "Error downloading file: Filename could not be determined"
                    )
                    self.logger.error(error_msg)
                    raise Exception(error_msg)

            with open(content_path, "wb") as file:
                file.write(response.content)
        else:
            error_msg = f"Error downloading file: Status code {response.status_code}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        return content_path

    # TODO: Discuss if we should deprecate this method due to unclear use by content_name
    def download_content(
        self,
        content_id: str,
        content_name: str,
        chat_id: Optional[str] = None,
        dir_path: Optional[Union[str, Path]] = "/tmp",
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

        response = self.request_content_by_id(content_id, chat_id)

        random_dir = tempfile.mkdtemp(dir=dir_path)
        content_path = Path(random_dir) / content_name

        if response.status_code == 200:
            with open(content_path, "wb") as file:
                file.write(response.content)
        else:
            error_msg = f"Error downloading file: Status code {response.status_code}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        return content_path
