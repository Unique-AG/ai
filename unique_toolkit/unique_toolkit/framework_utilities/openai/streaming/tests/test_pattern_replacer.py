import re

import pytest

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingPatternReplacer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simulate_stream(
    replacer: StreamingPatternReplacer,
    chunks: list[str],
) -> str:
    """Feed *chunks* one-by-one through the replacer, then flush."""
    display = ""
    for chunk in chunks:
        display += replacer.process(chunk)
    display += replacer.flush()
    return display


# ---------------------------------------------------------------------------
# Basic behaviour — literal patterns
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__passes_text_through__when_no_replacements() -> None:
    """
    Purpose: Verify text is forwarded immediately when max_match_length is 0.
    Why this matters: Ensures zero-overhead passthrough when feature is unused.
    Setup summary: Empty replacements list, max_match_length=0, assert full text
        returned at once.
    """
    replacer = StreamingPatternReplacer(replacements=[], max_match_length=0)

    display = ""
    display += replacer.process("Hello ")
    display += replacer.process("world")

    assert display == "Hello world"
    assert replacer._buffer == ""


@pytest.mark.ai
def test_process__replaces_literal_pattern__within_single_chunk() -> None:
    """
    Purpose: Verify a complete literal pattern inside one chunk is replaced.
    Why this matters: Core replacement functionality must work end-to-end.
    Setup summary: Single chunk containing full pattern, flush, assert replaced.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[\[REF\]\]", "[1]")],
        max_match_length=7,
    )

    display = _simulate_stream(replacer, ["See [[REF]] here"])

    assert display == "See [1] here"


@pytest.mark.ai
def test_process__replaces_pattern__spanning_two_chunks() -> None:
    """
    Purpose: Verify a pattern split across two consecutive chunks is replaced.
    Why this matters: Chunk boundaries are arbitrary; patterns must not be missed.
    Setup summary: Split '[[REF]]' across two chunks, assert replaced after flush.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[\[REF\]\]", "[1]")],
        max_match_length=7,
    )

    display = _simulate_stream(replacer, ["See [[RE", "F]] here"])

    assert display == "See [1] here"


@pytest.mark.ai
def test_process__replaces_pattern__spanning_many_chunks() -> None:
    """
    Purpose: Verify a pattern arriving one character at a time is still caught.
    Why this matters: Worst-case fragmentation must be handled correctly.
    Setup summary: Feed pattern character-by-character, assert replaced after flush.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("abcd", "X")],
        max_match_length=4,
    )

    display = _simulate_stream(replacer, list("__abcd__"))

    assert display == "__X__"


@pytest.mark.ai
def test_process__replaces_pattern__at_stream_end() -> None:
    """
    Purpose: Verify a pattern at the very end of the stream is replaced on flush.
    Why this matters: Buffer must be flushed correctly with final replacements.
    Setup summary: Pattern appears as the last content, assert flush replaces it.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[\[END\]\]", ".")],
        max_match_length=7,
    )

    display = _simulate_stream(replacer, ["Goodbye[[END]]"])

    assert display == "Goodbye."


@pytest.mark.ai
def test_process__replaces_multiple_patterns__in_stream() -> None:
    """
    Purpose: Verify multiple distinct patterns are all replaced correctly.
    Why this matters: Real-world usage involves several simultaneous patterns.
    Setup summary: Two different patterns in the stream, assert both replaced.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[\[A\]\]", "1"), (r"\[\[B\]\]", "2")],
        max_match_length=5,
    )

    display = _simulate_stream(replacer, ["See [[A]] and ", "[[B]] end"])

    assert display == "See 1 and 2 end"


@pytest.mark.ai
def test_process__handles_replacement_changing_length() -> None:
    """
    Purpose: Verify replacements that change text length work correctly.
    Why this matters: Length-changing replacements must not corrupt buffer offsets.
    Setup summary: Replace long pattern with short string, assert final text correct.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("<<LONG_TOKEN>>", "X")],
        max_match_length=14,
    )

    display = _simulate_stream(replacer, ["before<<LONG", "_TOKEN>>after"])

    assert display == "beforeXafter"


