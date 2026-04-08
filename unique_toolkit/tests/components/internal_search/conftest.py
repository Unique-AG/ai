"""Shared fixtures for internal_search tests."""

from __future__ import annotations

import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo


@pytest.fixture
def make_chunk():
    """Factory fixture — returns a ContentChunk with required page fields set."""

    def _make(
        chunk_id: str, text: str = "text", start_page: int = 1, end_page: int = 1
    ) -> ContentChunk:
        return ContentChunk(
            chunk_id=chunk_id, text=text, start_page=start_page, end_page=end_page
        )

    return _make


@pytest.fixture
def language_model_info() -> LanguageModelInfo:
    return LanguageModelInfo(
        name="gpt-4o", token_limit_input=128_000, token_limit_output=4096
    )


@pytest.fixture
def set_runnable_state(language_model_info):
    """Factory fixture — populates a service's state so run() is valid."""

    def _set(svc, queries: list[str]) -> None:
        svc._state.search_queries = queries
        svc._state.language_model_info = language_model_info
        svc._state.language_model_max_input_tokens = 128_000

    return _set
