"""Tenant context propagated via HTTP headers between SDK callers and the proxy."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

COMPANY_ID_HEADER = "x-unique-company-id"
USER_ID_HEADER = "x-unique-user-id"
CHAT_ID_HEADER = "x-unique-chat-id"
USER_METADATA_HEADER = "x-unique-user-metadata"

_CONTEXT_HEADER_FIELDS: tuple[tuple[str, str], ...] = (
    ("company_id", COMPANY_ID_HEADER),
    ("user_id", USER_ID_HEADER),
    ("chat_id", CHAT_ID_HEADER),
)

_LOGGER = logging.getLogger(__name__)


class RequestContext(BaseModel):
    """Caller identity for search-proxy requests."""

    model_config = ConfigDict(frozen=True)

    company_id: str
    user_id: str
    chat_id: str
    user_metadata: dict[str, Any] | None = None

    def to_headers(self) -> dict[str, str]:
        """Serialize context to the canonical HTTP header names."""
        headers = {
            COMPANY_ID_HEADER: self.company_id,
            USER_ID_HEADER: self.user_id,
            CHAT_ID_HEADER: self.chat_id,
        }
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
            user_metadata=_parse_user_metadata(
                normalized.get(USER_METADATA_HEADER),
                fallback=fallback.user_metadata,
            ),
        )


def _parse_user_metadata(
    raw: Any,
    *,
    fallback: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Decode the JSON user-metadata header, treating malformed values as absent.

    Callers that require an identity from this metadata fail closed on ``None``,
    so a malformed header must not raise here and abort the whole request.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return fallback
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        _LOGGER.warning("Ignoring malformed %s header", USER_METADATA_HEADER)
        return None
    if not isinstance(decoded, dict):
        _LOGGER.warning("Ignoring non-object %s header", USER_METADATA_HEADER)
        return None
    return decoded


LOCAL_REQUEST_CONTEXT = RequestContext(
    company_id="local",
    user_id="local",
    chat_id="local",
)


__all__ = [
    "CHAT_ID_HEADER",
    "COMPANY_ID_HEADER",
    "LOCAL_REQUEST_CONTEXT",
    "RequestContext",
    "USER_ID_HEADER",
    "USER_METADATA_HEADER",
]