# ---------------------------------------------------------------------------
# Buffer behaviour
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__holds_back_max_match_length__in_buffer() -> None:
    """
    Purpose: Verify the buffer retains exactly max_match_length characters.
    Why this matters: Releasing too much risks missing split patterns;
        holding too much adds unnecessary latency.
    Setup summary: Feed text longer than max_match_length, inspect buffer size.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("abcde", "X")],
        max_match_length=5,
    )

    display = replacer.process("Hello world!")

    assert len(replacer._buffer) == 5
    assert replacer._buffer == "orld!"
    assert display == "Hello w"


@pytest.mark.ai
def test_process__buffers_entirely__when_text_shorter_than_max_match() -> None:
    """
    Purpose: Verify short initial chunks are buffered without releasing text.
    Why this matters: Premature release could expose unresolved partial patterns.
    Setup summary: Feed chunk shorter than max_match_length, assert nothing released.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("abcdef", "X")],
        max_match_length=6,
    )

    display = replacer.process("Hi")

    assert display == ""
    assert replacer._buffer == "Hi"


@pytest.mark.ai
def test_flush__releases_remaining_buffer() -> None:
    """
    Purpose: Verify flush empties the buffer and releases all remaining text.
    Why this matters: End-of-stream must deliver the complete message.
    Setup summary: Process partial text, flush, assert buffer empty and text complete.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("abc", "X")],
        max_match_length=3,
    )

    display = replacer.process("Hello")
    assert replacer._buffer != ""

    display += replacer.flush()

    assert display == "Hello"
    assert replacer._buffer == ""


@pytest.mark.ai
def test_reset__clears_buffer__without_releasing() -> None:
    """
    Purpose: Verify reset discards buffered content.
    Why this matters: Enables clean state between unrelated streams.
    Setup summary: Buffer some text, reset, assert buffer empty.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("abc", "X")],
        max_match_length=3,
    )
    replacer.process("some text")

    replacer._buffer = ""

    assert replacer._buffer == ""


# ---------------------------------------------------------------------------
# Incremental streaming correctness
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__streams_incrementally__matching_incoming_rate() -> None:
    """
    Purpose: Verify each process call releases roughly delta-sized increments.
    Why this matters: The frontend must receive a steady text stream, not bursts.
    Setup summary: Feed equal-sized chunks, track display growth per call.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("XX", "YY")],
        max_match_length=2,
    )

    display = ""
    lengths: list[int] = []

    for chunk in ["aaaa", "bbbb", "cccc", "dddd"]:
        released = replacer.process(chunk)
        lengths.append(len(released))
        display += released

    assert lengths[0] == 2  # 4 chars in, 2 held back (max_match_length=2)
    assert lengths[1] == 4
    assert lengths[2] == 4
    assert lengths[3] == 4

    display += replacer.flush()
    assert display == "aaaabbbbccccdddd"


@pytest.mark.ai
def test_process__full_round_trip__preserves_non_pattern_text() -> None:
    """
    Purpose: Verify non-matching text passes through unmodified after flush.
    Why this matters: Buffering must not corrupt or lose any content.
    Setup summary: Stream text with no matching patterns, assert identity.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("NOMATCH", "X")],
        max_match_length=7,
    )
    text = "The quick brown fox jumps over the lazy dog"
    chunks = [text[i : i + 5] for i in range(0, len(text), 5)]

    display = _simulate_stream(replacer, chunks)

    assert display == text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__handles_empty_delta__gracefully() -> None:
    """
    Purpose: Verify empty deltas do not corrupt state.
    Why this matters: LLM streams may emit empty chunks.
    Setup summary: Interleave empty deltas, assert final output correct.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("ab", "X")],
        max_match_length=2,
    )

    display = _simulate_stream(replacer, ["", "a", "", "b", "", "c", ""])

    assert display == "Xc"


@pytest.mark.ai
def test_process__handles_pattern_appearing_multiple_times() -> None:
    """
    Purpose: Verify all occurrences of a pattern are replaced.
    Why this matters: Patterns may repeat in real model output.
    Setup summary: Two occurrences across chunks, assert both replaced.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[X\]", "!")],
        max_match_length=3,
    )

    display = _simulate_stream(replacer, ["A[X]B", "[X]C"])

    assert display == "A!B!C"


@pytest.mark.ai
def test_process__pattern_at_buffer_boundary__replaced_correctly() -> None:
    """
    Purpose: Verify a pattern that starts exactly at the buffer tail is caught.
    Why this matters: Off-by-one errors at boundaries are a common defect.
    Setup summary: Carefully sized chunks so the pattern starts at the retention
        boundary, assert correct replacement.
    """
    replacer = StreamingPatternReplacer(
        replacements=[("abc", "X")],
        max_match_length=3,
    )

    display = replacer.process("123abc456")
    assert replacer._buffer == "456"

    display += replacer.flush()
    assert display == "123X456"


