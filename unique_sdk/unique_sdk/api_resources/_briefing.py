"""Assistant briefing operations (``PUT /briefings/{assistantId}``).

Request and response shapes follow OpenAPI ``PublicUpsertBriefingRequestDto`` and
``PublicBriefingDto``. See :class:`Briefing.UpsertForAssistantParams`.
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
_MAX_PROMPTS = 200
_MAX_PROMPT_TITLE_LEN = 100
_MAX_PROMPT_BODY_LEN = 4000
_REQUEST_OPTION_KEYS = frozenset({"api_key", "api_base", "headers"})


def _utc_iso8601_now() -> str:
    """UTC instant as ISO 8601 with ``Z`` suffix (common interchange format)."""

    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_prompts(raw: Any) -> list[dict[str, str]]:
    """Normalize ``prompts`` for ``PublicUpsertBriefingRequestDto`` (max 200 items)."""
    if raw is None:
        raise ValueError(
            "Briefing upsert requires prompts= — a list of up to "
            f"{_MAX_PROMPTS} objects with title and body (OpenAPI "
            "PublicUpsertBriefingRequestDto). Use [] to clear prompts."
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


def _finalize_upsert_request_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Build JSON matching OpenAPI ``PublicUpsertBriefingRequestDto``.

    ``params`` matches :class:`Briefing.UpsertForAssistantParams` at the type level;
    transport keys from :class:`~unique_sdk._request_options.RequestOptions` are
    removed here so they are never sent as JSON.
    """
    kw = dict(params)
    for key in _REQUEST_OPTION_KEYS:
        kw.pop(key, None)

    text: Any | None = None
    if "text" in kw and kw["text"] is not None:
        text = kw["text"]
    elif kw.get("markdown") is not None:
        text = kw["markdown"]
    elif kw.get("content") is not None:
        text = kw["content"]

    for key in ("text", "markdown", "content"):
        kw.pop(key, None)

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
    prompts = _validate_prompts(prompts_raw)

    return {"text": text, "generatedAt": ga, "prompts": prompts}


class Briefing(APIResource["Briefing"]):
    """Create or replace the briefing attached to an assistant."""

    @classproperty
    def OBJECT_NAME(cls) -> Literal["briefing"]:
        return "briefing"

    RESOURCE_URL = "/briefings"

    class BriefingPromptItem(TypedDict):
        """One entry in ``prompts`` (``PublicPromptItemDto``)."""

        title: str
        body: str

    class UpsertForAssistantParams(RequestOptions):
        """HTTP body matching OpenAPI ``PublicUpsertBriefingRequestDto``."""

        text: NotRequired[str]
        generatedAt: NotRequired[str]
        prompts: list["Briefing.BriefingPromptItem"]
        markdown: NotRequired[str]
        content: NotRequired[str]

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
    def upsert_for_assistant(
        cls,
        *,
        user_id: str,
        company_id: str,
        assistant_id: str,
        **params: Unpack["Briefing.UpsertForAssistantParams"],
    ) -> "Briefing":
        """Upsert the briefing for ``assistant_id`` (external id = assistant id).

        Mirrors ``PublicBriefingController_upsertForAssistant`` (
        ``PUT /public/briefings/{assistantId}`` on the upstream OpenAPI surface).
        """
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(assistant_id))
        payload = _finalize_upsert_request_params(params)
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
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(assistant_id))
        payload = _finalize_upsert_request_params(params)
        return cast(
            "Briefing",
            await cls._static_request_async("put", url, user_id, company_id, payload),
        )
