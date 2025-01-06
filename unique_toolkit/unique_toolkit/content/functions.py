import unique_sdk
from typing import Optional, Union


def create_search(
    user_id: str,
    company_id: str,
    chat_id: Optional[str],
    search_string: str,
    search_type: str,
    scope_ids: Optional[list[str]],
    limit: int,
    reranker: Optional[dict],
    language: str,
    chat_only: Optional[bool],
    metadata_filter: Optional[dict],
    content_ids: Optional[list[str]],
):
    """Creates a search in the knowledge base."""
    return unique_sdk.Search.create(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString=search_string,
        searchType=search_type,
        scopeIds=scope_ids,
        limit=limit,
        reranker=reranker,
        language=language,
        chatOnly=chat_only,
        metaDataFilter=metadata_filter,
        contentIds=content_ids,
    )


async def create_search_async(
    user_id: str,
    company_id: str,
    chat_id: Optional[str],
    search_string: str,
    search_type: str,
    scope_ids: Optional[list[str]],
    limit: int,
    reranker: Optional[dict],
    language: str,
    chat_only: Optional[bool],
    metadata_filter: Optional[dict],
    content_ids: Optional[list[str]],
):
    """Asynchronously creates a search in the knowledge base."""
    return await unique_sdk.Search.create_async(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        searchString=search_string,
        searchType=search_type,
        scopeIds=scope_ids,
        limit=limit,
        reranker=reranker,
        language=language,
        chatOnly=chat_only,
        metaDataFilter=metadata_filter,
        contentIds=content_ids,
    )


def search_content(user_id: str, company_id: str, chat_id: Optional[str], where: dict):
    """Searches for content in the knowledge base."""
    return unique_sdk.Content.search(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        where=where,
    )


async def search_content_async(
    user_id: str, company_id: str, chat_id: Optional[str], where: dict
):
    """Asynchronously searches for content in the knowledge base."""
    return await unique_sdk.Content.search_async(
        user_id=user_id,
        company_id=company_id,
        chatId=chat_id,
        where=where,
    )


def upsert_content(
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
    )
