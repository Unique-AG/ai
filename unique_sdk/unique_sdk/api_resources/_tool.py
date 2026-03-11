"""Tool persistence API. Backend stores tool data in a single table (MessageTool) with type + jsonb payload."""

from typing import (
    Any,
    ClassVar,
    Literal,
    NotRequired,
    TypedDict,
    Unpack,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._list_object import ListObject
from unique_sdk._request_options import RequestOptions


class ToolResponse(TypedDict):
    content: NotRequired[str | None]


class ToolItem(TypedDict):
    externalToolCallId: str
    functionName: str
    arguments: NotRequired[dict[str, Any] | None]
    roundIndex: int
    sequenceIndex: int
    response: NotRequired[ToolResponse | None]


# Max messageIds per GET request (monorepo API limit); we paginate above this.
_MESSAGE_IDS_PAGE_SIZE = 200


def _chunk_message_ids(message_ids_str: str) -> list[str]:
    """Split comma-separated message IDs into chunks of at most _MESSAGE_IDS_PAGE_SIZE."""
    ids = [s.strip() for s in message_ids_str.split(",") if s.strip()]
    chunks: list[str] = []
    for i in range(0, len(ids), _MESSAGE_IDS_PAGE_SIZE):
        chunks.append(",".join(ids[i : i + _MESSAGE_IDS_PAGE_SIZE]))
    return chunks


class Tool(APIResource["Tool"]):
    OBJECT_NAME: ClassVar[Literal["tool"]] = "tool"
    RESOURCE_URL = "/messages/tools"

    class CreateParams(RequestOptions):
        messageId: str
        tools: list[ToolItem]

    class ListParams(RequestOptions):
        messageIds: str

    id: str
    externalToolCallId: str
    functionName: str
    arguments: dict[str, Any] | None
    roundIndex: int
    sequenceIndex: int
    messageId: str
    response: dict[str, Any] | None
    createdAt: str

    @classmethod
    def create_many(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Tool.CreateParams"],
    ) -> ListObject["Tool"]:
        result = cls._static_request(
            "post",
            cls.RESOURCE_URL,
            user_id,
            company_id,
            params=params,
        )

        if not isinstance(result, ListObject):
            raise TypeError(
                "Expected list object from API, got %s" % (type(result).__name__)
            )

        return result

    @classmethod
    async def create_many_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Tool.CreateParams"],
    ) -> ListObject["Tool"]:
        result = await cls._static_request_async(
            "post",
            cls.RESOURCE_URL,
            user_id,
            company_id,
            params=params,
        )

        if not isinstance(result, ListObject):
            raise TypeError(
                "Expected list object from API, got %s" % (type(result).__name__)
            )

        return result

    @classmethod
    def list(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Tool.ListParams"],
    ) -> ListObject["Tool"]:
        message_ids_str = params.get("messageIds") or ""
        chunks = _chunk_message_ids(message_ids_str)
        if not chunks:
            return ListObject.construct_from(
                {"data": [], "has_more": False, "url": cls.RESOURCE_URL},
                user_id=user_id,
                company_id=company_id,
                last_response=None,
            )
        if len(chunks) == 1:
            result = cls._static_request(
                "get",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params={**params, "messageIds": chunks[0]},
            )
            if not isinstance(result, ListObject):
                raise TypeError(
                    "Expected list object from API, got %s" % (type(result).__name__)
                )
            return result
        all_data: list[Any] = []
        for chunk in chunks:
            page = cls._static_request(
                "get",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params={**params, "messageIds": chunk},
            )
            if not isinstance(page, ListObject):
                raise TypeError(
                    "Expected list object from API, got %s" % (type(page).__name__)
                )
            all_data.extend(page.get("data", []))
        return ListObject.construct_from(
            {
                "data": all_data,
                "has_more": False,
                "url": cls.RESOURCE_URL,
            },
            user_id=user_id,
            company_id=company_id,
            last_response=None,
        )

    @classmethod
    async def list_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Tool.ListParams"],
    ) -> ListObject["Tool"]:
        message_ids_str = params.get("messageIds") or ""
        chunks = _chunk_message_ids(message_ids_str)
        if not chunks:
            return ListObject.construct_from(
                {"data": [], "has_more": False, "url": cls.RESOURCE_URL},
                user_id=user_id,
                company_id=company_id,
                last_response=None,
            )
        if len(chunks) == 1:
            result = await cls._static_request_async(
                "get",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params={**params, "messageIds": chunks[0]},
            )
            if not isinstance(result, ListObject):
                raise TypeError(
                    "Expected list object from API, got %s" % (type(result).__name__)
                )
            return result
        all_data: list[Any] = []
        for chunk in chunks:
            page = await cls._static_request_async(
                "get",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params={**params, "messageIds": chunk},
            )
            if not isinstance(page, ListObject):
                raise TypeError(
                    "Expected list object from API, got %s" % (type(page).__name__)
                )
            all_data.extend(page.get("data", []))
        return ListObject.construct_from(
            {
                "data": all_data,
                "has_more": False,
                "url": cls.RESOURCE_URL,
            },
            user_id=user_id,
            company_id=company_id,
            last_response=None,
        )
