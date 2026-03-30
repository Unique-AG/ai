"""Tests for ReferenceResolutionReplacer.

Covers:
- process(): pass-through and accumulation
- flush(): reference resolution, normalisation, hallucination removal, deduplication
- Cascade integration with StreamingPatternReplacer
- Property access before and after flush
"""

from __future__ import annotations

import pytest

from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
)
from unique_toolkit.framework_utilities.openai.streaming.reference_replacer import (
    ReferenceResolutionReplacer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def message_id() -> str:
    return "msg-test-123"


@pytest.fixture
def chunk_one() -> ContentChunk:
    """Single content chunk used as [1] reference target."""
    return ContentChunk(
        id="chunk-id-1",
        chunk_id="c1",
        key="source-one",
        title="Source One",
        url="https://example.com/1",
    )


@pytest.fixture
def chunk_two() -> ContentChunk:
    """Second content chunk used as [2] reference target."""
    return ContentChunk(
        id="chunk-id-2",
        chunk_id="c2",
        key="source-two",
        title="Source Two",
        url="https://example.com/2",
    )


@pytest.fixture
def two_chunks(chunk_one: ContentChunk, chunk_two: ContentChunk) -> list[ContentChunk]:
    return [chunk_one, chunk_two]


# ---------------------------------------------------------------------------
# process(): pass-through and accumulation
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_process__returns_delta_unchanged__for_single_call(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify process() returns the input delta unchanged (live preview).
    Why this matters: The streaming UI depends on receiving every token immediately;
        swallowing or modifying deltas would break the live preview.
    Setup summary: Create replacer, call process() once, assert return value equals input.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )

    result = replacer.process("Hello [1] world")

    assert result == "Hello [1] world"


@pytest.mark.ai
def test_AI_process__accumulates_all_deltas__across_multiple_calls(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify process() accumulates text from all calls before flush.
    Why this matters: flush() must operate on the complete text, not just the last delta.
    Setup summary: Call process() three times with distinct fragments, flush, check
        resolved_text contains all fragments.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    for fragment in ("Part A. ", "Part B [1]. ", "Part C."):
        replacer.process(fragment)

    replacer.flush()

    assert "Part A." in replacer.resolved_text
    assert "Part B" in replacer.resolved_text
    assert "Part C." in replacer.resolved_text


@pytest.mark.ai
def test_AI_process__returns_empty_string__for_empty_delta(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify process() handles empty delta gracefully.
    Why this matters: Real streams frequently emit empty deltas during tool-call phases.
    Setup summary: Call process(""), assert return value is "".
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )

    result = replacer.process("")

    assert result == ""


# ---------------------------------------------------------------------------
# flush(): empty accumulation
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_flush__returns_empty_string__when_nothing_accumulated(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() returns "" when no process() calls were made.
    Why this matters: flush() must not crash and must not add spurious text to the
        persistence layer's _full_text when the model produced no output text.
    Setup summary: Create replacer, call flush() immediately, assert return == "".
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )

    result = replacer.flush()

    assert result == ""


@pytest.mark.ai
def test_AI_flush__resolved_text_remains_empty__when_nothing_accumulated(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify resolved_text is "" after flush on an empty replacer.
    Why this matters: Handler code guards on `if ref_replacer.resolved_text` — an empty
        flush must not overwrite a valid accumulator message with an empty string.
    Setup summary: Create replacer, flush without process(), assert resolved_text == "".
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.flush()

    assert replacer.resolved_text == ""


# ---------------------------------------------------------------------------
# flush(): reference resolution happy paths
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_flush__converts_bracket_reference_to_superscript__with_matching_chunk(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() converts [1] to <sup>1</sup> when chunk is available.
    Why this matters: This is the core contract: downstream citation rendering requires
        <sup>N</sup> tags, not raw [N] brackets.
    Setup summary: Accumulate text containing [1], flush, assert resolved_text has <sup>1</sup>.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("The answer is here [1].")

    replacer.flush()

    assert "<sup>1</sup>" in replacer.resolved_text
    assert "[1]" not in replacer.resolved_text


@pytest.mark.ai
def test_AI_flush__builds_content_reference__with_correct_chunk_data(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() produces a ContentReference with the right chunk metadata.
    Why this matters: The frontend uses reference name and URL to display footnote links.
    Setup summary: Single chunk, single [1] citation, check reference fields.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("See [1] for details.")

    replacer.flush()

    assert len(replacer.references) == 1
    ref: ContentReference = replacer.references[0]
    assert ref.name == chunk_one.title
    assert ref.message_id == message_id
    assert ref.sequence_number == 1


@pytest.mark.ai
def test_AI_flush__resolves_multiple_references__to_independent_superscripts(
    message_id: str,
    two_chunks: list[ContentChunk],
) -> None:
    """
    Purpose: Verify flush() resolves multiple distinct [N] references correctly.
    Why this matters: Responses often cite several sources; each must become its own footnote.
    Setup summary: Text with [1] and [2], two chunks, assert both resolved and two references.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=two_chunks,
        message_id=message_id,
    )
    replacer.process("First fact [1] and second fact [2].")

    replacer.flush()

    assert "<sup>1</sup>" in replacer.resolved_text
    assert "<sup>2</sup>" in replacer.resolved_text
    assert len(replacer.references) == 2


# ---------------------------------------------------------------------------
# flush(): normalisation (second pass, idempotency)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_flush__normalises_unnormalised_source_pattern__before_resolving(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() handles text that still contains [source N] (not yet normalised).
    Why this matters: The second-pass _preprocess_message in flush() must be idempotent for
        already-normalised [N] text AND must still catch any missed [source N] patterns.
    Setup summary: Accumulate "[source 1]" (not yet normalised), flush, assert <sup>1</sup>.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("The answer is here [source 1].")

    replacer.flush()

    assert "<sup>1</sup>" in replacer.resolved_text


# ---------------------------------------------------------------------------
# flush(): hallucination removal
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_flush__removes_out_of_range_reference__when_no_matching_chunk(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() strips [N] when N exceeds the chunk list length.
    Why this matters: Models hallucinate references; leaving [N] in the final text
        exposes raw bracket noise to the frontend.
    Setup summary: One chunk, text cites [2] which has no matching chunk, assert [2] removed.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("This cites a hallucinated source [2].")

    replacer.flush()

    assert "[2]" not in replacer.resolved_text
    assert len(replacer.references) == 0


@pytest.mark.ai
def test_AI_flush__removes_all_bracket_references__when_chunks_is_empty(
    message_id: str,
) -> None:
    """
    Purpose: Verify flush() removes all [N] when no chunks are provided.
    Why this matters: Callers that pass an empty chunk list (e.g. no RAG context) must not
        end up with raw [N] noise in the persisted message.
    Setup summary: Empty chunk list, text with [1] and [3], flush, assert neither remains.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[],
        message_id=message_id,
    )
    replacer.process("References [1] and [3] have no matching chunks.")

    replacer.flush()

    assert "[1]" not in replacer.resolved_text
    assert "[3]" not in replacer.resolved_text
    assert len(replacer.references) == 0


# ---------------------------------------------------------------------------
# flush(): deduplication
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_flush__deduplicates_reference__when_same_chunk_cited_multiple_times(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() produces one ContentReference for a chunk cited more than once.
    Why this matters: The frontend renders one footnote entry per source; duplicate references
        would create confusing repeated footnotes.
    Setup summary: Text cites [1] twice, one chunk provided, assert one reference object.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("First mention [1] and again [1].")

    replacer.flush()

    assert len(replacer.references) == 1


# ---------------------------------------------------------------------------
# Property state before flush
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_resolved_text__is_empty_string__before_flush(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify resolved_text is "" before flush() is called.
    Why this matters: The handler reads resolved_text only after on_stream_end(); accessing
        it before that must return a safe empty-string sentinel, not raise.
    Setup summary: Create replacer and process text, read resolved_text without flushing.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("Some text [1].")

    assert replacer.resolved_text == ""


@pytest.mark.ai
def test_AI_references__is_empty_list__before_flush(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify references is [] before flush() is called.
    Why this matters: Same guard as resolved_text — handler must not touch message.references
        until after streaming completes.
    Setup summary: Create replacer and process text, read references without flushing.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("Some text [1].")

    assert replacer.references == []


@pytest.mark.ai
def test_AI_references__returns_copy__not_internal_list(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify references property returns a copy, not the internal list.
    Why this matters: Callers that mutate the returned list must not corrupt the replacer's
        internal state and affect subsequent reads.
    Setup summary: Flush, get references, mutate the returned list, re-read and assert unchanged.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("See [1].")
    replacer.flush()

    first_read = replacer.references
    first_read.clear()

    assert len(replacer.references) == 1


# ---------------------------------------------------------------------------
# flush() return value
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_flush__always_returns_empty_string__after_accumulation(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify flush() always returns "" regardless of accumulated content.
    Why this matters: The persistence layer's on_stream_end() appends the flush return
        to _full_text.  A non-empty return would duplicate already-released text.
    Setup summary: Accumulate several chunks with a reference, flush, assert return "".
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )
    replacer.process("Text with reference [1].")

    result = replacer.flush()

    assert result == ""


# ---------------------------------------------------------------------------
# Cascade integration with StreamingPatternReplacer
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_cascade__reference_in_pattern_replacer_tail__is_resolved_correctly(
    message_id: str,
    chunk_one: ContentChunk,
) -> None:
    """
    Purpose: Verify that a [N] reference held in the StreamingPatternReplacer's buffer tail
        is resolved when the cascade flush feeds it into ReferenceResolutionReplacer.process().
    Why this matters: Without cascade, the pattern replacer's 80-char tail bypasses the
        reference replacer; citations at end-of-response would never be converted to <sup>N</sup>.
    Setup summary: Feed a single short text to StreamingPatternReplacer, then simulate the
        cascade flush: call ref_replacer.process(pattern_flush) then ref_replacer.flush().
        Assert the tail reference is resolved.
    """
    pattern_replacer = StreamingPatternReplacer(
        replacements=NORMALIZATION_PATTERNS,
        max_match_length=NORMALIZATION_MAX_MATCH_LENGTH,
    )
    ref_replacer = ReferenceResolutionReplacer(
        content_chunks=[chunk_one],
        message_id=message_id,
    )

    # Simulate streaming: text is short enough to stay in pattern_replacer's buffer
    released = pattern_replacer.process("According to [source 1].")
    if released:
        ref_replacer.process(released)

    # Simulate cascade flush
    pattern_tail = pattern_replacer.flush()
    if pattern_tail:
        ref_replacer.process(pattern_tail)
    ref_replacer.flush()

    assert "<sup>1</sup>" in ref_replacer.resolved_text
    assert len(ref_replacer.references) == 1


@pytest.mark.ai
@pytest.mark.parametrize(
    "text, expected_sup, expected_ref_count",
    [
        ("See [1].", "<sup>1</sup>", 1),
        ("See [1] and [2].", "<sup>1</sup>", 2),
        ("No citations here.", None, 0),
        ("Hallucinated [5].", None, 0),
    ],
    ids=["single-ref", "two-refs", "no-refs", "hallucinated-ref"],
)
def test_AI_flush__parametrised_resolution_scenarios(
    message_id: str,
    two_chunks: list[ContentChunk],
    text: str,
    expected_sup: str | None,
    expected_ref_count: int,
) -> None:
    """
    Purpose: Table-driven test covering the main flush() resolution scenarios.
    Why this matters: Ensures the replacer handles common patterns correctly without
        brittle one-off tests for each variant.
    Setup summary: Parametrised text inputs with two available chunks; assert superscripts
        and reference counts match expectations.
    """
    replacer = ReferenceResolutionReplacer(
        content_chunks=two_chunks,
        message_id=message_id,
    )
    replacer.process(text)
    replacer.flush()

    if expected_sup is not None:
        assert expected_sup in replacer.resolved_text
    assert len(replacer.references) == expected_ref_count
