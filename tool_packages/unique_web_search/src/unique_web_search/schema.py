"""Shared web-search runtime models and re-exports for tool parameters.

Tool-call Pydantic models live under ``services/executors/vN/schema.py``;
symbols below are re-exported for backward-compatible imports
(e.g. ``from unique_web_search.schema import WebSearchPlan``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from unidecode import unidecode
from unique_toolkit.content.schemas import ContentChunk


class StepDebugInfo(BaseModel):
    step_name: str
    execution_time: float
    config: str | dict
    extra: dict = Field(default_factory=dict)


class WebPageChunk(BaseModel):
    url: str
    display_link: str
    title: str
    snippet: str
    content: str
    order: str

    def to_content_chunk(self) -> ContentChunk:
        """Convert WebPageChunk to ContentChunk format."""

        # Convert to ascii
        title = unidecode(self.title)
        name = f'{self.display_link}: "{title}"'

        return ContentChunk(
            id=name,
            text=self.content,
            order=int(self.order),
            start_page=None,
            end_page=None,
            key=name,
            chunk_id=self.order,
            url=self.url,
            title=name,
        )


class WebSearchDebugInfo(BaseModel):
    parameters: dict
    steps: list[StepDebugInfo] = []
    web_page_chunks: list[WebPageChunk] = []
    execution_time: float | None = None
    num_chunks_in_final_prompts: int = 0

    def model_dump(self, *, with_debug_details: bool = True, **kwargs):
        """
        Dump the model. When ``with_debug_details=False`` only the bulky
        ``web_page_chunks`` (full crawled page bodies) is stripped.

        The per-step ``extra`` dicts are intentionally kept — they hold small
        structured metadata about the search process (result counts, judge
        scores, kept/dropped URLs, objective/query/gap) that operators need
        to understand *why* the agent took a given decision. Stripping that
        was over-aggressive: the volume concern was always ``web_page_chunks``.
        """
        exclude = kwargs.pop("exclude", {})
        if not with_debug_details:
            exclude = {"web_page_chunks": True} | exclude
        return super().model_dump(exclude=exclude, **kwargs)
