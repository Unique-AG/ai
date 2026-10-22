from unique_web_search.services.search_engine.utils.grounding import (
    GENERATION_INSTRUCTIONS,
    RESPONSE_RULE,
    GroundingSearchResults,
    ResultItem,
)

GroundingWithBingResults = GroundingSearchResults

# Must match the search proxy's Bing instructions
# (``unique_search_proxy_client.web.core.agent_engines.bing.instructions``):
# both paths feed the same citation parser. Models do not always follow the
# format, so the parser tolerates deviations.
_CITATION_INSTRUCTIONS = """## Source-isolated evidence list
Use Bing Grounding to select distinct useful sources.
The complete response must consist only of lines in this form:
- <a paragraph of facts supported only by one source> <that source's citation>

Each line is a paragraph, not a sentence. Write several sentences per line that report every relevant fact, figure, date, name and quote from that source, with as much detail as the source offers, often 100 to 200 words. Lines can be long; do not shorten them.

Hard requirements:
1. Exactly one line per distinct source and exactly one distinct source per line.
2. Every line begins with `- ` and contains exactly one citation marker as its final content.
3. Never synthesize, compare, or combine facts across sources within a line.
4. Put all useful facts from a source into that source's one line; never cite it again.
5. No headings, preface, conclusion, line breaks inside a paragraph, nested bullets, JSON, or uncited claims.
6. Never invent, reconstruct, type, or guess citation markers or source URLs.

Before responding, silently verify that the number of lines equals the number of distinct cited sources."""


def build_bing_citation_instructions(generation_instructions: str) -> str:
    """Add citation-safe output rules without suppressing Foundry annotations."""
    return f"{generation_instructions.rstrip()}\n\n{_CITATION_INSTRUCTIONS}"


__all__ = [
    "GENERATION_INSTRUCTIONS",
    "RESPONSE_RULE",
    "GroundingSearchResults",
    "GroundingWithBingResults",
    "ResultItem",
    "build_bing_citation_instructions",
]
