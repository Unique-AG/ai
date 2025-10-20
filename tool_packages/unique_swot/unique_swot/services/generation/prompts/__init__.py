"""
SWOT Analysis Prompt Templates

This module loads and exposes all Jinja2 template files used for SWOT analysis generation.
Templates are organized into two categories:
- Extraction: For extracting insights from source documents
- Summarization: For aggregating and deduplicating insights from multiple batches
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Get the directory containing this file
_PROMPTS_DIR = Path(__file__).parent

# Create Jinja2 environment with the prompts directory as the base
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Extraction templates - for extracting insights from raw source documents
STRENGTHS_EXTRACTION_TEMPLATE: str = _jinja_env.get_template(
    "extraction/strengths.j2"
).render()
WEAKNESSES_EXTRACTION_TEMPLATE: str = _jinja_env.get_template(
    "extraction/weaknesses.j2"
).render()
OPPORTUNITIES_EXTRACTION_TEMPLATE: str = _jinja_env.get_template(
    "extraction/opportunities.j2"
).render()
THREATS_EXTRACTION_TEMPLATE: str = _jinja_env.get_template(
    "extraction/threats.j2"
).render()

# Summarization templates - for aggregating insights from multiple batches
STRENGTHS_SUMMARIZATION_TEMPLATE: str = _jinja_env.get_template(
    "summarization/strengths.j2"
).render()
WEAKNESSES_SUMMARIZATION_TEMPLATE: str = _jinja_env.get_template(
    "summarization/weaknesses.j2"
).render()
OPPORTUNITIES_SUMMARIZATION_TEMPLATE: str = _jinja_env.get_template(
    "summarization/opportunities.j2"
).render()
THREATS_SUMMARIZATION_TEMPLATE: str = _jinja_env.get_template(
    "summarization/threats.j2"
).render()

# Export all templates
__all__ = [
    # Extraction templates
    "STRENGTHS_EXTRACTION_TEMPLATE",
    "WEAKNESSES_EXTRACTION_TEMPLATE",
    "OPPORTUNITIES_EXTRACTION_TEMPLATE",
    "THREATS_EXTRACTION_TEMPLATE",
    # Summarization templates
    "STRENGTHS_SUMMARIZATION_TEMPLATE",
    "WEAKNESSES_SUMMARIZATION_TEMPLATE",
    "OPPORTUNITIES_SUMMARIZATION_TEMPLATE",
    "THREATS_SUMMARIZATION_TEMPLATE",
]
