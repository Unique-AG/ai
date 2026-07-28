"""Tenant context propagated via HTTP headers between SDK callers and the proxy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

COMPANY_ID_HEADER = "x-unique-company-id"
USER_ID_HEADER = "x-unique-user-id"
CHAT_ID_HEADER = "x-unique-chat-id"

_CONTEXT_HEADER_FIELDS: tuple[tuple[str, str], ...] = (
    ("company_id", COMPANY_ID_HEADER),
    ("user_id", USER_ID_HEADER),
    ("chat_id", CHAT_ID_HEADER),
)


class RequestContext(BaseModel):
    """Caller identity for search-proxy requests."""

    model_config = ConfigDict(frozen=True)

    company_id: str
    user_id: str
    chat_id: str

    def to_headers(self) -> dict[str, str]:
        """Serialize context to the canonical HTTP header names."""
        return {
            COMPANY_ID_HEADER: self.company_id,
            USER_ID_HEADER: self.user_id,
            CHAT_ID_HEADER: self.chat_id,
        }

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
        return cls(**values)


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
]
