"""Tests for streaming pattern replacement and SDK reference conversion."""

from __future__ import annotations

import re

import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
    chunks_to_sdk_references,
    extract_cited_sequence_numbers,
    filter_cited_sdk_references,
)


@pytest.mark.ai
def test_streaming_pattern_replacer__split_match_across_chunks__emits_sup_when_complete():
    """
    Purpose: Ensure buffered streaming replaces citation tokens split across chunk boundaries.
    Why this matters: Without buffering, partial regex matches would corrupt streamed UI text.
    Setup summary: Feed "[sour" then "ce 1]" through NORMALIZATION_PATTERNS; flush; expect "<sup>1</sup>".
    """
    replacer = StreamingPatternReplacer(
        NORMALIZATION_PATTERNS, max_match_length=NORMALIZATION_MAX_MATCH_LENGTH
    )
    out1 = replacer.process("[sour")
    out2 = replacer.process("ce 1]")
    tail = replacer.flush()
    assert out1 == ""
    assert out2 == ""
    assert tail == "<sup>1</sup>"


@pytest.mark.ai
def test_streaming_pattern_replacer__max_match_length_zero__releases_full_delta_each_call():
    """
    Purpose: Document behaviour when max_match_length is 0 (no trailing hold-back window).
    Why this matters: Callers that set 0 expect immediate forwarding without a suffix buffer.
    Setup summary: With max_match_length=0 the implementation returns the raw accumulated chunk
    for that call without applying configured replacements in-process; buffer is cleared each time.
    """
    replacer = StreamingPatternReplacer([(r"a", "X")], max_match_length=0)
    assert replacer.process("ab") == "ab"
    assert replacer.flush() == ""


@pytest.mark.ai
def test_streaming_pattern_replacer__flush__applies_replacements_to_remainder():
    """
    Purpose: Confirm flush() runs replacements on the final buffer and clears state.
    Why this matters: Trailing buffered characters must be normalized when the stream ends.
    Setup summary: One chunk shorter than the hold-back window releases nothing; flush emits ``<sup>1</sup>``.
    """
    replacer = StreamingPatternReplacer(
        NORMALIZATION_PATTERNS, max_match_length=NORMALIZATION_MAX_MATCH_LENGTH
    )
    assert replacer.process("[source 1]") == ""
    assert replacer.flush() == "<sup>1</sup>"
    assert replacer.flush() == ""


@pytest.mark.ai
def test_chunks_to_sdk_references__maps_chunks_to_sdk_shape():
    """
    Purpose: Validate ContentChunk → unique_sdk.Message.Reference conversion.
    Why this matters: Downstream SDK calls expect stable sequence numbers and source IDs.
    Setup summary: Two chunks with title/key/url; assert sequence numbers and sourceId formatting.
    """
    chunks = [
        ContentChunk(
            id="c1",
            chunk_id=None,
            key="k1",
            title="Doc A",
            text="",
            start_page=1,
            end_page=1,
            order=0,
            object="search_result",
            url="https://example.com/a",
            internally_stored_at=None,
        ),
        ContentChunk(
            id="c2",
            chunk_id="ch2",
            key=None,
            title=None,
            text="",
            start_page=1,
            end_page=1,
            order=1,
            object="search_result",
            url=None,
            internally_stored_at=None,
        ),
    ]
    refs = chunks_to_sdk_references(chunks)
    assert len(refs) == 2
    assert refs[0]["sequenceNumber"] == 1
    assert refs[0]["name"] == "Doc A"
    assert refs[0]["url"] == "https://example.com/a"
    assert refs[0]["sourceId"] == "c1"
    assert refs[1]["sequenceNumber"] == 2
    assert refs[1]["name"] == "k1"
    assert refs[1]["url"] == "unique://content/c2"
    assert refs[1]["sourceId"] == "c2_ch2"


@pytest.mark.ai
def test_streaming_pattern_replacer__callable_replacement__used_for_multi_source():
    """
    Purpose: Ensure callable replacements run in the streaming pipeline.
    Why this matters: Multi-source patterns like ``[source: 1, 2]`` rely on callables, not only strings.
    Setup summary: Single chunk ``[source: 1, 2]``; flush; expect ``<sup>1</sup><sup>2</sup>``.
    """
    replacer = StreamingPatternReplacer(
        NORMALIZATION_PATTERNS, max_match_length=NORMALIZATION_MAX_MATCH_LENGTH
    )
    combined = replacer.process("[source: 1, 2]") + replacer.flush()
    assert combined == "<sup>1</sup><sup>2</sup>"


def _make_chunk(idx: int) -> ContentChunk:
    return ContentChunk(
        id=f"c{idx}",
        chunk_id=None,
        key=None,
        title=f"Doc {idx}",
        text="",
        start_page=1,
        end_page=1,
        order=idx,
        object="search_result",
        url=f"https://example.com/{idx}",
        internally_stored_at=None,
    )


@pytest.mark.ai
def test_extract_cited_sequence_numbers__finds_only_sup_tagged_numbers():
    """
    Purpose: Only numbers wrapped in <sup> should be treated as cited.
    Why this matters: Streaming must not count incidental digits in the body as citations.
    Setup summary: Mixed text with literal digits and two <sup>...</sup> markers; expect the set ``{1, 3}``.
    """
    text = "Intro 42 and <sup>1</sup> plus more <sup>3</sup> and trailing 7"
    assert extract_cited_sequence_numbers(text) == {1, 3}


@pytest.mark.ai
def test_filter_cited_sdk_references__returns_empty_when_no_citations_yet():
    """
    Purpose: Before the model cites anything, no references should be surfaced.
    Why this matters: Fixes the bug where all retrieved chunks were shown up front.
    Setup summary: Two chunks available, streamed text has no <sup>; expect an empty list.
    """
    chunks = [_make_chunk(1), _make_chunk(2)]
    assert filter_cited_sdk_references(chunks, "hello world") == []


@pytest.mark.ai
def test_filter_cited_sdk_references__returns_only_cited_chunks():
    """
    Purpose: Only chunks whose 1-based index appears as <sup>N</sup> should be returned.
    Why this matters: The frontend shows whatever references the SDK message carries; others must be hidden.
    Setup summary: Three chunks, text cites <sup>1</sup> and <sup>3</sup>; expect references 1 and 3, in order.
    """
    chunks = [_make_chunk(1), _make_chunk(2), _make_chunk(3)]
    refs = filter_cited_sdk_references(chunks, "x <sup>1</sup> y <sup>3</sup>")
    assert [ref["sequenceNumber"] for ref in refs] == [1, 3]


@pytest.mark.ai
def test_filter_cited_sdk_references__ignores_out_of_range_citations():
    """
    Purpose: Citations that point outside the chunk list should be dropped silently.
    Why this matters: Models sometimes hallucinate source numbers; we should not invent references.
    Setup summary: Two chunks, text cites <sup>5</sup>; expect an empty list.
    """
    chunks = [_make_chunk(1), _make_chunk(2)]
    assert filter_cited_sdk_references(chunks, "hi <sup>5</sup>") == []


@pytest.mark.ai
def test_streaming_pattern_replacer__compiled_pattern__accepted_in_init():
    """
    Purpose: Verify compiled ``re.Pattern`` objects work alongside string patterns.
    Why this matters: Callers may pre-compile patterns for reuse or performance.
    Setup summary: Pass (re.compile(r"x"), "y"); process "xx"; expect "yy".
    """
    replacer = StreamingPatternReplacer([(re.compile("x"), "y")], max_match_length=0)
    assert replacer.process("xx") == "yy"