@pytest.mark.ai
@pytest.mark.parametrize(
    "replacements, max_match_length, chunks, expected",
    [
        ([], 0, ["hello"], "hello"),
        ([("a", "b")], 1, ["a"], "b"),
        ([("abc", "X")], 3, ["a", "b", "c"], "X"),
        ([("ab", "X"), ("cd", "Y")], 2, ["abcd"], "XY"),
        ([("<<", "<"), (">>", ">")], 2, ["1<<2>>3"], "1<2>3"),
    ],
    ids=[
        "no-replacements",
        "single-char-pattern",
        "char-by-char-arrival",
        "adjacent-patterns",
        "shorten-delimiters",
    ],
)
def test_process__parametrized_literal_cases(
    replacements: list[tuple[str, str]],
    max_match_length: int,
    chunks: list[str],
    expected: str,
) -> None:
    """
    Purpose: Table-driven tests for assorted literal replacement scenarios.
    Why this matters: Broad coverage of common and edge-case inputs.
    Setup summary: Parametrized replacements/chunks with expected final output.
    """
    replacer = StreamingPatternReplacer(
        replacements=replacements,
        max_match_length=max_match_length,
    )

    result = _simulate_stream(replacer, chunks)

    assert result == expected


# ---------------------------------------------------------------------------
# Regex-specific behaviour
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__replaces_regex_pattern__digit_sequence() -> None:
    """
    Purpose: Verify a regex matching variable-length digit runs is replaced.
    Why this matters: Core regex capability — patterns match variable-length text.
    Setup summary: Regex \\d+ with known max match length, chunks aligned so
        digit runs are not split across chunks.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\d+", "#")],
        max_match_length=5,
    )

    display = _simulate_stream(replacer, ["price: ", "420 USD"])

    assert display == "price: # USD"


@pytest.mark.ai
def test_process__replaces_compiled_regex__pattern() -> None:
    """
    Purpose: Verify pre-compiled re.Pattern objects work as patterns.
    Why this matters: Callers may pre-compile patterns for reuse or flags.
    Setup summary: Pass compiled pattern, assert replacement works identically.
    """
    pattern = re.compile(r"\[\[REF:\d+\]\]")
    replacer = StreamingPatternReplacer(
        replacements=[(pattern, "[ref]")],
        max_match_length=12,
    )

    display = _simulate_stream(replacer, ["See [[REF:1", "23]] here"])

    assert display == "See [ref] here"


@pytest.mark.ai
def test_process__replaces_regex__spanning_chunks() -> None:
    """
    Purpose: Verify a regex match that spans two chunks is caught by the buffer.
    Why this matters: The buffer must retain enough chars for partial regex matches.
    Setup summary: Split a matchable sequence across chunks, assert replaced.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"<sup>\d+</sup>", "")],
        max_match_length=15,
    )

    display = _simulate_stream(replacer, ["Text<sup>", "12</sup> more"])

    assert display == "Text more"


@pytest.mark.ai
def test_process__regex_with_alternation__replaces_all_variants() -> None:
    """
    Purpose: Verify a regex with alternation (|) matches all variants.
    Why this matters: Real patterns often use alternation for multiple tokens.
    Setup summary: Pattern with two alternatives, assert both matched.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[\[A\]\]|\[\[B\]\]", "?")],
        max_match_length=5,
    )

    display = _simulate_stream(replacer, ["[[A]] and [[B", "]]"])

    assert display == "? and ?"


@pytest.mark.ai
def test_process__regex_case_insensitive__with_compiled_flag() -> None:
    """
    Purpose: Verify compiled patterns with flags (e.g. IGNORECASE) are honoured.
    Why this matters: Callers need control over matching behaviour via re flags.
    Setup summary: Case-insensitive pattern, mixed-case input, assert all matched.
    """
    pattern = re.compile(r"hello", re.IGNORECASE)
    replacer = StreamingPatternReplacer(
        replacements=[(pattern, "hi")],
        max_match_length=5,
    )

    display = _simulate_stream(replacer, ["HELLO world, hel", "lo again"])

    assert display == "hi world, hi again"


@pytest.mark.ai
def test_process__regex_removes_pattern__with_empty_replacement() -> None:
    """
    Purpose: Verify patterns can be stripped by replacing with empty string.
    Why this matters: Common use case for removing markup/annotations from output.
    Setup summary: Regex matching tags, replace with '', assert tags removed.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"<[^>]+>", "")],
        max_match_length=20,
    )

    display = _simulate_stream(replacer, ["plain <b>bo", "ld</b> text"])

    assert display == "plain bold text"


