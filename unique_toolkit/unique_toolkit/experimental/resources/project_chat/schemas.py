"""Pydantic schemas for :mod:`unique_toolkit.experimental.resources.project_chat`.

The models mirror the responses of the ``/search/project-chats`` endpoints
(:class:`unique_sdk.ProjectChat`) with snake_case fields, camelCase aliases for
the wire payload, and parsed datetimes.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`; the public
    shape of these models may still change without notice.
"""

from __future__ import annotations

from datetime import datetime

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

_model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class ProjectChatChunk(BaseModel):
    """A chunk of an earlier project chat: consecutive question and answer pairs."""

    model_config = _model_config

    chat_id: str = Field(description="Chat the chunk belongs to.")
    chat_title: str | None = Field(default=None, description="Title of the chat.")
    chunk_index: int = Field(description="Position of the chunk in its chat, from 0.")
    pair_index_start: int = Field(
        description="First question and answer pair in the chunk, from 1."
    )
    pair_index_end: int = Field(
        description="Last question and answer pair in the chunk."
    )
    message_ids: list[str] = Field(
        default_factory=list, description="Messages in the chunk."
    )
    text: str = Field(
        description=(
            "Text of the chunk: each pair starts with ``[pair N · time]`` "
            "followed by ``User:`` and ``Assistant:`` lines."
        )
    )
    token_count: int = Field(description="Number of tokens in ``text``.")
    is_open: bool = Field(
        description="True for the last chunk of the chat, which can still grow."
    )
    created_at: datetime = Field(description="Time of the first message in the chunk.")
    updated_at: datetime = Field(description="Time of the last message in the chunk.")
    score: float | None = Field(
        default=None,
        description="Relevance score. Set by search only; not comparable across queries.",
    )
    highlights: list[str] | None = Field(
        default=None,
        description="Matching passages with ``<em>`` around hits. Set by search only.",
    )


class ProjectChatStats(BaseModel):
    """Chunk and token totals of one chat."""

    model_config = _model_config

    chat_id: str = Field(description="Chat identifier.")
    chunk_count: int = Field(description="Number of chunks in the chat.")
    token_count: int = Field(description="Number of tokens in the chat.")


class ProjectChatChunkPage(BaseModel):
    """Result of a search or of reading one chat: a page of chunks."""

    model_config = _model_config

    chunks: list[ProjectChatChunk] = Field(
        default_factory=list, alias="data", description="The chunks."
    )
    chat_stats: list[ProjectChatStats] = Field(
        default_factory=list,
        description="Totals of the chats in ``chunks``. Empty unless requested.",
    )
    next_cursor: str | None = Field(
        default=None,
        description=(
            "Pass as ``after`` to get the next page. ``None`` on the last page "
            "and always for search."
        ),
    )


class ProjectChatSummary(BaseModel):
    """One chat of a project, as listed by the recent chats call."""

    model_config = _model_config

    chat_id: str = Field(description="Chat identifier.")
    chat_title: str | None = Field(default=None, description="Title of the chat.")
    chat_created_at: datetime = Field(description="Creation time of the chat.")
    updated_at: datetime = Field(description="Time of the last message.")
    chunk_count: int = Field(description="Number of indexed chunks in the chat.")


class ProjectChatSummaryPage(BaseModel):
    """A page of a project's chats, most recently active first."""

    model_config = _model_config

    chats: list[ProjectChatSummary] = Field(
        default_factory=list, alias="data", description="The chats."
    )
    next_cursor: str | None = Field(
        default=None,
        description="Pass as ``after`` to get the next page. ``None`` on the last page.",
    )
