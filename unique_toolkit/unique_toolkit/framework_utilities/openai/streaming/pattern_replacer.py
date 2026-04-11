from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol

import unique_sdk

if TYPE_CHECKING:
    from unique_toolkit.content.schemas import ContentChunk

Replacement = str | Callable[[re.Match[str]], str]

NormalizationReplacement = Replacement
"""A regex replacement: either a string (may contain backreferences) or a
callable receiving a ``re.Match`` and returning a string."""

NormalizationPattern = tuple[str | re.Pattern[str], NormalizationReplacement]


def _expand_source_list_to_sup(match: re.Match[str]) -> str:
    """Expand ``[source: 1, 2, 3]`` into ``<sup>1</sup><sup>2</sup><sup>3</sup>``."""
    numbers = re.findall(r"\d+", match.group(0))
    return "".join(f"<sup>{n}</sup>" for n in numbers)


def _expand_source_list_to_brackets(match: re.Match[str]) -> str:
    """Expand ``[source: 1, 2, 3]`` into ``[1][2][3]``."""
    numbers = re.findall(r"\d+", match.group(0))
    return "".join(f"[{n}]" for n in numbers)


# ── Patterns shared by streaming and batch (strip non-source refs) ────────
_STRIP_NON_SOURCE_PATTERNS: list[NormalizationPattern] = [
    (r"(?i)\[(\\)?(<)?user(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?assistant(>)?\]", ""),
    (r"(?i)source[\s]?\[(\\)?(<)?conversation(>)?\]", "the previous conversation"),
    (r"(?i)\[(\\)?(<)?previous[_,\s]conversation(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?past[_,\s]conversation(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?previous[_,\s]?answer(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?previous[_,\s]question(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?conversation(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?none(>)?\]", ""),
]

NORMALIZATION_PATTERNS: list[NormalizationPattern] = [
    *_STRIP_NON_SOURCE_PATTERNS,
    # ── Normalise source references to <sup>N</sup> (streaming) ─────────
    # Bracket-consuming variants first so the outer [...] are removed too.
    # The bare fallbacks use (?<!\[) so they don't fire mid-stream when the
    # buffer holds "[source1" before the closing "]" has arrived — that would
    # strand the "[" and produce "[<sup>1</sup>]".
    (r"\[(\\)?<source[\s]?(\d+)>\]", r"<sup>\2</sup>"),  # [<source0>]
    (
        r"(?i)\[source[\s_]?(\d+)\]",
        r"<sup>\1</sup>",
    ),  # [source0], [Source 0], [source_0]
    (r"(?<!\[)source[\s_]?(\d+)", r"<sup>\1</sup>"),  # source0 not preceded by [
    (r'source_number="(\d+)"', r"<sup>\1</sup>"),
    (r"\[\*\*(\d+)\*\*\]", r"<sup>\1</sup>"),
    (
        r"(?i)(?<!\[)source[\s]?(\d+)",
        r"<sup>\1</sup>",
    ),  # SOURCE0, Source 0 not preceded by [
    (r"(?i)source[\s]?n°(\d+)", r"<sup>\1</sup>"),
    (r"\[(\\)?\[?<\[(\d+)\]?\]>\]", r"<sup>\2</sup>"),
    # ── Multi-source references (callable replacements) ────────────────
    (r"\[source:\s*([\d,\s]+)\]", _expand_source_list_to_sup),
    (
        r"(?:\[\[(\d+)\](?:,\s*(?:\[)?\d+(?:\])?)*\]|\[([\d,\s]+)\])",
        _expand_source_list_to_sup,
    ),
]
"""Normalisation rules that convert model-emitted citation formats
to the canonical ``<sup>N</sup>`` superscript notation (for streaming)."""

