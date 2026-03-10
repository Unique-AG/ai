from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TodoStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class TodoItem(BaseModel):
    id: str = Field(description="Unique identifier for this TODO")
    content: str = Field(description="Description of the task")
    status: TodoStatus


class TodoState(BaseModel):
    """Full TODO state for a session. Stored in ShortTermMemory."""

    todos: list[TodoItem] = Field(default_factory=list)
    last_updated_iteration: int = 0

    def merge(self, incoming: list[TodoItem]) -> TodoState:
        """Merge incoming items by ID: update existing, append new, preserve unmentioned."""
        existing_by_id = {t.id: t for t in self.todos}
        for item in incoming:
            existing_by_id[item.id] = item
        return TodoState(
            todos=list(existing_by_id.values()),
            last_updated_iteration=self.last_updated_iteration,
        )


class TodoWriteInput(BaseModel):
    todos: list[TodoItem] = Field(min_length=1)
    merge: bool = Field(
        default=True,
        description="If true, merge with existing todos by ID. If false, replace entirely.",
    )