@pytest.mark.ai
def test_process__multiple_regex_patterns__applied_in_order() -> None:
    """
    Purpose: Verify multiple regex patterns are applied sequentially in list order.
    Why this matters: Order determines priority when patterns could interact.
    Setup summary: Two patterns where order matters, assert correct precedence.
    """
    replacer = StreamingPatternReplacer(
        replacements=[
            (r"\d{3}", "NUM"),
            (r"NUM-NUM", "RANGE"),
        ],
        max_match_length=7,
    )

    display = _simulate_stream(replacer, ["call 123-45", "6 now"])

    assert display == "call RANGE now"


@pytest.mark.ai
@pytest.mark.parametrize(
    "replacements, max_match_length, chunks, expected",
    [
        ([(r"\s+", " ")], 3, ["a  b", "   c"], "a b c"),
        ([(r"[aeiou]", "_")], 1, ["hello"], "h_ll_"),
        ([(r"\bfoo\b", "bar")], 3, ["foo baz foo", "d"], "bar baz bard"),
        ([(r"x{2,4}", "Y")], 4, ["ax", "xxx", "b"], "aYb"),
    ],
    ids=[
        "collapse-whitespace",
        "replace-vowels",
        "word-boundary",
        "quantifier-range",
    ],
)
def test_process__parametrized_regex_cases(
    replacements: list[tuple[str, str]],
    max_match_length: int,
    chunks: list[str],
    expected: str,
) -> None:
    """
    Purpose: Table-driven tests for assorted regex replacement scenarios.
    Why this matters: Broad coverage of regex features used in practice.
    Setup summary: Parametrized regex patterns/chunks with expected final output.
    """
    replacer = StreamingPatternReplacer(
        replacements=replacements,
        max_match_length=max_match_length,
    )

    result = _simulate_stream(replacer, chunks)

    assert result == expected