BATCH_NORMALIZATION_PATTERNS: list[NormalizationPattern] = [
    *_STRIP_NON_SOURCE_PATTERNS,
    # ── Normalise source references to [N] (batch processing) ───────────
    # Batch path needs [N] so _extract_numbers_in_brackets and
    # _add_footnotes_to_text can work correctly.
    (r"\[(\\)?<source[\s]?(\d+)>\]", r"[\2]"),  # [<source0>] → [0]
    (r"(?i)\[source[\s_]?(\d+)\]", r"[\1]"),  # [source0] → [0]
    (r"(?<!\[)source[\s_]?(\d+)", r"[\1]"),  # source0 → [0]
    (r'source_number="(\d+)"', r"[\1]"),
    (r"\[\*\*(\d+)\*\*\]", r"[\1]"),  # [**1**] → [1]
    (r"(?i)(?<!\[)source[\s]?(\d+)", r"[\1]"),  # SOURCE0 → [0]
    (r"(?i)source[\s]?n°(\d+)", r"[\1]"),  # SOURCE n°1 → [1]
    (r"\[(\\)?\[?<\[(\d+)\]?\]>\]", r"[\2]"),
    # ── Multi-source references ────────────────────────────────────────
    (r"\[source:\s*([\d,\s]+)\]", _expand_source_list_to_brackets),
    (
        r"(?:\[\[(\d+)\](?:,\s*(?:\[)?\d+(?:\])?)*\]|\[([\d,\s]+)\])",
        _expand_source_list_to_brackets,
    ),
]
"""Normalisation rules that convert model-emitted citation formats
to the canonical ``[N]`` bracket notation (for batch processing)."""

NORMALIZATION_MAX_MATCH_LENGTH = 80
"""Upper bound on characters any single pattern can match.  Sized for
multi-source patterns like ``[source: 1, 2, ..., 20]``."""


def chunks_to_sdk_references(
    chunks: list[ContentChunk],
) -> list[unique_sdk.Message.Reference]:
    """Convert ``ContentChunk`` objects to ``unique_sdk.Message.Reference`` TypedDicts."""
    return [
        unique_sdk.Message.Reference(
            name=chunk.title or chunk.key or chunk.id or "",
            url=chunk.url or f"unique://content/{chunk.id}",
            sequenceNumber=i + 1,
            sourceId=(
                f"{chunk.id}_{chunk.chunk_id}" if chunk.chunk_id else chunk.id or ""
            ),
            source="node-ingestion-chunks",
            description=None,
            originalIndex=[i + 1],
        )
        for i, chunk in enumerate(chunks)
    ]


class StreamingReplacerProtocol(Protocol):
    def process(self, delta: str) -> str: ...
    def flush(self) -> str: ...


class StreamingPatternReplacer:
    """Buffers streaming text chunks to safely apply regex-based pattern
    replacements before forwarding to the frontend.

    Holds back up to ``max_match_length`` characters to ensure partial
    pattern matches at chunk boundaries are resolved correctly before any
    text is released.

    Patterns should have unambiguous boundaries (e.g. delimiters like
    ``[[...]]`` or ``<sup>...</sup>``) so that a partial arrival cannot
    form a shorter valid match.  Open-ended patterns such as bare
    ``\\d+`` may match eagerly within a single chunk before the next
    chunk can extend the match.

    Args:
        replacements: List of ``(pattern, replacement)`` pairs.  Each
            *pattern* is either a regex string or a compiled
            ``re.Pattern``.  Strings are compiled once at init time.
            *replacement* is either a string (may contain backreferences
            like ``\\1``) or a callable that receives a ``re.Match``
            and returns a string.
            Patterns are applied sequentially in the order given.
        max_match_length: Upper bound on the number of characters any
            single pattern can match.  Determines how many trailing
            characters are retained in the buffer between calls.
    """

    def __init__(
        self,
        replacements: Sequence[tuple[str | re.Pattern[str], Replacement]],
        max_match_length: int,
    ) -> None:
        self._replacements = [
            (re.compile(p) if isinstance(p, str) else p, repl)
            for p, repl in replacements
        ]
        self._max_match_length = max_match_length
        self._buffer = ""

    def process(self, delta: str) -> str:
        """Process a new streaming chunk.

        Appends *delta* to the internal buffer, applies all configured
        replacements, then releases only the "safe" prefix — everything
        except the trailing ``max_match_length`` characters which may
        still form part of a match.

        Args:
            delta: Newly arrived chunk of text.

        Returns:
            The safe prefix that can be forwarded to the frontend.
        """
        self._buffer += delta

        if self._max_match_length == 0:
            released = self._buffer
            self._buffer = ""
            return released

        self._buffer = self._apply_replacements(self._buffer)
        safe_end = max(0, len(self._buffer) - self._max_match_length)
        released = self._buffer[:safe_end]
        self._buffer = self._buffer[safe_end:]

        return released

    def flush(self) -> str:
        """Flush remaining buffer content at end of stream.

        Applies final replacements and releases all remaining buffered text.

        Returns:
            The remaining text from the buffer.
        """
        self._buffer = self._apply_replacements(self._buffer)
        released = self._buffer
        self._buffer = ""
        return released

    def _apply_replacements(self, text: str) -> str:
        for pattern, replacement in self._replacements:
            text = pattern.sub(replacement, text)
        return text
