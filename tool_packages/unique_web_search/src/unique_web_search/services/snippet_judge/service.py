"""Snippet judge service: score and explain (LLM), then rank and select (deterministic)."""

import logging

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    extract_registered_domain,
)
from unique_web_search.services.snippet_judge.prompts import (
    SNIPPET_JUDGE_SYSTEM_PROMPT,
    SNIPPET_JUDGE_USER_PROMPT_TEMPLATE,
    build_user_prompt,
)
from unique_web_search.services.snippet_judge.schema import (
    SnippetJudgeResponse,
    SnippetJudgment,
)

_LOGGER = logging.getLogger(__name__)


class SnippetJudgeConfig(BaseModel):
    """Configuration for the snippet judge."""

    model_config = get_configuration_dict()

    max_urls_to_select: int = Field(
        default=5,
        description="Maximum number of URLs to select after ranking (top-k by score).",
    )
    max_results_per_domain: int = Field(
        default=2,
        ge=1,
        description="Hard cap for how many selected results may come from the same registrable domain.",
    )
    system_prompt: str = Field(
        default=SNIPPET_JUDGE_SYSTEM_PROMPT,
        description="System message for the snippet judge LLM.",
    )
    user_prompt_template: str = Field(
        default=SNIPPET_JUDGE_USER_PROMPT_TEMPLATE,
        description="User prompt template. Must support placeholders: {objective}, {numbered_results}.",
    )


def _format_numbered_results(results: list[WebSearchResult]) -> str:
    """Format results as a numbered list for the prompt."""
    lines = []
    for i, r in enumerate(results):
        lines.append(f"{i}. {r.title} | {r.snippet} | {r.url}")
    return "\n".join(lines)


async def score_and_explain(
    objective: str,
    results: list[WebSearchResult],
    language_model_service: LanguageModelService,
    language_model: LMI,
    config: SnippetJudgeConfig | None = None,
) -> list[SnippetJudgment]:
    """Stage 1: Call LLM to get explanation and relevance_score for each result.

    Returns a list of SnippetJudgment in the same order as results (or keyed by index).
    """
    if not results:
        return []

    cfg = config or SnippetJudgeConfig()
    numbered_results = _format_numbered_results(results)
    user_prompt = build_user_prompt(
        objective, numbered_results, template=cfg.user_prompt_template
    )

    messages = (
        MessagesBuilder()
        .system_message_append(cfg.system_prompt)
        .user_message_append(user_prompt)
        .build()
    )

    response = await language_model_service.complete_async(
        messages,
        model_name=language_model.name,
        structured_output_model=SnippetJudgeResponse,
        structured_output_enforce_schema=True,
    )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Failed to parse snippet judge response from LLM")

    response_model = SnippetJudgeResponse.model_validate(parsed)
    judgments = response_model.judgments
    n = len(results)

    # Normalize indices to [0, n-1] and keep best score per index (deduplicate)
    by_index: dict[int, SnippetJudgment] = {}
    for j in judgments:
        idx = max(0, min(j.index, n - 1))
        new_j = SnippetJudgment(
            index=idx, explanation=j.explanation, relevance_score=j.relevance_score
        )
        if idx not in by_index or new_j.relevance_score > by_index[idx].relevance_score:
            by_index[idx] = new_j

    # One judgment per result index; fill missing with 0.0
    return [
        by_index.get(i, SnippetJudgment(index=i, explanation="", relevance_score=0.0))
        for i in range(n)
    ]


def rank_and_select(
    judgments: list[SnippetJudgment],
    results: list[WebSearchResult],
    max_urls_to_select: int,
    max_results_per_domain: int,
) -> list[int]:
    """Stage 2: Sort by relevance_score descending, return top-k indices.

    Tie-breaking: preserve original order (first occurrence wins).
    Applies a deterministic hard cap on how many selected results can come from
    the same registrable domain.
    """
    if not judgments or not results:
        return []

    # Sort by score descending, then by index ascending for ties
    sorted_judgments = sorted(
        judgments,
        key=lambda j: (-j.relevance_score, j.index),
    )
    selected_indices = []
    seen: set[int] = set()
    domain_counts: dict[str, int] = {}
    for j in sorted_judgments:
        if len(selected_indices) >= max_urls_to_select:
            break
        if j.index in seen:
            continue
        if j.index < 0 or j.index >= len(results):
            continue
        domain = extract_registered_domain(results[j.index].url)
        if domain_counts.get(domain, 0) >= max_results_per_domain:
            continue
        seen.add(j.index)
        selected_indices.append(j.index)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    return selected_indices


async def select_relevant(
    objective: str,
    results: list[WebSearchResult],
    language_model_service: LanguageModelService,
    language_model: LMI,
    config: SnippetJudgeConfig | None = None,
) -> list[WebSearchResult]:
    """Run stage 1 (score and explain) then stage 2 (rank); return filtered, ranked results.

    On LLM failure or empty judgments, falls back to returning all results (or first
    max_urls_to_select by original order).
    """
    cfg = config or SnippetJudgeConfig()

    if not results:
        return []

    try:
        judgments = await score_and_explain(
            objective=objective,
            results=results,
            language_model_service=language_model_service,
            language_model=language_model,
            config=cfg,
        )
    except Exception as e:
        _LOGGER.warning("Snippet judge LLM failed, falling back to all results: %s", e)
        return results[: cfg.max_urls_to_select]

    if not judgments:
        _LOGGER.warning(
            "Snippet judge returned no judgments, falling back to all results"
        )
        return results[: cfg.max_urls_to_select]

    ordered_indices = rank_and_select(
        judgments=judgments,
        results=results,
        max_urls_to_select=cfg.max_urls_to_select,
        max_results_per_domain=cfg.max_results_per_domain,
    )
    _LOGGER.info(f"Snippet judge ordered indices: {ordered_indices}")

    if not ordered_indices:
        return results[: cfg.max_urls_to_select]

    # Filter and reorder results by selected indices (valid only)
    n = len(results)
    valid_indices = [i for i in ordered_indices if 0 <= i < n]
    # Deduplicate preserving order
    seen: set[int] = set()
    unique_indices = []
    for i in valid_indices:
        if i not in seen:
            seen.add(i)
            unique_indices.append(i)

    return [results[i] for i in unique_indices]
