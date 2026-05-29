"""Snippet judge service: score and explain (LLM), then rank and select (deterministic)."""

import logging

import jinja2
from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.helpers import extract_registered_domain
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
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

# Upper bound of the judge prompt's "clearly irrelevant" band (0.00–0.14).
# When the *highest* score across all returned judgments is strictly below
# this threshold, the entire SERP is judged garbage (forum threads, social
# posts, broken results, off-topic pages) — distinct from "weak but possibly
# useful" (0.15–0.39). Treat the former as a structural off-topic signal so
# the executor surfaces a reformulate cue rather than dumping the unfiltered
# SERP into the agent's context. The threshold mirrors the band boundary
# defined in the judge's system prompt; changing one without the other will
# desynchronise calibration.
CLEARLY_IRRELEVANT_THRESHOLD = 0.15


class SerpOffTopicError(ValueError):
    """Raised when the LLM judge produced no relevant judgments for any result.

    Fires in two structurally-equivalent cases:

    1. **Empty judgments** — the LLM returned ``judgments=[]``. The judge had
       nothing to say about any URL on the SERP.
    2. **Clearly-irrelevant max** — the LLM returned judgments, but the
       *highest* relevance score was strictly below
       ``CLEARLY_IRRELEVANT_THRESHOLD`` (0.15). The judge looked at every URL
       and rated all of them in the "forum thread, social media post,
       off-topic, broken/spam" band defined by its own prompt.

    Both are semantically "this SERP is off-topic for the gap" — distinct
    from generic LLM failures (parse errors, refusals, schema mismatches)
    which use plain ``ValueError`` and trigger fail-open semantics.

    Callers (the V3 executor) catch this specifically to surface a structured
    "no relevant results — reformulate" signal to the agent instead of dumping
    the unfiltered SERP into context. Without this distinction, every truly
    off-topic SERP looked indistinguishable from an LLM hiccup, and both ended
    up serving the agent the same list of unrelated URLs.

    Subclasses ``ValueError`` so the existing general ``except Exception:``
    fallback path inside ``select_relevant`` still catches it *unless* a
    caller explicitly handles it first — which is the only design that lets
    us migrate one call site (the V3 executor) without breaking any others.
    """


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
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum relevance score required to keep a result (0.0–1.0). "
            "Results scored strictly below this threshold are dropped before top-k selection. "
            "Default 0.0 keeps top-k regardless of score; raise (e.g. 0.3) to drop low-quality hits."
        ),
    )
    system_prompt: str = Field(
        default=SNIPPET_JUDGE_SYSTEM_PROMPT,
        description=(
            "System message for the snippet judge LLM (Jinja2). "
            "Available variables: {{ objective }}, {{ numbered_results }}, and the "
            "optional {{ query }} (the actual search query issued) and {{ gap }} "
            "(the specific sub-question this search is meant to fill)."
        ),
    )
    user_prompt_template: str = Field(
        default=SNIPPET_JUDGE_USER_PROMPT_TEMPLATE,
        description=(
            "User prompt template (Jinja2). "
            "Available variables: {{ objective }}, {{ numbered_results }}, and the "
            "optional {{ query }} and {{ gap }} (rendered only when the caller "
            "provides them)."
        ),
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
    query: str | None = None,
    gap: str | None = None,
) -> list[SnippetJudgment]:
    """Stage 1: Call LLM to get explanation and relevance_score for each result.

    Optionally pass ``query`` (the actual search query issued) and ``gap`` (the
    specific sub-question this search is meant to fill) so the judge scores
    against the full intent rather than just the broad objective.

    Returns a list of SnippetJudgment in the same order as results (or keyed by index).
    """
    if not results:
        return []

    cfg = config or SnippetJudgeConfig()
    numbered_results = _format_numbered_results(results)
    render_ctx = {
        "objective": objective,
        "numbered_results": numbered_results,
        "query": query,
        "gap": gap,
    }
    system_message = jinja2.Template(cfg.system_prompt).render(**render_ctx)
    user_prompt = build_user_prompt(
        objective,
        numbered_results,
        template=cfg.user_prompt_template,
        query=query,
        gap=gap,
    )

    messages = (
        MessagesBuilder()
        .system_message_append(system_message)
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
        # The structured-output decoder couldn't produce a SnippetJudgeResponse
        # at all — refusal, schema mismatch, or empty completion. We have no
        # judgments to recover; log the result titles so operators can pattern-
        # match which content types break the judge (BNPP traces showed this
        # firing on SERPs heavy with social-media / PDF URLs that the judge
        # may have refused to score).
        _LOGGER.warning(
            "Snippet judge structured output parsing returned None for %d "
            "results; first titles: %s",
            len(results),
            [r.title[:80] for r in results[:3]],
        )
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

    # No usable judgments at all (empty list, or every index out of range and
    # squashed to a single bucket that still left the rest unfilled). Treating
    # those as "all at threshold floor" would let *every* result pass ranking
    # silently — the executor would then return a truncated top-k *without
    # ever triggering its unfiltered-SERP fallback*, hiding URLs from the
    # agent that an explicit sub-threshold judge run would have surfaced.
    # Raise instead so ``select_relevant``'s except block falls open with the
    # full result list (no scores attached), matching LLM-failure semantics.
    if not by_index:
        # Capture the SERP shape on the way out so we can diagnose *why* the
        # judge skipped everything — production traces show this firing on
        # SERPs heavy in social-media / PDF URLs, and without this log we
        # only see ``before=N, after=N, kept_scores={}`` at the executor level
        # with no signal on which URLs the LLM bailed on.
        _LOGGER.warning(
            "Snippet judge produced 0 usable judgments for %d results "
            "(raw judgments=%d); URLs=%s",
            n,
            len(judgments),
            [r.url for r in results],
        )
        # Out-of-range indices are *clamped* into [0, n-1] at line 143, so
        # ``by_index`` is empty iff the LLM literally returned ``judgments=[]``.
        # That's a structural "this SERP is off-topic" signal — distinct from
        # parsing/refusal failures (which use plain ``ValueError`` below) — so
        # raise the specialised exception. Callers that opt in (the V3
        # executor) can surface a "reformulate" cue to the agent instead of
        # dumping unfiltered URLs into context. Callers that don't opt in
        # still hit the generic fail-open path because ``SerpOffTopicError``
        # subclasses ``ValueError``.
        raise SerpOffTopicError(
            f"Snippet judge returned no usable judgments for {n} results "
            f"(received {len(judgments)} raw entries). SERP appears entirely "
            f"off-topic for the gap."
        )

    # Second off-topic case: the judge scored every URL, but every score lands
    # in the "clearly irrelevant" band (0.00–0.14 per the prompt's calibration).
    # That's the signal the BNPP rental-rate / sale-price traces kept hitting —
    # garbled Thai-script queries produced pubmed chemistry papers and LinkedIn
    # profiles, the judge correctly scored everything in the 0.0–0.1 range,
    # ``min_score=0.3`` filtered them all out, the executor fell back to the
    # unfiltered list, and the agent then had 5 unrelated URLs in its context.
    # We can detect that path here and route it through the same reformulate
    # cue as the empty-judgments case — same exception, same downstream handler,
    # different log line. Anything ≥0.15 stays on the existing fall-back path
    # because "weak but possibly useful" remains a legitimate signal the agent
    # can act on (e.g. by fetching the least-weak result rather than retrying).
    max_score = max(j.relevance_score for j in by_index.values())
    if max_score < CLEARLY_IRRELEVANT_THRESHOLD:
        _LOGGER.warning(
            "Snippet judge scored every result in the clearly-irrelevant band "
            "(max=%.2f < %.2f) for %d results; URLs=%s",
            max_score,
            CLEARLY_IRRELEVANT_THRESHOLD,
            n,
            [r.url for r in results],
        )
        raise SerpOffTopicError(
            f"Snippet judge max score {max_score:.2f} is below the "
            f"clearly-irrelevant threshold ({CLEARLY_IRRELEVANT_THRESHOLD}). "
            f"SERP appears entirely off-topic for the gap."
        )

    # One judgment per result index. The structured output schema *asks* for one
    # per result, but LLMs occasionally skip some, especially on long SERPs.
    # Fill missing slots with a score tied to ``cfg.min_score``: this lands them
    # *at the threshold floor* so they (a) survive the cut — we don't silently
    # drop URLs the LLM forgot to score — but (b) rank below every result the
    # LLM explicitly judged worth keeping, and (c) crucially do NOT outrank
    # results the LLM marked low (those are below the threshold and get dropped
    # entirely). Avoids the asymmetry where an LLM omission would beat an
    # explicit low score.
    missing_score = cfg.min_score
    missing = [i for i in range(n) if i not in by_index]
    if missing:
        _LOGGER.warning(
            "Snippet judge omitted %d/%d judgments (indices=%s); using threshold-floor score %.2f for missing entries.",
            len(missing),
            n,
            missing,
            missing_score,
        )
    return [
        by_index.get(
            i,
            SnippetJudgment(
                index=i,
                explanation="(no judgment returned by model)",
                relevance_score=missing_score,
            ),
        )
        for i in range(n)
    ]


def rank_and_select(
    judgments: list[SnippetJudgment],
    results: list[WebSearchResult],
    max_urls_to_select: int,
    max_results_per_domain: int,
    min_score: float = 0.0,
) -> list[int]:
    """Stage 2: Sort by relevance_score descending, return top-k indices.

    Tie-breaking: preserve original order (first occurrence wins).
    Applies a deterministic hard cap on how many selected results can come from
    the same registrable domain. Drops any judgment with score strictly below
    ``min_score`` so hopeless results are excluded entirely rather than padding
    the top-k.
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
        if j.relevance_score < min_score:
            continue
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
    query: str | None = None,
    gap: str | None = None,
) -> list[WebSearchResult]:
    """Run stage 1 (score and explain) then stage 2 (rank); return filtered, ranked results.

    Optionally pass ``query`` (the actual search query issued) and ``gap`` (the specific
    sub-question this search is meant to fill) to ground the judge on the full intent.

    On LLM failure or empty judgments, returns **all** results unmodified — truncating
    a failed filter would silently drop URLs that the caller has no way to recover.
    When ranking succeeds but the ``min_score`` threshold excludes every result, returns
    an empty list (the filter intentionally found nothing relevant).
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
            query=query,
            gap=gap,
        )
    except SerpOffTopicError:
        # Don't fall open here: the SERP is structurally off-topic, not the
        # judge failing. Let it propagate so the V3 executor can surface a
        # "reformulate" cue to the agent instead of unfiltered noise. Other
        # callers that don't catch this still hit the same default behaviour
        # they had before via the ``ValueError`` superclass; only callers
        # that *explicitly* handle ``SerpOffTopicError`` opt into the new
        # signal-based flow.
        raise
    except Exception as e:
        _LOGGER.warning("Snippet judge LLM failed, falling back to all results: %s", e)
        return list(results)

    if not judgments:
        _LOGGER.warning(
            "Snippet judge returned no judgments, falling back to all results"
        )
        return list(results)

    ordered_indices = rank_and_select(
        judgments=judgments,
        results=results,
        max_urls_to_select=cfg.max_urls_to_select,
        max_results_per_domain=cfg.max_results_per_domain,
        min_score=cfg.min_score,
    )
    _LOGGER.info(f"Snippet judge ordered indices: {ordered_indices}")

    # Empty selection here means the judge ran successfully but every result was
    # below ``min_score`` (or otherwise excluded). That is a *signal*, not a
    # failure — return an empty list rather than padding with garbage.
    if not ordered_indices:
        return []

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

    # Attach the judge's score to each kept result so downstream consumers
    # (executor → ContentChunk JSON payload → agent) can see how strongly each
    # surviving result matched the gap. The agent uses scores ≥ 0.85 as a
    # "primary-source-class hit, prefer fetch over another search" signal.
    score_by_index = {j.index: j.relevance_score for j in judgments}
    return [
        results[i].model_copy(update={"relevance_score": score_by_index.get(i)})
        for i in unique_indices
    ]
