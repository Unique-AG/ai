import logging
from typing import Any, Callable, Generic, TypeVar

from google.genai import types
from pydantic import BaseModel

from unique_web_search.services.search_engine.utils.vertexai.exceptions import (
    VertexAIContentResponseEmptyException,
)

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel | str, covariant=True)
T_Model = TypeVar("T_Model", bound=BaseModel)


class PostProcessFunction(Generic[T]):
    def __init__(self, callable: Callable[..., T], **kwargs: Any):
        self.callable = callable
        self.kwargs = kwargs

    def __call__(self, response: types.GenerateContentResponse) -> T:
        return self.callable(response, **self.kwargs)


def parse_to_structured_results(
    response: types.GenerateContentResponse, response_schema: type[T_Model]
) -> T_Model:
    return response_schema.model_validate(response.parsed)


def add_citations(response: types.GenerateContentResponse) -> str:
    text = response.text

    if not text:
        raise VertexAIContentResponseEmptyException()

    try:
        metadata = response.candidates[0].grounding_metadata  # type: ignore
        supports = metadata.grounding_supports  # type: ignore
        chunks = metadata.grounding_chunks  # type: ignore
    except KeyError:
        raise VertexAIContentResponseEmptyException()

    text = _insert_citations_into_text(text, supports, chunks)  # type: ignore

    return text


def _build_citation_links(
    chunk_indices: list[int], chunks: list[types.GroundingChunk]
) -> str:
    """Return a citation string like: [1](url), [2](url)."""
    links = []
    for idx in chunk_indices:
        if 0 <= idx < len(chunks):
            uri = chunks[idx].web.uri  # type: ignore
            links.append(f"[{idx + 1}]({uri})")
    return ", ".join(links)


def _insert_citations_into_text(
    text: str,
    supports: list[types.GroundingSupport],
    chunks: list[types.GroundingChunk],
) -> str:
    """Insert citation links into text based on grounding supports."""

    sorted_supports = sorted(
        supports,
        key=lambda s: s.segment.end_index,  # type: ignore
        reverse=True,
    )

    for support in sorted_supports:
        chunk_indices = support.grounding_chunk_indices or []
        if not chunk_indices:
            continue

        citation = _build_citation_links(chunk_indices, chunks)
        if not citation:
            continue

        end_index = support.segment.end_index
        text = text[:end_index] + citation + text[end_index:]

    return text
