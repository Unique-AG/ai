"""
SWOT Analysis Prompt Templates

This module loads and exposes all Jinja2 template files used for SWOT analysis generation.
Templates are organized into two categories:
- Extraction: For extracting insights from source documents
- Summarization: For aggregating and deduplicating insights from multiple batches
"""

from unique_swot.services.generation.prompts.extraction.config import (
    ExtractionPromptConfig,
)
from unique_swot.services.generation.prompts.summarization.config import (
    SummarizationPromptConfig,
)

__all__ = [
    "ExtractionPromptConfig",
    "SummarizationPromptConfig",
]
