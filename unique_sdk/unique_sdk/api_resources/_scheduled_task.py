from __future__ import annotations

from typing import Literal, NotRequired, TypedDict, Unpack, cast
from urllib.parse import quote_plus

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class ScheduledTask(APIResource["ScheduledTask"]):
    """Cron-tab style scheduled task that triggers an assistant on a recurring schedule.

    Each task defines a cron expression, an assistant to execute, an optional
    chat to continue, and a prompt to send.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["scheduled_task"]:
        return "scheduled_task"

    RESOURCE_URL = "/scheduled-tasks"

    # -- Nested param types ------------------------------------------------

    class CreateParams(RequestOptions):
        cronExpression: str
        assistantId: str
        prompt: str
        chatId: NotRequired[str | None]
        enabled: NotRequired[bool]

    class ModifyParams(RequestOptions):
        cronExpression: NotRequired[str]
        assistantId: NotRequired[str]
        prompt: NotRequired[str]
        chatId: NotRequired[str | None]
        enabled: NotRequired[bool]

    class DeletedObject(TypedDict):
        id: str
        object: str
        deleted: bool

    # -- Instance fields (typing only) -------------------------------------

    id: str
    object: str
    cronExpression: str
    assistantId: str
    assistantName: str | None
    chatId: str | None
    prompt: str
    enabled: bool
    lastRunAt: str | None
    createdAt: str
    updatedAt: str

    # -- Class methods: sync -----------------------------------------------

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ScheduledTask.CreateParams"],
    ) -> "ScheduledTask":
        return cast(
            "ScheduledTask",
            cls._static_request(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    def list(
        cls,
        user_id: str,
        company_id: str,
    ) -> list["ScheduledTask"]:
        result = cls._static_request(
            "get",
            cls.RESOURCE_URL,
            user_id,
            company_id,
        )
        data = result.get("data", []) if hasattr(result, "get") else []
        return cast(list["ScheduledTask"], data)

    @classmethod
    def retrieve(
        cls,
        user_id: str,
        company_id: str,
        id: str,
    ) -> "ScheduledTask":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "ScheduledTask",
            cls._static_request(
                "get",
                url,
                user_id,
                company_id,
            ),
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["ScheduledTask.ModifyParams"],
    ) -> "ScheduledTask":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "ScheduledTask",
            cls._static_request(
                "patch",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    def delete(
        cls,
        user_id: str,
        company_id: str,
        id: str,
    ) -> "ScheduledTask.DeletedObject":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "ScheduledTask.DeletedObject",
            cls._static_request(
                "delete",
                url,
                user_id,
                company_id,
            ),
        )

    # -- Class methods: async ----------------------------------------------

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ScheduledTask.CreateParams"],
    ) -> "ScheduledTask":
        return cast(
            "ScheduledTask",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def list_async(
        cls,
        user_id: str,
        company_id: str,
    ) -> list["ScheduledTask"]:
        result = await cls._static_request_async(
            "get",
            cls.RESOURCE_URL,
            user_id,
            company_id,
        )
        data = result.get("data", []) if hasattr(result, "get") else []
        return cast(list["ScheduledTask"], data)

    @classmethod
    async def retrieve_async(
        cls,
        user_id: str,
        company_id: str,
        id: str,
    ) -> "ScheduledTask":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "ScheduledTask",
            await cls._static_request_async(
                "get",
                url,
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["ScheduledTask.ModifyParams"],
    ) -> "ScheduledTask":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "ScheduledTask",
            await cls._static_request_async(
                "patch",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        id: str,
    ) -> "ScheduledTask.DeletedObject":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "ScheduledTask.DeletedObject",
            await cls._static_request_async(
                "delete",
                url,
                user_id,
                company_id,
            ),
        )
