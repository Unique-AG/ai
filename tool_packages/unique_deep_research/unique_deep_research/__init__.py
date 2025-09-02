"""
Deep Research Tool Package

This package provides advanced research capabilities using various AI engines.
Currently supports OpenAI's deep research engine with plans for additional engines.
"""

from .config import DeepResearchEngine, DeepResearchToolConfig
from .service import DeepResearchTool

__all__ = [
    "DeepResearchTool",
    "DeepResearchToolConfig",
    "DeepResearchEngine",
]
