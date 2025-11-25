import logging
from typing import Any, Callable, Generic, TypeVar

from google.genai import types
from pydantic import BaseModel

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel | str, covariant=True)
T_Model = TypeVar("T_Model", bound=BaseModel)


class PostProcessFunction(Generic[T]):
    def __init__(self, callable: Callable[..., T], **kwargs: Any):
        self.callable = callable
        self.kwargs = kwargs

    def __call__(self, response: types.GenerateContentResponse) -> T:
        return self.callable(response, **self.kwargs)


def add_citations(response: types.GenerateContentResponse) -> str:
    text = response.text
    if not text:
        return "The response from gemini is empty therefore unable to add citations"

    try:
        supports = response.candidates[0].grounding_metadata.grounding_supports  # type: ignore
        chunks = response.candidates[0].grounding_metadata.grounding_chunks  # type: ignore
        sorted_supports = sorted(
            supports,  # type: ignore
            key=lambda s: s.segment.end_index,  # type: ignore
            reverse=True,
        )

        for support in sorted_supports:
            end_index = support.segment.end_index
            if support.grounding_chunk_indices:
                # Create citation string like [1](link1)[2](link2)
                citation_links = []
                for i in support.grounding_chunk_indices:
                    if i < len(chunks):  # type: ignore
                        uri = chunks[i].web.uri  # type: ignore
                        citation_links.append(f"[{i + 1}]({uri})")

                citation_string = ", ".join(citation_links)
                text = text[:end_index] + citation_string + text[end_index:]  # type: ignore

        return text

    except Exception as e:
        _LOGGER.error(f"Error adding citations: {e}")
        return "An error occurred while adding citations to the response"


def parse_to_structured_results(
    response: types.GenerateContentResponse, response_schema: type[T_Model]
) -> T_Model:
    return response_schema.model_validate(response.parsed)
