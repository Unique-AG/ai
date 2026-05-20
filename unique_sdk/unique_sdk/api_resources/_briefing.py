"""Assistant briefing operations on ``/briefings/{assistantId}``.

Request and response shapes follow OpenAPI ``UpsertBriefingRequestDto`` and
``BriefingDto``. See :class:`Briefing.UpsertForAssistantParams`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, TypedDict, Unpack, cast
from urllib.parse import quote_plus

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty

_MAX_TEXT_LEN = 4000
_MAX_TITLE_LEN = 100
_MAX_PROMPTS = 200
_MAX_PROMPT_TITLE_LEN = 100
_MAX_PROMPT_BODY_LEN = 4000
_REQUEST_OPTION_KEYS = frozenset({"api_key", "api_base", "headers"})


def _utc_iso8601_now() -> str:
    """UTC instant as ISO 8601 with ``Z`` suffix (common interchange format)."""

    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_prompts(raw: Any) -> list[dict[str, str]]:
    """Normalize ``prompts`` for ``UpsertBriefingRequestDto`` (max 200 items)."""
    if raw is None:
        raise ValueError(
            "Briefing upsert requires prompts= — a list of up to "
            f"{_MAX_PROMPTS} objects with title and body (OpenAPI "
            "UpsertBriefingRequestDto). Use [] to clear prompts."
        )
    if not isinstance(raw, list):
        raise TypeError(f"prompts must be a list, got {type(raw)!r}")
    if len(raw) > _MAX_PROMPTS:
        raise ValueError(
            f"prompts must have at most {_MAX_PROMPTS} items (got {len(raw)})"
        )
    out: list[dict[str, str]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise TypeError(f"prompts[{i}] must be a mapping, got {type(item)!r}")
        title = item.get("title")
        body = item.get("body")
        if not isinstance(title, str) or not isinstance(body, str):
            raise TypeError(
                f"prompts[{i}] must have string title and body (got {type(title)!r}, {type(body)!r})"
            )
        if len(title) > _MAX_PROMPT_TITLE_LEN:
            raise ValueError(
                f"prompts[{i}].title must be at most {_MAX_PROMPT_TITLE_LEN} characters"
            )
        if len(body) > _MAX_PROMPT_BODY_LEN:
            raise ValueError(
                f"prompts[{i}].body must be at most {_MAX_PROMPT_BODY_LEN} characters"
            )
        out.append({"title": title, "body": body})
    return out


class _UpsertBriefingWire(TypedDict):
    """Exact JSON keys for ``PUT`` body (``UpsertBriefingRequestDto``)."""

    text: str
    generatedAt: str
    prompts: list[dict[str, str]]
    title: NotRequired[str]


class Briefing(APIResource["Briefing"]):
    """Read, upsert, or detach the briefing attached to an assistant."""

    @classproperty
    def OBJECT_NAME(cls) -> Literal["briefing"]:
        return "briefing"

    RESOURCE_URL = "/briefings"

    class BriefingPromptItem(TypedDict):
        """One entry in ``prompts`` (``PromptItemDto``)."""

        title: str
        body: str

    class UpsertForAssistantParams(RequestOptions):
        """HTTP body matching OpenAPI ``UpsertBriefingRequestDto``."""

        text: NotRequired[str]
        generatedAt: NotRequired[str]
        prompts: list["Briefing.BriefingPromptItem"]
        title: NotRequired[str]
        markdown: NotRequired[str]
        content: NotRequired[str]

    class DetachResult(TypedDict):
        """Response from ``DELETE /briefings/{assistantId}`` (``DeleteBriefingResultDto``)."""

        id: str
        object: str
        deleted: bool

    @classmethod
    def _assistant_url(cls, assistant_id: str) -> str:
        return "%s/%s" % (cls.RESOURCE_URL, quote_plus(assistant_id))

    @classmethod
    def _wire_json_from_upsert_params(
        cls, params: Mapping[str, Any]
    ) -> _UpsertBriefingWire:
        """Reduce :class:`UpsertForAssistantParams` kwargs to wire JSON keys only."""
        kw = dict(params)
        for key in _REQUEST_OPTION_KEYS:
            kw.pop(key, None)

        text_raw = kw.get("text")
        md_raw = kw.get("markdown")
        content_raw = kw.get("content")
        if text_raw is not None:
            text: Any | None = text_raw
        elif md_raw is not None:
            text = md_raw
        elif content_raw is not None:
            text = content_raw
        else:
            text = None
        kw.pop("text", None)
        kw.pop("markdown", None)
        kw.pop("content", None)

        if text is None:
            raise ValueError(
                "Briefing upsert requires text= with the briefing (max "
                f"{_MAX_TEXT_LEN} chars). Legacy keywords markdown= or "
                "content= are also accepted."
            )
        if not isinstance(text, str):
            raise TypeError(f"Briefing text must be a string, got {type(text)!r}")
        if not text.strip():
            raise ValueError("Briefing text must not be empty or whitespace-only")
        if len(text) > _MAX_TEXT_LEN:
            raise ValueError(
                f"Briefing text must be at most {_MAX_TEXT_LEN} characters "
                f"(got {len(text)})"
            )

        generated_raw = kw.pop("generatedAt", None)
        if generated_raw is None or (
            isinstance(generated_raw, str) and not generated_raw.strip()
        ):
            ga = _utc_iso8601_now()
        elif isinstance(generated_raw, str):
            ga = generated_raw.strip()
        else:
            ga = generated_raw

        prompts_raw = kw.pop("prompts", None)
        prompts_list = _validate_prompts(prompts_raw)

        wire: _UpsertBriefingWire = {
            "text": text,
            "generatedAt": ga,
            "prompts": prompts_list,
        }

        title_raw = kw.pop("title", None)
        if title_raw is not None:
            if not isinstance(title_raw, str):
                raise TypeError(
                    f"Briefing title must be a string, got {type(title_raw)!r}"
                )
            if len(title_raw) > _MAX_TITLE_LEN:
                raise ValueError(
                    f"Briefing title must be at most {_MAX_TITLE_LEN} characters "
                    f"(got {len(title_raw)})"
                )
            wire["title"] = title_raw

        return wire

    id: str
    object: str
    assistantId: str
    externalId: str | None
    text: str | None
    generatedAt: str | None
    prompts: list[Any] | None
    content: str | None
    title: str | None
    createdAt: str | None
    updatedAt: str | None

    @classmethod
    def get_for_assistant(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
    ) -> "Briefing":
        """Return the briefing attached to ``assistant_id``.

        Mirrors ``BriefingController_getForAssistant`` (``GET /briefings/{assistantId}``).
        """
        url = cls._assistant_url(assistant_id)
        return cast(
            "Briefing",
            cls._static_request("get", url, user_id, company_id),
        )

    @classmethod
    async def get_for_assistant_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
    ) -> "Briefing":
        """Async variant of :meth:`get_for_assistant`."""
        url = cls._assistant_url(assistant_id)
        return cast(
            "Briefing",
            await cls._static_request_async("get", url, user_id, company_id),
        )

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

        Mirrors ``BriefingController_upsertForAssistant`` (``PUT /briefings/{assistantId}``).
        """
        url = cls._assistant_url(assistant_id)
        payload = cls._wire_json_from_upsert_params(params)
        return cast(
            "Briefing",
            cls._static_request("put", url, user_id, company_id, payload),
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
        url = cls._assistant_url(assistant_id)
        payload = cls._wire_json_from_upsert_params(params)
        return cast(
            "Briefing",
            await cls._static_request_async("put", url, user_id, company_id, payload),
        )

    @classmethod
    def detach_for_assistant(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
    ) -> "Briefing.DetachResult":
        """Detach the briefing from ``assistant_id`` (underlying record may remain).

        Mirrors ``BriefingController_detachForAssistant`` (
        ``DELETE /briefings/{assistantId}``).
        """
        url = cls._assistant_url(assistant_id)
        return cast(
            "Briefing.DetachResult",
            cls._static_request("delete", url, user_id, company_id),
        )

    @classmethod
    async def detach_for_assistant_async(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
    ) -> "Briefing.DetachResult":
        """Async variant of :meth:`detach_for_assistant`."""
        url = cls._assistant_url(assistant_id)
        return cast(
            "Briefing.DetachResult",
            await cls._static_request_async("delete", url, user_id, company_id),
        )
