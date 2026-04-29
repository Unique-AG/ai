"""Assistant briefing operations (``PUT /briefings/{assistantId}``).

Request and response shapes follow OpenAPI components ``UpsertBriefingRequest``
and ``Briefing``. Extend :class:`Briefing.UpsertForAssistantParams` if new body
fields are added to the public schema.
"""

from __future__ import annotations

from typing import Literal, Unpack, cast
from urllib.parse import quote_plus

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class Briefing(APIResource["Briefing"]):
    """Create or replace the briefing attached to an assistant."""

    @classproperty
    def OBJECT_NAME(cls) -> Literal["briefing"]:
        return "briefing"

    RESOURCE_URL = "/briefings"

    class UpsertForAssistantParams(RequestOptions):
        """HTTP body matching OpenAPI ``UpsertBriefingRequest``."""

        content: str

    id: str
    object: str
    assistantId: str
    content: str | None
    title: str | None
    createdAt: str | None
    updatedAt: str | None

    @classmethod
    def upsert_for_assistant(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
        **params: Unpack["Briefing.UpsertForAssistantParams"],
    ) -> "Briefing":
        """Upsert the briefing for ``assistant_id`` (external id = assistant id).

        Mirrors ``BriefingController_upsertForAssistant`` (
        ``PUT /briefings/{assistantId}``).
        """
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(assistant_id))
        return cast(
            "Briefing",
            cls._static_request("put", url, user_id, company_id, params),
        )

    @classmethod
    async def upsert_for_assistant_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
        **params: Unpack["Briefing.UpsertForAssistantParams"],
    ) -> "Briefing":
        """Async variant of :meth:`upsert_for_assistant`."""
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(assistant_id))
        return cast(
            "Briefing",
            await cls._static_request_async("put", url, user_id, company_id, params),
        )
