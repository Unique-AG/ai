"""Input schema of the ProjectChatSearch tool.

One flat schema for every use: ``mode`` says what to do, the other fields are
optional. A ``before`` validator normalises what weaker models tend to send
(empty strings, upper-case modes, pages as strings) so it never fails on form.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["search", "read", "recent"]

_OPTIONAL_TEXT_FIELDS = ("query", "chat_id", "after", "before")


class ProjectChatSearchInput(BaseModel):
    """Arguments of one ProjectChatSearch call."""

    model_config = ConfigDict(extra="ignore")

    mode: Mode = Field(
        description=(
            "What to do: 'search' finds passages matching `query`; 'read' reads "
            "the chat `chat_id` in order; 'recent' lists the project's chats, "
            "most recently active first."
        ),
    )
    query: str | None = Field(
        default=None,
        description="search: what to look for, in the words the user would have used.",
    )
    chat_id: str | None = Field(
        default=None,
        description=(
            "read: the chat to read (required). search: optional, only search "
            "inside this chat. Use a chat id from an earlier result."
        ),
    )
    after: str | None = Field(
        default=None,
        description="search and recent: only activity on or after this day, YYYY-MM-DD.",
    )
    before: str | None = Field(
        default=None,
        description="search and recent: only activity on or before this day, YYYY-MM-DD.",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="read and recent: which page of results, starting at 1.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        values: dict[str, Any] = dict(data)
        mode = values.get("mode")
        if isinstance(mode, str):
            values["mode"] = mode.strip().lower()
        for field in _OPTIONAL_TEXT_FIELDS:
            value = values.get(field)
            if isinstance(value, str):
                value = value.strip()
                values[field] = value or None
        page = values.get("page")
        if page is None or (isinstance(page, str) and not page.strip()):
            values["page"] = 1
        elif isinstance(page, str) and page.strip().isdigit():
            values["page"] = max(int(page.strip()), 1)
        elif isinstance(page, int) and page < 1:
            values["page"] = 1
        return values


def parse_day(value: str, *, end_of_day: bool) -> datetime:
    """Parse a day or an ISO date-time into an aware UTC datetime.

    A bare ``YYYY-MM-DD`` means the start of that day, or its end when
    ``end_of_day`` is set, so ``before=2026-11-24`` includes the whole day.

    Raises:
        ValueError: The value is neither a day nor an ISO date-time.
    """
    text = value.strip()
    if len(text) == 10:
        day = date.fromisoformat(text)
        return datetime.combine(day, time.max if end_of_day else time.min, UTC)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
