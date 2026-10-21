"""Bing grounding tool configuration shared by the proxy and legacy runners.

Azure bakes these knobs into an *agent version* at creation time — they are not
sent per request — so every runner derives its agent name from them. Keeping the
value object and its hash payload here means the proxy client and the web-search
tool cannot drift on what a given agent name stands for.
"""

from __future__ import annotations

import hashlib
from dataclasses import astuple, dataclass

#: Name prefix of every auto-provisioned Bing grounding agent.
BING_AUTO_AGENT_NAME_PREFIX = "unique-grounding-with-bing"

_CONFIG_HASH_LENGTH = 12
_HASH_FIELD_SEPARATOR = "\0"

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


@dataclass(frozen=True, slots=True)
class BingGroundingConfiguration:
    """Knobs forwarded to ``BingGroundingSearchConfiguration`` on the agent tool."""

    fetch_size: int
    market: str | None = None
    freshness: str | None = None

    def hash_payload(self) -> str:
        """Stable string identifying this tool configuration."""
        return _HASH_FIELD_SEPARATOR.join(str(value) for value in astuple(self))


def bing_agent_config_hash(
    *,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> str:
    """Return a short hex digest of everything baked into the agent version."""
    payload = _HASH_FIELD_SEPARATOR.join(
        (model, instructions, grounding.hash_payload()),
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:_CONFIG_HASH_LENGTH]


def bing_agent_name(
    *,
    model: str,
    instructions: str,
    grounding: BingGroundingConfiguration,
) -> str:
    """Build a Foundry-safe agent name unique to this configuration."""
    digest = bing_agent_config_hash(
        model=model,
        instructions=instructions,
        grounding=grounding,
    )
    return f"{BING_AUTO_AGENT_NAME_PREFIX}-{digest}"


def build_bing_citation_instructions(generation_instructions: str) -> str:
    """Add citation-safe output rules without suppressing Foundry annotations."""
    return f"{generation_instructions.rstrip()}\n\n{_CITATION_INSTRUCTIONS}"


def is_auto_provisioned_bing_agent_name(name: str) -> bool:
    """True for names this module would have generated."""
    return name.startswith(f"{BING_AUTO_AGENT_NAME_PREFIX}-")


__all__ = [
    "BING_AUTO_AGENT_NAME_PREFIX",
    "BingGroundingConfiguration",
    "bing_agent_config_hash",
    "bing_agent_name",
    "build_bing_citation_instructions",
    "is_auto_provisioned_bing_agent_name",
]
