import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, cast

import requests
import unique_sdk

from unique_toolkit._common._base_service import BaseService
from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentSearchType,
    ContentUploadInput,
    RerankerConfig,
)


class ContentService(BaseService):
    """
    Provides methods for searching, downloading and uploading content in the knowledge base.

    Attributes:
        state (ChatState): The chat state.
        logger (Optional[logging.Logger]): The logger. Defaults to None.
    """

    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        super().__init__(state, logger)

    DEFAULT_SEARCH_LANGUAGE = "english"

    def search_content_chunks(
        self,
        search_string: str,
        search_type: ContentSearchType,
        limit: int,
        search_language: str = DEFAULT_SEARCH_LANGUAGE,
        reranker_config: Optional[RerankerConfig] = None,
        scope_ids: Optional[list[str]] = [],
        chat_only: Optional[bool] = None,
    ) -> list[ContentChunk]:
        """
        Performs a synchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str): The language for the full-text search. Defaults to "english".
            reranker_config (Optional[RerankerConfig]): The reranker configuration. Defaults to None.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to None.
            chat_only (Optional[bool]): Whether to search only in the current chat. Defaults to None.

        Returns:
            list[ContentChunk]: The search results.
        """
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
                reranker=reranker_config,  # type: ignore
                language=search_language,  # type: ignore
                chatOnly=chat_only,
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
        reranker_config: Optional[RerankerConfig] = None,
        scope_ids: Optional[list[str]] = [],
        chat_only: Optional[bool] = None,
    ):
        """
        Performs an asynchronous search for content chunks in the knowledge base.

        Args:
            search_string (str): The search string.
            search_type (ContentSearchType): The type of search to perform.
            limit (int): The maximum number of results to return.
            search_language (str): The language for the full-text search. Defaults to "english".
            reranker_config (Optional[RerankerConfig]): The reranker configuration. Defaults to None.
            scope_ids (Optional[list[str]]): The scope IDs. Defaults to [].
            chat_only (Optional[bool]): Whether to search only in the current chat. Defaults to None.

        Returns:
            list[ContentChunk]: The search results.
        """
        if not scope_ids:
            self.logger.warning("No scope IDs provided for search.")

        try:
            searches = await unique_sdk.Search.create_async(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
                searchString=search_string,
                searchType=search_type.name,
                scopeIds=scope_ids,
                limit=limit,
                # TODO fix types in SDK
                reranker=reranker_config.model_dump() if reranker_config else None,  # type: ignore
                language=search_language,  # type: ignore
                chatOnly=chat_only,
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
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
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
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
                # TODO add type parameter
                where=where,  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Error while searching contents: {e}")
            raise e

        return self._map_contents(contents)

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

        byte_size = os.path.getsize(path_to_content)
        created_content = self._trigger_upsert_content(
            input=ContentUploadInput(
                key=content_name, title=content_name, mime_type=mime_type
            ),
            scope_id=scope_id,
            chat_id=chat_id,
        )

        write_url = created_content.write_url

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

        read_url = created_content.read_url

        if not read_url:
            error_msg = "Read url for uploaded content is missing"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        if chat_id:
            self._trigger_upsert_content(
                input=ContentUploadInput(
                    key=content_name,
                    title=content_name,
                    mime_type=mime_type,
                    byte_size=byte_size,
                ),
                content_url=read_url,
                chat_id=chat_id,
            )
        else:
            self._trigger_upsert_content(
                input=ContentUploadInput(
                    key=content_name,
                    title=content_name,
                    mime_type=mime_type,
                    byte_size=byte_size,
                ),
                content_url=read_url,
                scope_id=scope_id,
            )

        return created_content

    def _trigger_upsert_content(
        self,
        input: ContentUploadInput,
        scope_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        content_url: Optional[str] = None,
    ):
        if not chat_id and not scope_id:
            raise ValueError("chat_id or scope_id must be provided")

        try:
            if input.byte_size:
                input_json = {
                    "key": input.key,
                    "title": input.title,
                    "mimeType": input.mime_type,
                    "byteSize": input.byte_size,
                }
            else:
                input_json = {
                    "key": input.key,
                    "title": input.title,
                    "mimeType": input.mime_type,
                }
            content = unique_sdk.Content.upsert(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                input=input_json,  # type: ignore
                fileUrl=content_url,
                scopeId=scope_id,
                chatId=chat_id,
                sourceOwnerType=None,  # type: ignore
                storeInternally=False,
            )
            return Content(**content)
        except Exception as e:
            self.logger.error(f"Error while uploading content: {e}")
            raise e

    def download_content(
        self,
        content_id: str,
        content_name: str,
        chat_id: Optional[str] = None,
    ) -> Path:
        """
        Downloads content to temporary directory

        Args:
            content_id (str): The id of the uploaded content.
            content_name (str): The name of the uploaded content.
            chat_id (Optional[str]): The chat_id, defaults to None.

        Returns:
            content_path: The path to the downloaded content in the temporary directory.

        Raises:
            Exception: If the download fails.
        """

        url = f"{unique_sdk.api_base}/content/{content_id}/file"
        if chat_id:
            url = f"{url}?chatId={chat_id}"

        # Create a random directory inside /tmp
        random_dir = tempfile.mkdtemp(dir="/tmp")

        # Create the full file path
        content_path = Path(random_dir) / content_name

        # Download the file and save it to the random directory
        headers = {
            "x-api-version": unique_sdk.api_version,
            "x-app-id": unique_sdk.app_id,
            "x-user-id": self.state.user_id,
            "x-company-id": self.state.company_id,
            "Authorization": "Bearer %s" % (unique_sdk.api_key,),
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            with open(content_path, "wb") as file:
                file.write(response.content)
        else:
            error_msg = f"Error downloading file: Status code {response.status_code}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        return content_path
