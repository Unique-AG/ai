from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Protocol

Replacement = str | Callable[[re.Match[str]], str]

NormalizationReplacement = Replacement
"""A regex replacement: either a string (may contain backreferences) or a
callable receiving a ``re.Match`` and returning a string."""

NormalizationPattern = tuple[str | re.Pattern[str], NormalizationReplacement]


def _expand_source_list(match: re.Match[str]) -> str:
    """Expand ``[source: 1, 2, 3]`` or ``[[1], [2], [3]]`` into ``[1][2][3]``."""
    numbers = re.findall(r"\d+", match.group(0))
    return "".join(f"[{n}]" for n in numbers)


NORMALIZATION_PATTERNS: list[NormalizationPattern] = [
    # ── Strip non-source references (all case-insensitive) ─────────────
    (r"(?i)\[(\\)?(<)?user(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?assistant(>)?\]", ""),
    (r"(?i)source[\s]?\[(\\)?(<)?conversation(>)?\]", "the previous conversation"),
    (r"(?i)\[(\\)?(<)?previous[_,\s]conversation(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?past[_,\s]conversation(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?previous[_,\s]?answer(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?previous[_,\s]question(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?conversation(>)?\]", ""),
    (r"(?i)\[(\\)?(<)?none(>)?\]", ""),
    # ── Normalise source references to [N] ─────────────────────────────
    (r"\[(\\)?<source[\s]?(\d+)>\]", r"[\2]"),
    (r"source[\s_]?(\d+)", r"[\1]"),
    (r'source_number="(\d+)"', r"[\1]"),
    (r"\[\*\*(\d+)\*\*\]", r"[\1]"),
    (r"(?i)source[\s]?(\d+)", r"[\1]"),
    (r"(?i)source[\s]?n°(\d+)", r"[\1]"),
    (r"\[(\\)?\[?<\[(\d+)\]?\]>\]", r"[\2]"),
    # ── Multi-source references (callable replacements) ────────────────
    (r"\[source:\s*([\d,\s]+)\]", _expand_source_list),
    (
        r"(?:\[\[(\d+)\](?:,\s*(?:\[)?\d+(?:\])?)*\]|\[([\d,\s]+)\])",
        _expand_source_list,
    ),
]
"""Normalisation rules that convert model-emitted citation formats
to the canonical ``[N]`` bracket notation."""

NORMALIZATION_MAX_MATCH_LENGTH = 80
"""Upper bound on characters any single pattern can match.  Sized for
multi-source patterns like ``[source: 1, 2, ..., 20]``."""


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
