"""Run-scoped collection of language-model invocation usage."""

from typing import Any

from unique_toolkit.language_model.invocation_stats import InvocationStatsCollector

collector = InvocationStatsCollector("web_search")


def record_vertex_response(
    *,
    model_name: str,
    response: Any,
    source: str,
) -> None:
    """Record Google GenAI usage metadata using toolkit token names."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return

    collector.record_token_usage(
        model_name=model_name,
        usage={
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "completion_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
            "reasoning_tokens": getattr(usage, "thoughts_token_count", None),
            "cached_tokens": getattr(usage, "cached_content_token_count", None),
        },
        source=source,
    )
