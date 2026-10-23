from __future__ import annotations

from importlib.resources import files

from jinja2 import StrictUndefined, Template

# Describes the output format we want from the agent. Models do not always
# follow it, so downstream parsing should tolerate deviations and keep what it
# can rather than reject the whole answer.
_CITATION_INSTRUCTIONS = Template(
    files(__package__)
    .joinpath("citation_instructions.j2")
    .read_text(encoding="utf-8")
    .strip(),
    undefined=StrictUndefined,
)


def build_bing_citation_instructions(generation_instructions: str) -> str:
    """Add citation-safe output rules without suppressing Foundry annotations."""
    return _CITATION_INSTRUCTIONS.render(
        generation_instructions=generation_instructions.rstrip()
    )


__all__ = ["build_bing_citation_instructions"]
