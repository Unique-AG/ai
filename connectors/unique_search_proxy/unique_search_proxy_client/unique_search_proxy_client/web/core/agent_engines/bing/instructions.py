from __future__ import annotations

# Describes the output format we want from the agent. Models do not always
# follow it, so downstream parsing should tolerate deviations and keep what it
# can rather than reject the whole answer.
_CITATION_INSTRUCTIONS = """## Source-isolated evidence list
Use Bing Grounding to select distinct useful sources.
The complete response must consist only of lines in this form:
- <facts supported only by one source> <that source's citation>

Hard requirements:
1. Exactly one line per distinct source and exactly one distinct source per line.
2. Every line begins with `- ` and contains exactly one citation marker as its final content.
3. Never synthesize, compare, or combine facts across sources within a line.
4. Consolidate all useful facts from a source into that source's one line; never cite it again.
5. No headings, preface, conclusion, continuation lines, nested bullets, JSON, or uncited claims.
6. Never invent, reconstruct, type, or guess citation markers or source URLs.

Before responding, silently verify that the number of lines equals the number of distinct cited sources."""


def build_bing_citation_instructions(generation_instructions: str) -> str:
    """Add citation-safe output rules without suppressing Foundry annotations."""
    return f"{generation_instructions.rstrip()}\n\n{_CITATION_INSTRUCTIONS}"


__all__ = ["build_bing_citation_instructions"]
