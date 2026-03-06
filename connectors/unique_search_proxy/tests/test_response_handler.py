from unittest.mock import MagicMock

import pytest
from core.vertexai.exceptions import VertexAIContentResponseEmptyException
from core.vertexai.response_handler import (
    PostProcessFunction,
    _build_citation_links,
    _insert_citations_into_text,
    add_citations,
    parse_to_structured_results,
)
from pydantic import BaseModel


class TestPostProcessFunction:
    def test_basic_callable(self):
        fn = PostProcessFunction(lambda resp: resp.text)
        mock_resp = MagicMock()
        mock_resp.text = "hello"
        assert fn(mock_resp) == "hello"

    def test_with_kwargs(self):
        def extractor(resp, key="default"):
            return key

        fn = PostProcessFunction(extractor, key="custom")
        assert fn(MagicMock()) == "custom"


class TestBuildCitationLinks:
    def test_single_citation(self):
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        result = _build_citation_links([0], [chunk])
        assert result == "[1](https://a.com)"

    def test_multiple_citations(self):
        c1, c2 = MagicMock(), MagicMock()
        c1.web.uri = "https://a.com"
        c2.web.uri = "https://b.com"
        result = _build_citation_links([0, 1], [c1, c2])
        assert result == "[1](https://a.com), [2](https://b.com)"

    def test_out_of_range_index_skipped(self):
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        result = _build_citation_links([0, 5], [chunk])
        assert result == "[1](https://a.com)"

    def test_empty_indices(self):
        result = _build_citation_links([], [])
        assert result == ""

    def test_negative_index_skipped(self):
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        result = _build_citation_links([-1, 0], [chunk])
        assert result == "[1](https://a.com)"


class TestInsertCitationsIntoText:
    def _make_support(self, end_index, chunk_indices):
        support = MagicMock()
        support.segment.end_index = end_index
        support.grounding_chunk_indices = chunk_indices
        return support

    def _make_chunk(self, uri):
        chunk = MagicMock()
        chunk.web.uri = uri
        return chunk

    def test_single_citation(self):
        text = "Hello world."
        chunks = [self._make_chunk("https://a.com")]
        supports = [self._make_support(12, [0])]
        result = _insert_citations_into_text(text, supports, chunks)
        assert result == "Hello world.[1](https://a.com)"

    def test_multiple_citations_inserted_correctly(self):
        text = "First sentence. Second sentence."
        chunks = [self._make_chunk("https://a.com"), self._make_chunk("https://b.com")]
        supports = [
            self._make_support(15, [0]),
            self._make_support(31, [1]),
        ]
        result = _insert_citations_into_text(text, supports, chunks)
        assert "[1](https://a.com)" in result
        assert "[2](https://b.com)" in result

    def test_empty_chunk_indices_skipped(self):
        text = "Hello."
        supports = [self._make_support(6, [])]
        result = _insert_citations_into_text(text, supports, [])
        assert result == "Hello."

    def test_no_supports(self):
        result = _insert_citations_into_text("Hello.", [], [])
        assert result == "Hello."


class TestAddCitations:
    def _make_response(self, text, supports=None, chunks=None):
        response = MagicMock()
        response.text = text
        candidate = MagicMock()
        candidate.grounding_metadata.grounding_supports = supports or []
        candidate.grounding_metadata.grounding_chunks = chunks or []
        response.candidates = [candidate]
        return response

    def test_empty_text_raises(self):
        response = MagicMock()
        response.text = None
        with pytest.raises(VertexAIContentResponseEmptyException):
            add_citations(response)

    def test_with_citations(self):
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        support = MagicMock()
        support.segment.end_index = 5
        support.grounding_chunk_indices = [0]
        response = self._make_response("Hello", supports=[support], chunks=[chunk])
        result = add_citations(response)
        assert "[1](https://a.com)" in result


class TestParseToStructuredResults:
    def test_parses_response(self):
        class MyModel(BaseModel):
            name: str

        response = MagicMock()
        response.parsed = {"name": "test"}
        result = parse_to_structured_results(response, MyModel)
        assert result.name == "test"
