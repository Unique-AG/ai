from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict, Unpack, cast
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from unique_sdk._client import _BaseClient

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class Module(APIResource["Module"]):
    """An assistant module that configures behaviour, tools, and instructions.

    Modules are attached to assistants (spaces) and define their capabilities,
    configuration, and tool definitions.  They control weight/priority, whether
    the module is external, and whether custom instructions are enabled.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["module"]:
        return "module"

    RESOURCE_URL = "/modules"

    @classmethod
    def class_url(cls) -> str:
        return cls.RESOURCE_URL

    class ListParams(RequestOptions):
        assistantId: NotRequired[str | None]

    class CreateParams(RequestOptions):
        assistantId: str
        name: str
        description: NotRequired[str | None]
        weight: NotRequired[int | None]
        isExternal: NotRequired[bool | None]
        isCustomInstructionEnabled: NotRequired[bool | None]
        configuration: NotRequired[dict[str, Any] | None]
        toolDefinition: NotRequired[dict[str, Any] | None]
        moduleTemplateId: NotRequired[str | None]

    class ModifyParams(RequestOptions):
        name: NotRequired[str | None]
        description: NotRequired[str | None]
        weight: NotRequired[int | None]
        isExternal: NotRequired[bool | None]
        isCustomInstructionEnabled: NotRequired[bool | None]
        configuration: NotRequired[dict[str, Any] | None]
        toolDefinition: NotRequired[dict[str, Any] | None]

    class DeletedObject(TypedDict):
        id: str
        object: str
        deleted: bool

    id: str
    name: str
    description: str | None
    toolDefinition: dict[str, Any] | None
    configuration: dict[str, Any] | None
    assistantId: str
    weight: int | None
    isExternal: bool
    isCustomInstructionEnabled: bool
    moduleTemplateId: str | None
    createdAt: str
    updatedAt: str

    @classmethod
    def list(
        cls,
        *,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Module.ListParams"],
    ) -> builtins.list["Module"]:
        result = cls._static_request(
            "get",
            cls.RESOURCE_URL,
            user_id,
            company_id,
            params or None,
            client=client,
        )
        if isinstance(result, builtins.list):
            data = result
        else:
            data = result.get("data", []) if hasattr(result, "get") else []
        return cast(builtins.list["Module"], data)

    @classmethod
    async def list_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Module.ListParams"],
    ) -> builtins.list["Module"]:
        result = await cls._static_request_async(
            "get",
            cls.RESOURCE_URL,
            user_id,
            company_id,
            params or None,
            client=client,
        )
        if isinstance(result, builtins.list):
            data = result
        else:
            data = result.get("data", []) if hasattr(result, "get") else []
        return cast(builtins.list["Module"], data)

    @classmethod
    def retrieve(
        cls,
        *,
        user_id: str,
        company_id: str,
        id: str,
        client: "_BaseClient | None" = None,
    ) -> "Module":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "Module",
            cls._static_request("get", url, user_id, company_id, client=client),
        )

    @classmethod
    async def retrieve_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        id: str,
        client: "_BaseClient | None" = None,
    ) -> "Module":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "Module",
            await cls._static_request_async(
                "get", url, user_id, company_id, client=client
            ),
        )

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Module.CreateParams"],
    ) -> "Module":
        return cast(
            "Module",
            cls._static_request(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
                client=client,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Module.CreateParams"],
    ) -> "Module":
        return cast(
            "Module",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
                client=client,
            ),
        )

    @classmethod
    def modify(
        cls,
        *,
        user_id: str,
        company_id: str,
        id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Module.ModifyParams"],
    ) -> "Module":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "Module",
            cls._static_request(
                "patch", url, user_id, company_id, params, client=client
            ),
        )

    @classmethod
    async def modify_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Module.ModifyParams"],
    ) -> "Module":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "Module",
            await cls._static_request_async(
                "patch", url, user_id, company_id, params, client=client
            ),
        )

    @classmethod
    def delete(
        cls,
        *,
        user_id: str,
        company_id: str,
        id: str,
        client: "_BaseClient | None" = None,
    ) -> "Module.DeletedObject":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "Module.DeletedObject",
            cls._static_request("delete", url, user_id, company_id, client=client),
        )

    @classmethod
    async def delete_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        id: str,
        client: "_BaseClient | None" = None,
    ) -> "Module.DeletedObject":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(id))
        return cast(
            "Module.DeletedObject",
            await cls._static_request_async(
                "delete", url, user_id, company_id, client=client
            ),
        )