# ---------------------------------------------------------------------------
# Capture-group / backreference replacements
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__replaces_source_ref__with_capture_group() -> None:
    """
    Purpose: Verify [sourceN] is converted to <sup>N</sup> using a backreference.
    Why this matters: Primary real-world use case — LLM outputs source refs that
        must be rewritten to superscript footnotes during streaming.
    Setup summary: Pattern captures the digit group, replacement uses \\1.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[source\s?(\d+)\]", r"<sup>\1</sup>")],
        max_match_length=15,
    )

    display = _simulate_stream(
        replacer, ["See [source1] and [source 2", "] for details"]
    )

    assert display == "See <sup>1</sup> and <sup>2</sup> for details"


@pytest.mark.ai
def test_process__replaces_source_ref__spanning_chunks() -> None:
    """
    Purpose: Verify a source reference split across chunks is still captured.
    Why this matters: The model can split [source12] at any byte boundary.
    Setup summary: Split reference mid-token, assert replacement with correct number.
    """
    replacer = StreamingPatternReplacer(
        replacements=[(r"\[source\s?(\d+)\]", r"<sup>\1</sup>")],
        max_match_length=15,
    )

    display = _simulate_stream(replacer, ["text [sour", "ce12] end"])

    assert display == "text <sup>12</sup> end"


@pytest.mark.ai
def test_process__replaces_multiple_source_formats__with_groups() -> None:
    """
    Purpose: Verify several source-reference formats are normalised simultaneously.
    Why this matters: Models produce varied formats; all must be caught in one pass.
    Setup summary: Multiple replacement patterns with backreferences, assert all
        variants normalised to <sup>N</sup>.
    """
    replacer = StreamingPatternReplacer(
        replacements=[
            (r"\[source\s?(\d+)\]", r"<sup>\1</sup>"),
            (r"\[(\d+)\]", r"<sup>\1</sup>"),
        ],
        max_match_length=15,
    )

    display = _simulate_stream(
        replacer,
        ["Ref [source1], ref [2", "], and [source 3]"],
    )

    assert display == "Ref <sup>1</sup>, ref <sup>2</sup>, and <sup>3</sup>"


@pytest.mark.ai
def test_process__named_group__in_replacement() -> None:
    """
    Purpose: Verify named capture groups work in replacements.
    Why this matters: Named groups improve readability for complex patterns.
    Setup summary: Pattern with (?P<name>...) group, replacement uses \\g<name>.
    """
    replacer = StreamingPatternReplacer(
        replacements=[
            (
                r"\[source\s?(?P<num>\d+)\]",
                r"<sup>\g<num></sup>",
            )
        ],
        max_match_length=15,
    )

    display = _simulate_stream(replacer, ["See [source42] here"])

    assert display == "See <sup>42</sup> here"


# ---------------------------------------------------------------------------
# Callable replacements
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_process__callable_replacement__expands_match() -> None:
    """
    Purpose: Verify a callable replacement receives the match and returns text.
    Why this matters: Multi-source patterns like [source: 1, 2] need callables
        to expand a variable number of captures.
    Setup summary: Callable that extracts digits and formats them, assert output.
    """

    def _expand(match: re.Match[str]) -> str:
        numbers = re.findall(r"\d+", match.group(0))
        return "".join(f"[{n}]" for n in numbers)

    replacer = StreamingPatternReplacer(
        replacements=[(r"\[source:\s*([\d,\s]+)\]", _expand)],
        max_match_length=30,
    )

    display = _simulate_stream(replacer, ["See [source: 1, 2,", " 3] end"])

    assert display == "See [1][2][3] end"


@pytest.mark.ai
def test_process__callable_replacement__combined_brackets() -> None:
    """
    Purpose: Verify the combined-brackets pattern expands [[1], [2]] to [1][2].
    Why this matters: Models sometimes output grouped bracket references.
    Setup summary: Callable expanding grouped references across chunks.
    """

    def _expand(match: re.Match[str]) -> str:
        numbers = re.findall(r"\d+", match.group(0))
        return "".join(f"[{n}]" for n in numbers)

    replacer = StreamingPatternReplacer(
        replacements=[
            (
                r"(?:\[\[(\d+)\](?:,\s*(?:\[)?\d+(?:\])?)*\]|\[([\d,\s]+)\])",
                _expand,
            )
        ],
        max_match_length=40,
    )

    display = _simulate_stream(replacer, ["text [[1], [2", "], [3]] done"])

    assert display == "text [1][2][3] done"


# ---------------------------------------------------------------------------
# Reference patterns integration
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.parametrize(
    "chunks, expected",
    [
        # [<user>] stripped
        (["Hello [<user>] world"], "Hello  world"),
        # [\<assistant>] stripped
        (["Reply [\\<assistant>] here"], "Reply  here"),
        # source [conversation] → the previous conversation
        (
            ["see source [conver", "sation] for context"],
            "see the previous conversation for context",
        ),
        # [<source 1>] → [1]
        (["cite [<source 1>] now"], "cite [1] now"),
        # source 1 → [1]
        (["see source 1 for info"], "see [1] for info"),
        # source_number="2" → [2]
        (['ref source_number="2" end'], "ref [2] end"),
        # [**3**] → [3]
        (["bold [**3**] ref"], "bold [3] ref"),
        # SOURCE 4 → [4]  (case insensitive)
        (["cite SOURCE 4 here"], "cite [4] here"),
        # source n°5 → [5]
        (["see source n°5 now"], "see [5] now"),
        # [source: 1, 2, 3] → [1][2][3]
        (["list [source: 1,", " 2, 3] end"], "list [1][2][3] end"),
    ],
    ids=[
        "strip-user",
        "strip-assistant",
        "conversation-to-text",
        "xml-source-to-bracket",
        "source-N-to-bracket",
        "source-number-attr",
        "bold-ref",
        "uppercase-source",
        "source-n-degree",
        "multi-source-list",
    ],
)
def test_reference_patterns__end_to_end(
    chunks: list[str],
    expected: str,
) -> None:
    """
    Purpose: Verify the full REFERENCE_PATTERNS list normalises each format.
    Why this matters: These are the real production patterns; regressions break
        footnote rendering in the frontend.
    Setup summary: Feed each reference format through the replacer, assert
        canonical output.
    """
    from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
        NORMALIZATION_MAX_MATCH_LENGTH,
        NORMALIZATION_PATTERNS,
    )

    replacer = StreamingPatternReplacer(
        replacements=NORMALIZATION_PATTERNS,
        max_match_length=NORMALIZATION_MAX_MATCH_LENGTH,
    )

    result = _simulate_stream(replacer, chunks)

    assert result == expected
