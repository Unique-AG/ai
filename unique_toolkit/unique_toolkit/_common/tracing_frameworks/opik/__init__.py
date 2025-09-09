"""
Opik tracing framework integration for the Unique Toolkit.

Simple, non-breaking tracing for function decorators and LangGraph.
"""

from .track import (
    LangChainTracer,
    get_langchain_tracer,
    get_tracking_decorator,
    is_opik_enabled,
    track,
    update_current_trace,
)

__all__ = [
    "track",
    "get_tracking_decorator",
    "is_opik_enabled",
    "update_current_trace",
    "get_langchain_tracer",
    "LangChainTracer",
]
