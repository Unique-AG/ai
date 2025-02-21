import logging
import os
import re
import tempfile
from pathlib import Path

import requests
import unique_sdk

from unique_toolkit.content import DOMAIN_NAME
from unique_toolkit.content.constants import DEFAULT_SEARCH_LANGUAGE
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentRerankerConfig,
    ContentSearchType,
)
from unique_toolkit.content.utils import map_contents, map_to_content_chunks

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


def search_content_chunks(
    user_id: str,
    company_id: str,
    chat_id: str,
    search_string: str,
    search_type: ContentSearchType,
    limit: int,
    search_language: str = DEFAULT_SEARCH_LANGUAGE,
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
        search_language (str): The language for the full-text search. Defaults to "english".
        reranker_config (ContentRerankerConfig | None): The reranker configuration. Defaults to None.
        scope_ids (list[str] | None): The scope IDs. Defaults to None.
        chat_only (bool | None): Whether to search only in the current chat. Defaults to None.
        metadata_filter (dict | None): UniqueQL metadata filter. If unspecified/None, it tries to use the metadata filter from the event. Defaults to None.
        content_ids (list[str] | None): The content IDs to search. Defaults to None.
    Returns:
        list[ContentChunk]: The search results.
    """
    if not scope_ids:
        logger.warning("No scope IDs provided for search.")

    if content_ids:
        logger.info(f"Searching for content chunks with content_ids: {content_ids}")

    try:
        searches = unique_sdk.Search.create(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            searchString=search_string,
            searchType=search_type.name,
            scopeIds=scope_ids,
            limit=limit,
            reranker=(
                reranker_config.model_dump(by_alias=True) if reranker_config else None
            ),
            language=search_language,
            chatOnly=chat_only,
            metaDataFilter=metadata_filter,
            contentIds=content_ids,
        )
        return map_to_content_chunks(searches)
    except Exception as e:
        logger.error(f"Error while searching content chunks: {e}")
        raise e


async def search_content_chunks_async(
    user_id: str,
    company_id: str,
    chat_id: str,
    search_string: str,
    search_type: ContentSearchType,
    limit: int,
    search_language: str = DEFAULT_SEARCH_LANGUAGE,
    reranker_config: ContentRerankerConfig | None = None,
    scope_ids: list[str] | None = None,
    chat_only: bool | None = None,
    metadata_filter: dict | None = None,
    content_ids: list[str] | None = None,
):
    """
    Performs an asynchronous search for content chunks in the knowledge base.
    """
    if not scope_ids:
        logger.warning("No scope IDs provided for search.")

    if content_ids:
        logger.info(
            f"Searching for content chunks asynchronously with content_ids: {content_ids}"
        )

    try:
        searches = await unique_sdk.Search.create_async(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            searchString=search_string,
            searchType=search_type.name,
            scopeIds=scope_ids,
            limit=limit,
            reranker=(
                reranker_config.model_dump(by_alias=True) if reranker_config else None
            ),
            language=search_language,
            chatOnly=chat_only,
            metaDataFilter=metadata_filter,
            contentIds=content_ids,
        )
        return map_to_content_chunks(searches)
    except Exception as e:
        logger.error(f"Error while searching content chunks: {e}")
        raise e


def search_contents(
    user_id: str,
    company_id: str,
    chat_id: str,
    where: dict,
):
    """
    Performs an asynchronous search for content files in the knowledge base by filter.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        chat_id (str): The chat ID.
        where (dict): The search criteria.

    Returns:
        list[Content]: The search results.
    """
    if where.get("contentId"):
        logger.info(f"Searching for content with content_id: {where['contentId']}")

    try:
        contents = unique_sdk.Content.search(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            # TODO add type parameter in SDK
            where=where,  # type: ignore
        )
        return map_contents(contents)
    except Exception as e:
        logger.error(f"Error while searching contents: {e}")
        raise e


async def search_contents_async(
    user_id: str,
    company_id: str,
    chat_id: str,
    where: dict,
):
    """Asynchronously searches for content in the knowledge base."""
    if where.get("contentId"):
        logger.info(f"Searching for content with content_id: {where['contentId']}")

    try:
        contents = await unique_sdk.Content.search_async(
            user_id=user_id,
            company_id=company_id,
            chatId=chat_id,
            where=where,  # type: ignore
        )
        return map_contents(contents)
    except Exception as e:
        logger.error(f"Error while searching contents: {e}")
        raise e


def _upsert_content(
    user_id: str,
    company_id: str,
    input_data: dict,
    scope_id: str | None = None,
    chat_id: str | None = None,
    file_url: str | None = None,
):
    """Upserts content in the knowledge base."""
    return unique_sdk.Content.upsert(
        user_id=user_id,
        company_id=company_id,
        input=input_data,
        scopeId=scope_id,
        chatId=chat_id,
        fileUrl=file_url,
    )  # type: ignore


def upload_content(
    user_id: str,
    company_id: str,
    path_to_content: str,
    content_name: str,
    mime_type: str,
    scope_id: str | None = None,
    chat_id: str | None = None,
    skip_ingestion: bool = False,
):
    """
    Uploads content to the knowledge base.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        path_to_content (str): The path to the content to upload.
        content_name (str): The name of the content.
        mime_type (str): The MIME type of the content.
        scope_id (str | None): The scope ID. Defaults to None.
        chat_id (str | None): The chat ID. Defaults to None.
        skip_ingestion (bool): Whether to skip ingestion. Defaults to False.

    Returns:
        Content: The uploaded content.
    """

    try:
        return _trigger_upload_content(
            user_id=user_id,
            company_id=company_id,
            path_to_content=path_to_content,
            content_name=content_name,
            mime_type=mime_type,
            scope_id=scope_id,
            chat_id=chat_id,
            skip_ingestion=skip_ingestion,
        )
    except Exception as e:
        logger.error(f"Error while uploading content: {e}")
        raise e


def _trigger_upload_content(
    user_id: str,
    company_id: str,
    path_to_content: str,
    content_name: str,
    mime_type: str,
    scope_id: str | None = None,
    chat_id: str | None = None,
    skip_ingestion: bool = False,
):
    """
    Uploads content to the knowledge base.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        path_to_content (str): The path to the content to upload.
        content_name (str): The name of the content.
        mime_type (str): The MIME type of the content.
        scope_id (str | None): The scope ID. Defaults to None.
        chat_id (str | None): The chat ID. Defaults to None.
        skip_ingestion (bool): Whether to skip ingestion. Defaults to False.

    Returns:
        Content: The uploaded content.
    """

    if not chat_id and not scope_id:
        raise ValueError("chat_id or scope_id must be provided")

    byte_size = os.path.getsize(path_to_content)
    created_content = _upsert_content(
        user_id=user_id,
        company_id=company_id,
        input_data={
            "key": content_name,
            "title": content_name,
            "mimeType": mime_type,
        },
        scope_id=scope_id,
        chat_id=chat_id,
    )  # type: ignore

    write_url = created_content["writeUrl"]

    if not write_url:
        error_msg = "Write url for uploaded content is missing"
        logger.error(error_msg)
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
        logger.error(error_msg)
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
        _upsert_content(
            user_id=user_id,
            company_id=company_id,
            input_data=input_dict,
            file_url=read_url,
            chat_id=chat_id,
        )  # type: ignore
    else:
        _upsert_content(
            user_id=user_id,
            company_id=company_id,
            input_data=input_dict,
            file_url=read_url,
            scope_id=scope_id,
        )  # type: ignore

    return Content(**created_content)


def request_content_by_id(
    user_id: str, company_id: str, content_id: str, chat_id: str | None
) -> requests.Response:
    """
    Sends a request to download content from a chat.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        content_id (str): The ID of the content to download.
        chat_id (str): The ID of the chat from which to download the content. Defaults to None to download from knowledge base.

    Returns:
        requests.Response: The response object containing the downloaded content.

    """
    logger.info(f"Requesting content with content_id: {content_id}")
    url = f"{unique_sdk.api_base}/content/{content_id}/file"
    if chat_id:
        url = f"{url}?chatId={chat_id}"

    # Download the file and save it to the random directory
    headers = {
        "x-api-version": unique_sdk.api_version,
        "x-app-id": unique_sdk.app_id,
        "x-user-id": user_id,
        "x-company-id": company_id,
        "Authorization": "Bearer %s" % (unique_sdk.api_key,),
    }

    return requests.get(url, headers=headers)


def download_content_to_file_by_id(
    user_id: str,
    company_id: str,
    content_id: str,
    chat_id: str | None = None,
    filename: str | None = None,
    tmp_dir_path: str | Path | None = "/tmp",
):
    """
    Downloads content from a chat and saves it to a file.

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        content_id (str): The ID of the content to download.
        chat_id (str | None): The ID of the chat to download from. Defaults to None and the file is downloaded from the knowledge base.
        filename (str | None): The name of the file to save the content as. If not provided, the original filename will be used. Defaults to None.
        tmp_dir_path (str | Path | None): The path to the temporary directory where the content will be saved. Defaults to "/tmp".

    Returns:
        Path: The path to the downloaded file.

    Raises:
        Exception: If the download fails or the filename cannot be determined.
    """

    logger.info(f"Downloading content to file with content_id: {content_id}")
    response = request_content_by_id(user_id, company_id, content_id, chat_id)
    random_dir = tempfile.mkdtemp(dir=tmp_dir_path)

    if response.status_code == 200:
        if filename:
            content_path = Path(random_dir) / filename
        else:
            pattern = r'filename="([^"]+)"'
            match = re.search(pattern, response.headers.get("Content-Disposition", ""))
            if match:
                content_path = Path(random_dir) / match.group(1)
            else:
                error_msg = "Error downloading file: Filename could not be determined"
                logger.error(error_msg)
                raise Exception(error_msg)

        with open(content_path, "wb") as file:
            file.write(response.content)
    else:
        error_msg = f"Error downloading file: Status code {response.status_code}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return content_path


# TODO: Discuss if we should deprecate this method due to unclear use by content_name
def download_content(
    user_id: str,
    company_id: str,
    content_id: str,
    content_name: str,
    chat_id: str | None = None,
    dir_path: str | Path | None = "/tmp",
) -> Path:
    """
    Downloads content to temporary directory

    Args:
        user_id (str): The user ID.
        company_id (str): The company ID.
        content_id (str): The id of the uploaded content.
        content_name (str): The name of the uploaded content.
        chat_id (str | None): The chat_id, defaults to None.
        dir_path (str | Path): The directory path to download the content to, defaults to "/tmp". If not provided, the content will be downloaded to a random directory inside /tmp. Be aware that this directory won't be cleaned up automatically.

    Returns:
        content_path: The path to the downloaded content in the temporary directory.

    Raises:
        Exception: If the download fails.
    """

    logger.info(f"Downloading content with content_id: {content_id}")
    response = request_content_by_id(user_id, company_id, content_id, chat_id)

    random_dir = tempfile.mkdtemp(dir=dir_path)
    content_path = Path(random_dir) / content_name

    if response.status_code == 200:
        with open(content_path, "wb") as file:
            file.write(response.content)
    else:
        error_msg = f"Error downloading file: Status code {response.status_code}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return content_path
