from pathlib import Path

from jinja2 import StrictUndefined, Template

from unique_web_search.services.search_engine.utils.grounding import (
    GENERATION_INSTRUCTIONS,
    RESPONSE_RULE,
    GroundingSearchResults,
    ResultItem,
)
from unique_web_search.utils import load_template

GroundingWithBingResults = GroundingSearchResults

# Must match the search proxy's Bing instructions
# (``unique_search_proxy_client.web.core.agent_engines.bing.citation_instructions.j2``):
# both paths feed the same citation parser. Models do not always follow the
# format, so the parser tolerates deviations.
_CITATION_INSTRUCTIONS = Template(
    load_template(Path(__file__).parent, "citation_instructions.j2"),
    undefined=StrictUndefined,
)


def build_bing_citation_instructions(generation_instructions: str) -> str:
    """Add citation-safe output rules without suppressing Foundry annotations."""
    return _CITATION_INSTRUCTIONS.render(
        generation_instructions=generation_instructions.rstrip()
    )


__all__ = [
    "GENERATION_INSTRUCTIONS",
    "RESPONSE_RULE",
    "GroundingSearchResults",
    "GroundingWithBingResults",
    "ResultItem",
    "build_bing_citation_instructions",
]
