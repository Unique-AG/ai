"""Load the project memory for a project chat turn (UN-29145)."""

from __future__ import annotations

from logging import Logger

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.experimental.resources.project_memory import ProjectMemories


async def load_project_memory_text(*, event: ChatEvent, logger: Logger) -> str:
    """The project's memory document for the system prompt, or ``""``.

    Empty for chats outside a project and for projects without a memory yet.
    A failed read never fails the turn: it runs without project memory.
    """
    if not event.payload.project_id:
        return ""
    try:
        document = await ProjectMemories.from_event(event).get_document_async()
    except Exception as exc:
        logger.warning(
            "[project-memory] load failed - running without project memory: [%s]",
            type(exc).__name__,
        )
        return ""
    return (document or "").strip()
