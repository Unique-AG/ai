from __future__ import annotations

from enum import StrEnum

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

_TERMINAL_STATUSES: frozenset[TodoStatus] = frozenset(
    {TodoStatus.COMPLETED, TodoStatus.CANCELLED}
)


class TodoItem(BaseModel):
    """Stored todo item — always has content."""

    id: str = Field(
        description="Unique identifier for this TODO (model-generated, free-form string e.g. 'research-apis', 'step-1')",
    )
    content: str = Field(description="Description of the task")
    status: TodoStatus
    active_form: str | None = Field(
        default=None,
        description="Present-continuous form of the task shown as live status text "
        "(e.g. 'Searching documents', 'Analyzing results'). "
        "Provide when creating or updating an item.",
    )


class TodoItemInput(BaseModel):
    """Input todo item — content is optional for merge updates (status-only changes)."""

    id: str = Field(
        description="Unique identifier for this TODO (model-generated, free-form string e.g. 'research-apis', 'step-1')",
    )
    content: str | None = Field(
        default=None,
        description="Description of the task. Required when creating new items, optional when updating existing ones via merge.",
    )
    status: TodoStatus
    active_form: str | None = Field(
        default=None,
        description="Present-continuous form shown as live status text "
        "(e.g. 'Searching documents'). Provide for richer UI display.",
    )


class TodoList(BaseModel):
    """Full TODO state for a session. Stored in ShortTermMemory."""

    todos: list[TodoItem] = Field(default_factory=list)
    last_updated_iteration: int = 0

    def update(self, incoming: list[TodoItemInput]) -> TodoList:
        """Update by ID: overwrite existing, append new, preserve unmentioned.

        When an incoming item omits content, the existing content is preserved.
        active_form falls back to existing value when not supplied.
        New items without content get an empty string as fallback.
        """
        existing_by_id = {t.id: t for t in self.todos}
        for item in incoming:
            existing = existing_by_id.get(item.id)
            content = (
                item.content
                if item.content is not None
                else (existing.content if existing else "")
            )
            active_form = (
                item.active_form
                if item.active_form is not None
                else (existing.active_form if existing else None)
            )
            existing_by_id[item.id] = TodoItem(
                id=item.id,
                content=content,
                status=item.status,
                active_form=active_form,
            )
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

    def status_counts(self) -> dict[str, int]:
        """Return a dict of status counts for debug_info and logging."""
        counts: dict[str, int] = {
            "total": len(self.todos),
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "cancelled": 0,
        }
        for t in self.todos:
            key = t.status.value
            if key in counts:
                counts[key] += 1
        return counts

    def _format_lines(self) -> list[str]:
        return [
            f"  {_STATUS_ICONS.get(t.status, '[ ]')} {t.content} (id: {t.id})"
            for t in self.todos
        ]

    def _summarize(self) -> str:
        completed = sum(1 for t in self.todos if t.status == TodoStatus.COMPLETED)
        return f"{completed}/{len(self.todos)} completed"


class TodoWriteInput(BaseModel):
    todos: list[TodoItemInput] = Field(min_length=1)
    merge: bool = Field(
        default=True,
        description="If true, merge with existing todos by ID. If false, replace entirely.",
    )
