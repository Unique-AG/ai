"""Shared text-sanitization helpers — single source of truth for NUL-byte hygiene.

The web-search pipeline ingests strings from three external sources: the search
engine API (titles / snippets / URLs / cached content), the crawler (full page
bodies extracted from PDFs / HTML), and the agent itself (objective / query /
gap / supplied URLs). All three occasionally surface ASCII control characters
— most often the NUL byte (``\\u0000``), which Postgres TEXT columns reject
with error ``22P05`` ("``\\u0000`` cannot be converted to text") and which
crashes every downstream ``modify_message`` / ``stream-responses`` call once
the dirty text lands in a tool result.

Two sanitization shapes are needed:

- ``sanitize_single_line`` — for short fields (URLs, titles, snippets, queries,
  objectives, gaps) where whitespace structure does not matter and adjacent
  words must not silently merge when a stripped control char sat between them.
  Replaces control characters with SPACE and then collapses whitespace runs.

- ``strip_controls`` — for long-form text (page bodies / crawler output) where
  paragraph and list structure must survive. Strips control characters (TAB /
  LF / CR are *not* in the class, so they pass through unchanged), leaving the
  rest of the document intact.

Both functions are no-ops on clean text, so wrapping is cheap and safe to call
defensively.
"""

from __future__ import annotations

import re

# C0 controls (except TAB/LF/CR), C1 controls, DEL, BOM, noncharacters, and the
# replacement char (``�``). TAB ``\x09``, LF ``\x0a``, CR ``\x0d`` are
# deliberately excluded so ``strip_controls`` preserves line structure in
# long-form text; ``sanitize_single_line`` then collapses them along with any
# spacing the control-→-space substitution introduced.
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f￾￿�]")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_controls(text: str) -> str:
    """Strip C0/C1/DEL/BOM/noncharacters; preserve TAB/LF/CR.

    For long-form text (page bodies) where paragraph / list structure must
    survive. NUL-byte safe: removes ``\\u0000`` which Postgres TEXT columns
    reject (error ``22P05``).
    """
    return CONTROL_CHAR_RE.sub("", text)


def sanitize_single_line(text: str) -> str:
    """Replace controls with space, collapse whitespace runs, trim.

    For short, single-line fields (URLs, titles, snippets, queries, objectives,
    gaps) where whitespace structure does not matter. Replacing with SPACE
    instead of stripping preserves word boundaries — observed regression
    otherwise: ``a\\x0eb`` would strip to ``ab`` and the engine matched a
    nonsense token, returning an empty SERP. With SPACE substitution the same
    input becomes ``a b`` and the engine tokenizes both words.

    Safe to call on any short externally-supplied string. No-op for clean text.
    """
    spaced = CONTROL_CHAR_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", spaced).strip()
