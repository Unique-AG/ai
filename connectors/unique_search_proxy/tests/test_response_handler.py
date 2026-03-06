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
    @pytest.mark.ai
    def test_basic_callable(self):
        """
        Purpose: Verify PostProcessFunction wraps and invokes a plain callable.
        Why this matters: PostProcessFunction is the extensibility point for response processing.
        Setup summary: Wrap a lambda, call it with a mock response, assert return value.
        """
        fn = PostProcessFunction(lambda resp: resp.text)
        mock_resp = MagicMock()
        mock_resp.text = "hello"
        assert fn(mock_resp) == "hello"

    @pytest.mark.ai
    def test_with_kwargs(self):
        """
        Purpose: Verify PostProcessFunction forwards keyword arguments.
        Why this matters: Some post-processors require additional configuration.
        Setup summary: Wrap a function with a keyword arg, call it, assert the kwarg is used.
        """
        def extractor(resp, key="default"):
            return key

        fn = PostProcessFunction(extractor, key="custom")
        assert fn(MagicMock()) == "custom"


class TestBuildCitationLinks:
    @pytest.mark.ai
    def test_single_citation(self):
        """
        Purpose: Verify a single citation index produces a markdown link.
        Why this matters: Citations link AI answers back to their source URLs.
        Setup summary: Pass one chunk index and assert the formatted link.
        """
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        result = _build_citation_links([0], [chunk])
        assert result == "[1](https://a.com)"

    @pytest.mark.ai
    def test_multiple_citations(self):
        """
        Purpose: Verify multiple citation indices produce comma-separated links.
        Why this matters: A single sentence may be grounded by multiple sources.
        Setup summary: Pass two chunk indices and assert both links appear.
        """
        c1, c2 = MagicMock(), MagicMock()
        c1.web.uri = "https://a.com"
        c2.web.uri = "https://b.com"
        result = _build_citation_links([0, 1], [c1, c2])
        assert result == "[1](https://a.com), [2](https://b.com)"

    @pytest.mark.ai
    def test_out_of_range_index_skipped(self):
        """
        Purpose: Verify out-of-range chunk indices are silently skipped.
        Why this matters: API may return stale indices; skipping prevents IndexError.
        Setup summary: Pass an in-range and out-of-range index, assert only valid link.
        """
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        result = _build_citation_links([0, 5], [chunk])
        assert result == "[1](https://a.com)"

    @pytest.mark.ai
    def test_empty_indices(self):
        """
        Purpose: Verify empty indices produce an empty string.
        Why this matters: Not all text segments have citations.
        Setup summary: Pass empty lists and assert empty output.
        """
        result = _build_citation_links([], [])
        assert result == ""

    @pytest.mark.ai
    def test_negative_index_skipped(self):
        """
        Purpose: Verify negative indices are silently skipped.
        Why this matters: Defensive handling of unexpected API data.
        Setup summary: Pass a negative and valid index, assert only valid link.
        """
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

    @pytest.mark.ai
    def test_single_citation(self):
        """
        Purpose: Verify a citation link is inserted at the correct text position.
        Why this matters: Citation placement must align with the grounded text segment.
        Setup summary: Insert one citation at end_index=12 and assert the result.
        """
        text = "Hello world."
        chunks = [self._make_chunk("https://a.com")]
        supports = [self._make_support(12, [0])]
        result = _insert_citations_into_text(text, supports, chunks)
        assert result == "Hello world.[1](https://a.com)"

    @pytest.mark.ai
    def test_multiple_citations_inserted_correctly(self):
        """
        Purpose: Verify multiple citations are inserted at their respective positions.
        Why this matters: Multi-source grounding requires correct per-segment attribution.
        Setup summary: Insert two citations at different offsets and assert both appear.
        """
        text = "First sentence. Second sentence."
        chunks = [self._make_chunk("https://a.com"), self._make_chunk("https://b.com")]
        supports = [
            self._make_support(15, [0]),
            self._make_support(31, [1]),
        ]
        result = _insert_citations_into_text(text, supports, chunks)
        assert "[1](https://a.com)" in result
        assert "[2](https://b.com)" in result

    @pytest.mark.ai
    def test_empty_chunk_indices_skipped(self):
        """
        Purpose: Verify supports with no chunk indices leave the text unchanged.
        Why this matters: Some supports may have empty grounding data.
        Setup summary: Pass a support with empty indices and assert text is unchanged.
        """
        text = "Hello."
        supports = [self._make_support(6, [])]
        result = _insert_citations_into_text(text, supports, [])
        assert result == "Hello."

    @pytest.mark.ai
    def test_no_supports(self):
        """
        Purpose: Verify text is returned unchanged when there are no supports.
        Why this matters: Not all AI responses include grounding metadata.
        Setup summary: Pass empty supports and assert text is unchanged.
        """
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

    @pytest.mark.ai
    def test_empty_text_raises(self):
        """
        Purpose: Verify None text raises VertexAIContentResponseEmptyException.
        Why this matters: Empty AI responses need distinct handling from normal results.
        Setup summary: Set response.text=None and expect the specific exception.
        """
        response = MagicMock()
        response.text = None
        with pytest.raises(VertexAIContentResponseEmptyException):
            add_citations(response)

    @pytest.mark.ai
    def test_with_citations(self):
        """
        Purpose: Verify citations are inserted into the response text.
        Why this matters: This is the primary grounding flow for Vertex AI results.
        Setup summary: Build a response with one support and chunk, assert citation appears.
        """
        chunk = MagicMock()
        chunk.web.uri = "https://a.com"
        support = MagicMock()
        support.segment.end_index = 5
        support.grounding_chunk_indices = [0]
        response = self._make_response("Hello", supports=[support], chunks=[chunk])
        result = add_citations(response)
        assert "[1](https://a.com)" in result


class TestParseToStructuredResults:
    @pytest.mark.ai
    def test_parses_response(self):
        """
        Purpose: Verify parsed response data is converted to the target Pydantic model.
        Why this matters: Structured results are the return type for typed search endpoints.
        Setup summary: Mock response.parsed, call parse_to_structured_results, assert the model.
        """
        class MyModel(BaseModel):
            name: str

        response = MagicMock()
        response.parsed = {"name": "test"}
        result = parse_to_structured_results(response, MyModel)
        assert result.name == "test"
