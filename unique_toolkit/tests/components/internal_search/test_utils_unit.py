"""Unit tests for unique_toolkit.components.internal_search.base.utils."""

import pytest

from unique_toolkit.components.internal_search.base.schemas import SearchStringResult
from unique_toolkit.components.internal_search.base.utils import (
    clean_search_string,
    interleave_search_results_round_robin,
)
from unique_toolkit.content.schemas import ContentChunk

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(chunk_id: str, text: str = "") -> ContentChunk:
    return ContentChunk(chunk_id=chunk_id, text=text)


def _result(query: str, chunk_ids: list[str]) -> SearchStringResult:
    return SearchStringResult(
        query=query,
        chunks=[_chunk(cid) for cid in chunk_ids],
    )


# ---------------------------------------------------------------------------
# clean_search_string
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_clean_search_string__removes_qdf_suffix():
    """
    Purpose: Verifies that --QDF=<n> is stripped from the end of the search string.
    Why this matters: Downstream search APIs do not understand QDF operators; leaving
        them in would corrupt the query.
    Setup summary: Input with a trailing --QDF=1 operator; assert it is absent in output.
    """
    raw = "GPT4 performance on MMLU benchmark --QDF=1"
    assert clean_search_string(raw) == "GPT4 performance on MMLU benchmark"


@pytest.mark.verified
def test_clean_search_string__removes_boost_operators():
    """
    Purpose: Verifies that +(term) boost syntax is unwrapped to just the term.
    Why this matters: Boost operators are search-engine–specific; callers that forward
        the cleaned string to a different engine would send malformed queries otherwise.
    Setup summary: Input with multiple +(…) fragments; assert parentheses and + are gone.
    """
    raw = "Best practices for +(security) and +(privacy) for +(cloud storage) --QDF=2"
    assert (
        clean_search_string(raw)
        == "Best practices for security and privacy for cloud storage"
    )


@pytest.mark.verified
def test_clean_search_string__plain_string_unchanged():
    """
    Purpose: Verifies that a string with no operators is returned as-is.
    Why this matters: The function must be a no-op on already-clean inputs to avoid
        corrupting valid queries.
    Setup summary: Plain query string with no special syntax.
    """
    raw = "what is machine learning"
    assert clean_search_string(raw) == raw


@pytest.mark.verified
def test_clean_search_string__collapses_extra_whitespace():
    """
    Purpose: Verifies that operator removal does not leave stray whitespace.
    Why this matters: Extra spaces would make identical queries look distinct after
        deduplication.
    Setup summary: Query where removing operators would leave multiple consecutive spaces.
    """
    raw = "hello  world"
    assert clean_search_string(raw) == "hello world"


@pytest.mark.verified
def test_clean_search_string__empty_string():
    """
    Purpose: Verifies that an empty string is handled without error.
    Why this matters: Guard against crashes when upstream sends an empty search string.
    Setup summary: Empty input; expect empty output.
    """
    assert clean_search_string("") == ""


# ---------------------------------------------------------------------------
# interleave_search_results_round_robin
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_interleave__empty_input_returns_empty():
    """
    Purpose: Verifies that an empty list returns an empty list.
    Why this matters: Callers may pass zero results; a crash here would break the pipeline.
    Setup summary: Empty input list; assert output is also empty.
    """
    assert interleave_search_results_round_robin([]) == []


@pytest.mark.verified
def test_interleave__single_result_preserves_chunks():
    """
    Purpose: Verifies that a single SearchStringResult is exploded into per-chunk entries.
    Why this matters: Downstream consumers expect each SearchStringResult to contain
        exactly one chunk after interleaving.
    Setup summary: One result with three chunks; assert output has three single-chunk results.
    """
    results = [_result("q1", ["a", "b", "c"])]
    out = interleave_search_results_round_robin(results)
    assert len(out) == 3
    assert all(len(r.chunks) == 1 for r in out)
    assert [r.chunks[0].chunk_id for r in out] == ["a", "b", "c"]


@pytest.mark.verified
def test_interleave__round_robin_ordering():
    """
    Purpose: Verifies that chunks from multiple queries are interleaved position-by-position.
    Why this matters: Round-robin ordering ensures diversity in the merged chunk list;
        a naive concatenation would front-load one query's results.
    Setup summary: Two results with two chunks each; assert output alternates between them.
    """
    results = [
        _result("q1", ["a", "b"]),
        _result("q2", ["c", "d"]),
    ]
    out = interleave_search_results_round_robin(results)
    ids = [r.chunks[0].chunk_id for r in out]
    assert ids == ["a", "c", "b", "d"]


@pytest.mark.verified
def test_interleave__deduplicates_chunks():
    """
    Purpose: Verifies that duplicate chunk_ids are removed, keeping the first occurrence.
    Why this matters: Duplicate chunks inflate context size and confuse citations.
    Setup summary: Two results sharing a common chunk_id; assert only the first is kept.
    """
    results = [
        _result("q1", ["a", "shared"]),
        _result("q2", ["shared", "b"]),
    ]
    out = interleave_search_results_round_robin(results)
    ids = [r.chunks[0].chunk_id for r in out]
    assert ids.count("shared") == 1
    assert "a" in ids
    assert "b" in ids


@pytest.mark.verified
def test_interleave__unequal_length_results():
    """
    Purpose: Verifies correct interleaving when results have different chunk counts.
    Why this matters: The shorter result should not cause index errors; extras from the
        longer result must still appear.
    Setup summary: Results with 3 and 2 chunks; assert all 5 unique chunks appear in output.
    """
    results = [
        _result("q1", ["a", "b", "c"]),
        _result("q2", ["d", "e"]),
    ]
    out = interleave_search_results_round_robin(results)
    ids = [r.chunks[0].chunk_id for r in out]
    assert set(ids) == {"a", "b", "c", "d", "e"}
    # First two positions must be from pos-0 of each query
    assert ids[0] == "a"
    assert ids[1] == "d"
