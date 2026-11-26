"""Project chat search: find and read the earlier chats of a user's project.

Wraps the public endpoints under ``/search/project-chats``. Chats of a project
are indexed in chunks of consecutive question and answer pairs:

- ``POST /search/project-chats`` returns the chunks that best match a query.
- ``POST /search/project-chats/chunks`` returns the chunks of one chat in
  order, one page at a time.
- ``POST /search/project-chats/recent`` lists the chats of the project, most
  recently active first.

Only the project's owner can call them, and the Projects feature must be on
for the company. Search returns an empty list while project chat indexing is
off for the company.
"""

from datetime import datetime
from typing import Any, Literal, TypedDict, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._unique_object import UniqueObject
from unique_sdk._util import classproperty

_SEARCH_URL = "/search/project-chats"
_CHUNKS_URL = "/search/project-chats/chunks"
_RECENT_URL = "/search/project-chats/recent"


def _body(**fields: Any) -> dict[str, Any]:
    # Keyword-only fields: request options such as api_key or headers never
    # reach the body. None is left out so the endpoint applies its defaults.
    body: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        body[key] = value.isoformat() if isinstance(value, datetime) else value
    return body


class ProjectChatChunk(UniqueObject):
    """A chunk of an earlier project chat: consecutive question and answer pairs.

    Attributes:
        chatId (str): Chat the chunk belongs to.
        chatTitle (str | None): Title of the chat.
        chunkIndex (int): Position of the chunk in its chat, from 0.
        pairIndexStart (int): First question and answer pair in the chunk,
            from 1.
        pairIndexEnd (int): Last question and answer pair in the chunk.
        messageIds (list[str]): Messages in the chunk.
        text (str): Text of the chunk.
        tokenCount (int): Number of tokens in ``text``.
        isOpen (bool): ``True`` for the last chunk of the chat, which can
            still grow.
        createdAt (str): Time of the first message in the chunk, ISO 8601.
        updatedAt (str): Time of the last message in the chunk, ISO 8601.
        score (float | None): Relevance score. Set by search only.
        highlights (list[str] | None): Highlighted passages. Set by search
            only.
        object (Literal["search.project-chat-chunk"]): Object type identifier.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["search.project-chat-chunk"]:
        return "search.project-chat-chunk"

    chatId: str
    chatTitle: str | None
    chunkIndex: int
    pairIndexStart: int
    pairIndexEnd: int
    messageIds: list[str]
    text: str
    tokenCount: int
    isOpen: bool
    createdAt: str
    updatedAt: str
    score: float | None
    highlights: list[str] | None
    object: Literal["search.project-chat-chunk"]


class ProjectChat(APIResource["ProjectChat"]):
    """An earlier chat of a user's project, as listed by ``list_recent``.

    The class also holds the three project chat search calls: ``search``,
    ``list_chunks`` and ``list_recent``, each with an ``_async`` variant.

    Attributes:
        chatId (str): Chat identifier.
        chatTitle (str | None): Title of the chat.
        chatCreatedAt (str): Creation time of the chat, ISO 8601.
        updatedAt (str): Time of the last message, ISO 8601.
        chunkCount (int): Number of indexed chunks in the chat.
        object (Literal["search.project-chat"]): Object type identifier.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["search.project-chat"]:
        return "search.project-chat"

    class ChatStats(TypedDict):
        """Chunk and token totals of one chat.

        Attributes:
            chatId (str): Chat identifier.
            chunkCount (int): Number of chunks in the chat.
            tokenCount (int): Number of tokens in the chat.
        """

        chatId: str
        chunkCount: int
        tokenCount: int

    class ChunkList(TypedDict):
        """Response of ``search`` and ``list_chunks``.

        Attributes:
            object (Literal["list"]): Object type identifier.
            data (list[ProjectChatChunk]): The chunks.
            chatStats (list[ProjectChat.ChatStats]): Totals of the chats in
                ``data``. Empty unless ``include_chat_stats`` is set.
            nextCursor (str | None): Pass as ``after`` to get the next page.
                ``None`` on the last page and always for search.
        """

        object: Literal["list"]
        data: list[ProjectChatChunk]
        chatStats: list["ProjectChat.ChatStats"]
        nextCursor: str | None

    class ChatList(TypedDict):
        """Response of ``list_recent``.

        Attributes:
            object (Literal["list"]): Object type identifier.
            data (list[ProjectChat]): The chats, most recently active first.
            nextCursor (str | None): Pass as ``after`` to get the next page.
                ``None`` on the last page.
        """

        object: Literal["list"]
        data: list["ProjectChat"]
        nextCursor: str | None

    chatId: str
    chatTitle: str | None
    chatCreatedAt: str
    updatedAt: str
    chunkCount: int
    object: Literal["search.project-chat"]

    @staticmethod
    def _search_body(
        project_id: str,
        query: str,
        chat_ids: list[str] | None,
        exclude_chat_ids: list[str] | None,
        created_after: datetime | str | None,
        created_before: datetime | str | None,
        limit: int | None,
        include_chat_stats: bool | None,
    ) -> dict[str, Any]:
        return _body(
            projectId=project_id,
            query=query,
            chatIds=chat_ids,
            excludeChatIds=exclude_chat_ids,
            createdAfter=created_after,
            createdBefore=created_before,
            limit=limit,
            includeChatStats=include_chat_stats,
        )

    @staticmethod
    def _chunks_body(
        project_id: str,
        chat_id: str,
        limit: int | None,
        after: str | None,
        include_chat_stats: bool | None,
    ) -> dict[str, Any]:
        return _body(
            projectId=project_id,
            chatId=chat_id,
            limit=limit,
            after=after,
            includeChatStats=include_chat_stats,
        )

    @staticmethod
    def _recent_body(
        project_id: str,
        exclude_chat_ids: list[str] | None,
        updated_after: datetime | str | None,
        updated_before: datetime | str | None,
        limit: int | None,
        after: str | None,
    ) -> dict[str, Any]:
        return _body(
            projectId=project_id,
            excludeChatIds=exclude_chat_ids,
            updatedAfter=updated_after,
            updatedBefore=updated_before,
            limit=limit,
            after=after,
        )

    @classmethod
    def search(
        cls,
        user_id: str,
        company_id: str,
        *,
        project_id: str,
        query: str,
        chat_ids: list[str] | None = None,
        exclude_chat_ids: list[str] | None = None,
        created_after: datetime | str | None = None,
        created_before: datetime | str | None = None,
        limit: int | None = None,
        include_chat_stats: bool | None = None,
    ) -> "ProjectChat.ChunkList":
        """Search the earlier chats of a project the user owns.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project to search.
            query (str): What to look for, at most 2000 characters.
            chat_ids (list[str] | None): Only search these chats, at most 200.
            exclude_chat_ids (list[str] | None): Leave out these chats, at
                most 200, for example the current one.
            created_after (datetime | str | None): Only chunks whose first
                message is at or after this time. Use a timezone-aware
                datetime or an ISO 8601 string.
            created_before (datetime | str | None): Only chunks whose first
                message is at or before this time.
            limit (int | None): Number of chunks, 1 to 50. The endpoint
                defaults to 20.
            include_chat_stats (bool | None): Also return chunk and token
                totals of the chats in the result.

        Returns:
            ProjectChat.ChunkList: The best matching chunks, with ``score``
                and ``highlights`` set. ``nextCursor`` is always ``None``.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user (404), or a parameter is invalid (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: Projects are off for the company, or the user
                may not read chats (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectChat.ChunkList",
            cls._static_request(
                "post",
                _SEARCH_URL,
                user_id,
                company_id,
                params=cls._search_body(
                    project_id,
                    query,
                    chat_ids,
                    exclude_chat_ids,
                    created_after,
                    created_before,
                    limit,
                    include_chat_stats,
                ),
            ),
        )

    @classmethod
    async def search_async(
        cls,
        user_id: str,
        company_id: str,
        *,
        project_id: str,
        query: str,
        chat_ids: list[str] | None = None,
        exclude_chat_ids: list[str] | None = None,
        created_after: datetime | str | None = None,
        created_before: datetime | str | None = None,
        limit: int | None = None,
        include_chat_stats: bool | None = None,
    ) -> "ProjectChat.ChunkList":
        """Search the earlier chats of a project the user owns.

        See ``search`` for the arguments, return value and errors.
        """
        return cast(
            "ProjectChat.ChunkList",
            await cls._static_request_async(
                "post",
                _SEARCH_URL,
                user_id,
                company_id,
                params=cls._search_body(
                    project_id,
                    query,
                    chat_ids,
                    exclude_chat_ids,
                    created_after,
                    created_before,
                    limit,
                    include_chat_stats,
                ),
            ),
        )

    @classmethod
    def list_chunks(
        cls,
        user_id: str,
        company_id: str,
        *,
        project_id: str,
        chat_id: str,
        limit: int | None = None,
        after: str | None = None,
        include_chat_stats: bool | None = None,
    ) -> "ProjectChat.ChunkList":
        """Read one chat of a project the user owns, in order.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project of the chat.
            chat_id (str): The chat to read.
            limit (int | None): Number of chunks per page, 1 to 50. The
                endpoint defaults to 20.
            after (str | None): ``nextCursor`` of the previous page.
            include_chat_stats (bool | None): Also return the chunk and token
                totals of the chat.

        Returns:
            ProjectChat.ChunkList: One page of chunks, ordered by
                ``chunkIndex``. ``score`` and ``highlights`` are ``None``.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user (404), or a parameter is invalid (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: Projects are off for the company, or the user
                may not read chats (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectChat.ChunkList",
            cls._static_request(
                "post",
                _CHUNKS_URL,
                user_id,
                company_id,
                params=cls._chunks_body(
                    project_id, chat_id, limit, after, include_chat_stats
                ),
            ),
        )

    @classmethod
    async def list_chunks_async(
        cls,
        user_id: str,
        company_id: str,
        *,
        project_id: str,
        chat_id: str,
        limit: int | None = None,
        after: str | None = None,
        include_chat_stats: bool | None = None,
    ) -> "ProjectChat.ChunkList":
        """Read one chat of a project the user owns, in order.

        See ``list_chunks`` for the arguments, return value and errors.
        """
        return cast(
            "ProjectChat.ChunkList",
            await cls._static_request_async(
                "post",
                _CHUNKS_URL,
                user_id,
                company_id,
                params=cls._chunks_body(
                    project_id, chat_id, limit, after, include_chat_stats
                ),
            ),
        )

    @classmethod
    def list_recent(
        cls,
        user_id: str,
        company_id: str,
        *,
        project_id: str,
        exclude_chat_ids: list[str] | None = None,
        updated_after: datetime | str | None = None,
        updated_before: datetime | str | None = None,
        limit: int | None = None,
        after: str | None = None,
    ) -> "ProjectChat.ChatList":
        """List the chats of a project the user owns, most recently active first.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project to list.
            exclude_chat_ids (list[str] | None): Leave out these chats, at
                most 200.
            updated_after (datetime | str | None): Only chats active at or
                after this time. Use a timezone-aware datetime or an ISO 8601
                string.
            updated_before (datetime | str | None): Only chats last active at
                or before this time.
            limit (int | None): Number of chats per page, 1 to 20. The
                endpoint defaults to 20.
            after (str | None): ``nextCursor`` of the previous page.

        Returns:
            ProjectChat.ChatList: One page of chats.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user (404), or a parameter is invalid (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: Projects are off for the company, or the user
                may not read chats (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectChat.ChatList",
            cls._static_request(
                "post",
                _RECENT_URL,
                user_id,
                company_id,
                params=cls._recent_body(
                    project_id,
                    exclude_chat_ids,
                    updated_after,
                    updated_before,
                    limit,
                    after,
                ),
            ),
        )

    @classmethod
    async def list_recent_async(
        cls,
        user_id: str,
        company_id: str,
        *,
        project_id: str,
        exclude_chat_ids: list[str] | None = None,
        updated_after: datetime | str | None = None,
        updated_before: datetime | str | None = None,
        limit: int | None = None,
        after: str | None = None,
    ) -> "ProjectChat.ChatList":
        """List the chats of a project the user owns, most recently active first.

        See ``list_recent`` for the arguments, return value and errors.
        """
        return cast(
            "ProjectChat.ChatList",
            await cls._static_request_async(
                "post",
                _RECENT_URL,
                user_id,
                company_id,
                params=cls._recent_body(
                    project_id,
                    exclude_chat_ids,
                    updated_after,
                    updated_before,
                    limit,
                    after,
                ),
            ),
        )
