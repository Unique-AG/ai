"""Tenant context propagated via HTTP headers between SDK callers and the proxy."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

COMPANY_ID_HEADER = "x-unique-company-id"
USER_ID_HEADER = "x-unique-user-id"
CHAT_ID_HEADER = "x-unique-chat-id"
USER_METADATA_HEADER = "x-unique-user-metadata"
ENTRY_POINT_HEADER = "x-unique-entry-point"
MESSAGE_ID_HEADER = "x-unique-message-id"
SERVICE_ID_HEADER = "x-service-id"

_CONTEXT_HEADER_FIELDS: tuple[tuple[str, str], ...] = (
    ("company_id", COMPANY_ID_HEADER),
    ("user_id", USER_ID_HEADER),
    ("chat_id", CHAT_ID_HEADER),
)

_LOGGER = logging.getLogger(__name__)


class EntryPoint(StrEnum):
    """Service where a search request entered the platform."""

    CHAT_TOOL = "chat_tool"
    PUBLIC_API = "public_api"
    CONDUCT = "conduct"
    UNIQUE_API = "unique_api"
    GRAPHQL = "graphql"
    DEEP_RESEARCH = "deep_research"
    WEB_SEARCH_SERVICE = "web_search_service"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> EntryPoint:
        return cls.UNKNOWN


class RequestContext(BaseModel):
    """Caller identity for search-proxy requests."""

    model_config = ConfigDict(frozen=True)

    company_id: str
    user_id: str
    chat_id: str
    entry_point: EntryPoint = EntryPoint.UNKNOWN
    # Calling service from ``x-service-id``; logged only, never enforced.
    caller: str = "unknown"
    # Reserved for analytics; optional until callers send it.
    message_id: str | None = None
    user_metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def invalid_identity_headers(self) -> list[str]:
        """Identity headers whose value is not a numeric id (``local``, blank, junk)."""
        return [
            header_name
            for header_name, value in (
                (COMPANY_ID_HEADER, self.company_id),
                (USER_ID_HEADER, self.user_id),
            )
            if not (value.isascii() and value.isdecimal())
        ]

    @property
    def is_attributed(self) -> bool:
        return not self.invalid_identity_headers

    def to_headers(self) -> dict[str, str]:
        """Serialize context to the canonical HTTP header names."""
        headers = {
            COMPANY_ID_HEADER: self.company_id,
            USER_ID_HEADER: self.user_id,
            CHAT_ID_HEADER: self.chat_id,
        }
        if self.entry_point is not EntryPoint.UNKNOWN:
            headers[ENTRY_POINT_HEADER] = self.entry_point.value
        if self.message_id:
            headers[MESSAGE_ID_HEADER] = self.message_id
        if self.user_metadata:
            # ``ensure_ascii`` keeps the value latin-1 encodable, which HTTP
            # headers require.
            headers[USER_METADATA_HEADER] = json.dumps(
                self.user_metadata,
                ensure_ascii=True,
            )
        return headers

    @classmethod
    def missing_headers(cls, headers: Mapping[str, Any]) -> list[str]:
        """Return header names that are absent or blank."""
        normalized = {key.lower(): value for key, value in headers.items()}
        missing: list[str] = []
        for _field, header_name in _CONTEXT_HEADER_FIELDS:
            value = normalized.get(header_name.lower())
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(header_name)
        return missing

    @classmethod
    def from_headers(
        cls,
        headers: Mapping[str, Any],
        *,
        fallback: RequestContext,
    ) -> RequestContext:
        """Build context from headers, using ``fallback`` for any missing values."""
        normalized = {key.lower(): value for key, value in headers.items()}
        values: dict[str, str] = {}
        for field_name, header_name in _CONTEXT_HEADER_FIELDS:
            raw = normalized.get(header_name.lower())
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                values[field_name] = getattr(fallback, field_name)
            else:
                values[field_name] = str(raw)
        return cls(
            **values,
            entry_point=normalized.get(
                ENTRY_POINT_HEADER.lower(),
                fallback.entry_point,
            ),
            caller=normalized.get(SERVICE_ID_HEADER) or fallback.caller,
            message_id=str(normalized.get(MESSAGE_ID_HEADER) or "").strip()
            or fallback.message_id,
            user_metadata=_parse_user_metadata(
                normalized.get(USER_METADATA_HEADER),
                fallback=fallback.user_metadata,
            ),
        )


def _parse_user_metadata(
    raw: Any,
    *,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    """Decode the JSON user-metadata header; absent → fallback, malformed → {}."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return fallback
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError) as exc:
        # Log the error class only — never the header body (may contain PII).
        _LOGGER.warning(
            "Ignoring malformed %s header (%s)",
            USER_METADATA_HEADER,
            type(exc).__name__,
        )
        return {}
    if not isinstance(decoded, dict):
        _LOGGER.warning("Ignoring non-object %s header", USER_METADATA_HEADER)
        return {}
    return decoded


LOCAL_REQUEST_CONTEXT = RequestContext(
    company_id="local",
    user_id="local",
    chat_id="local",
)


__all__ = [
    "CHAT_ID_HEADER",
    "COMPANY_ID_HEADER",
    "ENTRY_POINT_HEADER",
    "EntryPoint",
    "LOCAL_REQUEST_CONTEXT",
    "MESSAGE_ID_HEADER",
    "RequestContext",
    "SERVICE_ID_HEADER",
    "USER_ID_HEADER",
    "USER_METADATA_HEADER",
]
