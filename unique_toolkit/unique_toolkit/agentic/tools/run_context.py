from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self

from unique_toolkit.app.schemas import ChatEvent


class ToolRunContext(BaseModel):
    """Tool-manager runtime state decoupled from a raw :class:`ChatEvent`."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tool_choices: list[str] = Field(default_factory=list)
    disabled_tools: list[str] = Field(default_factory=list)
    tool_init_event: ChatEvent | None = None

    @classmethod
    def from_chat_event(cls, event: ChatEvent) -> Self:
        return cls(
            tool_choices=list(event.payload.tool_choices),
            disabled_tools=list(event.payload.disabled_tools),
            tool_init_event=event,
        )
