from __future__ import annotations

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field


class TodoStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


_STATUS_ICONS: dict[TodoStatus, str] = {
    TodoStatus.PENDING: "[ ]",
    TodoStatus.IN_PROGRESS: "[>]",
    TodoStatus.COMPLETED: "[x]",
    TodoStatus.CANCELLED: "[-]",
}

_TERMINAL_STATUSES: ClassVar[frozenset[TodoStatus]] = frozenset(
    {TodoStatus.COMPLETED, TodoStatus.CANCELLED}
)


class TodoItem(BaseModel):
    id: str = Field(
        description="Unique identifier for this TODO (model-generated, free-form string e.g. 'research-apis', 'step-1')",
    )
    content: str = Field(description="Description of the task")
    status: TodoStatus


class TodoList(BaseModel):
    """Full TODO state for a session. Stored in ShortTermMemory."""

    todos: list[TodoItem] = Field(default_factory=list)
    last_updated_iteration: int = 0

    def update(self, incoming: list[TodoItem]) -> TodoList:
        """Update by ID: overwrite existing, append new, preserve unmentioned."""
        existing_by_id = {t.id: t for t in self.todos}
        for item in incoming:
            existing_by_id[item.id] = item
        return TodoList(
            todos=list(existing_by_id.values()),
            last_updated_iteration=self.last_updated_iteration,
        )

    def has_active_items(self) -> bool:
        return any(t.status not in _TERMINAL_STATUSES for t in self.todos)

    def format(self) -> str:
        """Format as human-readable text for tool responses."""
        if not self.todos:
            return "No tasks tracked."
        summary = self._summarize()
        return f"Task list ({summary}):\n" + "\n".join(self._format_lines())

    def _format_lines(self) -> list[str]:
        return [
            f"  {_STATUS_ICONS.get(t.status, '[ ]')} {t.content} (id: {t.id})"
            for t in self.todos
        ]

    def _summarize(self) -> str:
        completed = sum(1 for t in self.todos if t.status == TodoStatus.COMPLETED)
        return f"{completed}/{len(self.todos)} completed"


class TodoWriteInput(BaseModel):
    todos: list[TodoItem] = Field(min_length=1)
    merge: bool = Field(
        default=True,
        description="If true, merge with existing todos by ID. If false, replace entirely.",
    )
