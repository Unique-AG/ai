"""Web Search V3 executor: one command per invocation (``query`` search or ``urls`` fetch)."""

from __future__ import annotations

import json
import logging
import re
from time import time

from unidecode import unidecode
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.monitoring import metric_scope

from unique_web_search.metrics import (
    crawl_duration,
    crawl_errors,
    llm_duration,
    search_duration,
    search_errors,
    search_total,
)
from unique_web_search.schema import StepDebugInfo
from unique_web_search.services.content_processing.cleaning.character_sanitize import (
    _CONTROL_CHAR_RE,
)
from unique_web_search.services.executors.base_executor import BaseWebSearchExecutor
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v3.config import SerpFilterConfig
from unique_web_search.services.executors.v3.schema import (
    FetchUrlsPayload,
    SearchPayload,
    WebSearchV3ToolParameters,
)
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.snippet_judge.service import (
    SerpOffTopicError,
    SnippetJudgeConfig,
    select_relevant,
)

_LOGGER = logging.getLogger(__name__)

# Same character class as ``CharacterSanitize`` (single source of truth for
# "what is a control character") but with a *different replacement strategy*:
# for queries we substitute SPACE instead of stripping, so word boundaries
# survive. Observed case (BNPP test set): the model emitted
# ``\x1a\x0e1\x0ea\x0e3\x004Treasury Department ...``; stripping merged the
# digits into the next word as ``1a34Treasury``, which the engine then matched
# as a nonsense token and the SERP came back empty. Replacing with space
# yields ``1 a 3 4 Treasury Department ...`` — still not pretty, but Google
# tokenizes the legitimate words separately and the search has a chance.
_WHITESPACE_RE = re.compile(r"\s+")


def _sanitize_text(text: str) -> str:
    """Replace control characters with spaces, then normalize whitespace.

    Real models / elicitation forms occasionally produce strings with ASCII
    control characters (``\\u0000`` NUL, ``\\u000E`` Shift-Out, ``\\u000B``
    Vertical Tab, …) embedded in otherwise-valid text. Three things go wrong
    if we don't clean them:

    1. NUL (``\\u0000``) cannot be stored in Postgres TEXT columns
       (error ``22P05``); any LLM string that lands in our ``debug_info``
       crashes the downstream ``modify_message`` / ``stream-responses`` calls
       with a generic 500.
    2. Stripped control chars merge adjacent words (``a\\x0eb`` → ``ab``);
       replacing with space preserves word boundaries.
    3. Stray control chars in search queries produce empty SERPs.

    Uses the same character class as ``CharacterSanitize`` (drop C0/C1
    controls, DEL, BOM/noncharacters; preserve TAB/LF/CR — those become
    whitespace after the collapse step — and all Cf format chars relevant to
    non-Latin scripts) but **replaces with space** rather than stripping.

    Safe to call on any short LLM-supplied string (query, objective, gap, URL).
    No-op for clean text.
    """
    spaced = _CONTROL_CHAR_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", spaced).strip()


class WebSearchV3Executor(BaseWebSearchExecutor[WebSearchV3ToolParameters]):
    """Run either a ``query`` search (SERP-only JSON chunks) or a ``urls`` fetch (crawl + pipeline)."""

    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchV3ToolParameters,
        serp_filter_config: SerpFilterConfig | None = None,
    ):
        super().__init__(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
        )
        self.serp_filter_config = serp_filter_config

    async def run(self) -> list[ContentChunk]:
        p = self.tool_parameters
        # Sanitize every LLM-supplied string at the entry point so downstream
        # code (debug_info recording, search engine, SERP-filter LLM, UI
        # notifications) all see clean text. Postgres TEXT columns reject
        # ``\\u0000`` (error 22P05) — without this, any control char in
        # ``objective`` / ``gap`` / ``urls`` crashes the modify_message and
        # stream-responses calls with a generic 500.
        objective = _sanitize_text(p.objective)
        if isinstance(p.payload, SearchPayload):
            await self._message_log_callback.log_progress("_Executing Search_")
            return await self._run_search(
                query=_sanitize_text(p.payload.query),
                objective=objective,
                gap=_sanitize_text(p.payload.gap),
            )
        if isinstance(p.payload, FetchUrlsPayload):
            await self._message_log_callback.log_progress("_Reading Web Pages_")
            return await self._run_fetch_urls(
                urls=[_sanitize_text(u) for u in p.payload.urls],
                objective=objective,
            )

        msg = "WebSearchV3ToolParameters requires exactly one of 'query' or 'urls'."

        raise ValueError(msg)

    async def _run_search(
        self,
        *,
        query: str,
        objective: str,
        gap: str,
    ) -> list[ContentChunk]:
        self.notify_name = "**Searching Web**"
        self.notify_message = objective
        await self.notify_callback()

        elicited = await self.query_elicitation([query])
        query = elicited[0]

        # ``run()`` already sanitized ``query`` before we got here, but
        # ``query_elicitation`` is an LLM call that can re-introduce control
        # chars (observed: elicitation form forwards the model's raw output).
        # Re-sanitize defensively. No-op for clean queries.
        sanitized_query = _sanitize_text(query)
        if sanitized_query != query:
            _LOGGER.warning(
                "Elicited query contained non-printable / control characters; "
                "re-sanitized before issuing to engine. before=%r after=%r",
                query,
                sanitized_query,
            )
            query = sanitized_query

        # Pathological input: the query was non-empty but consisted entirely of
        # control / format / whitespace characters that sanitization stripped.
        # Issuing an empty query to the engine wastes an API call and returns
        # an empty SERP. Skip the call, record the skip in the debug step, and
        # return no chunks — the agent will see "no results" and adapt
        # (typically by reformulating with different keywords on the next turn).
        if not query:
            _LOGGER.error(
                "Search query became empty after sanitization (input was entirely "
                "control/format/whitespace characters). Skipping engine call."
            )
            self.debug_info.steps.append(
                StepDebugInfo(
                    step_name="SEARCH.skipped",
                    execution_time=0,
                    config="empty_query_after_sanitization",
                    extra={"objective": objective, "gap": gap},
                )
            )
            await self._message_log_callback.log_web_search_results([])
            return []

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="SEARCH",
                execution_time=0,
                config={
                    "objective": objective,
                    "query": query,
                    "gap": gap,
                },
            )
        )

        engine = self.search_service.config.search_engine_name.value
        time_start = time()
        _LOGGER.info(
            "Company %s Searching with %s", self.company_id, self.search_service
        )

        await self._message_log_callback.log_queries([query])
        with metric_scope(search_duration, search_errors, engine=engine):
            search_total.labels(engine=engine).inc()
            results = await self.search_service.search(query)

        delta_time = time() - time_start
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="SEARCH.search",
                execution_time=delta_time,
                config=self.search_service.config.search_engine_name.name,
                extra={
                    "query": query,
                    "number_of_results": len(results),
                    "urls": [result.url for result in results],
                },
            )
        )
        _LOGGER.info("Searched with %s in %s seconds", self.search_service, delta_time)

        try:
            results = await self._filter_serp_results(
                objective=objective,
                query=query,
                gap=gap,
                results=results,
            )
        except SerpOffTopicError:
            # Every result scored as off-topic for the gap. Don't pollute the
            # agent's context with the unfiltered SERP (LinkedIn profiles,
            # random social posts, etc. that the judge already rejected);
            # surface a single structured "reformulate" chunk instead, which
            # short-circuits the explore-then-exploit loop with a clear next
            # action. Skips ``log_web_search_results`` since there are no
            # URLs the agent will (or should) act on for this search.
            await self._message_log_callback.log_web_search_results([])
            return [self._make_reformulate_chunk(query=query, gap=gap)]

        # Surface the *filtered* SERP to the operator's message log so the UI
        # mirrors what the agent actually received. The complete pre-filter
        # list (including dropped URLs) remains visible via the
        # ``SEARCH.search`` and ``SEARCH.serp_filter`` debug steps.
        await self._message_log_callback.log_web_search_results(results)

        chunks = self._serp_results_to_content_chunks(results)
        return chunks

    async def _filter_serp_results(
        self,
        *,
        objective: str,
        results: list[WebSearchResult],
        query: str | None = None,
        gap: str | None = None,
    ) -> list[WebSearchResult]:
        """Apply LLM-based relevance filtering to SERP results when enabled.

        The judge scores each result against ``objective``, ``query``, and ``gap``
        (when provided) so it accounts for the specific sub-question being asked,
        not just the broad task objective.

        Short-circuits the LLM call only when there is at most one result *and*
        ``min_score`` is ``0`` — with a single result and a non-zero threshold we
        still need to score it to know whether to keep it.

        Behaviour on the various failure modes:
        - Filter disabled / empty SERP / generic LLM exception: returns the
          original results unmodified (fail-open).
        - Judge ran but every result fell below ``min_score``: returns the
          original results unmodified (fail-safe) so the agent still has URLs
          available to fetch. ``fell_back_to_unfiltered=True`` in debug.
        - Judge returned literally ``judgments=[]`` (entire SERP off-topic):
          raises ``SerpOffTopicError`` for ``_run_search`` to catch. We do
          *not* fall open here — production traces showed that path dumping
          5 unrelated URLs (LinkedIn profiles, RICS pages, random Facebook
          posts) into the agent's context, which then either confused the
          agent or burned iterations trying to fetch garbage. The debug step
          records ``serp_quality="off_topic"`` so operators can see the
          signal without ever opening logs.
        """
        cfg = self.serp_filter_config
        if not cfg or not cfg.enabled or not results:
            return results

        # Nothing to rank or threshold: a single result either passes or fails
        # ``min_score``, but we can't know without scoring it. Save the LLM call
        # only when the threshold is disabled.
        if len(results) <= 1 and cfg.min_score <= 0.0:
            return results

        # Update progress UI for parity with other multi-stage flows (crawl /
        # analyze / resort) so the operator sees the extra LLM step.
        self.notify_name = "**Filtering Search Results**"
        self.notify_message = gap or objective
        await self.notify_callback()
        await self._message_log_callback.log_progress("_Filtering Search Results_")

        time_start = time()
        # ``select_relevant`` swallows generic LLM exceptions internally
        # (fail-open contract — returns all results on parse/refusal/etc.),
        # so wrapping it with ``metric_scope(llm_duration, llm_errors, ...)``
        # would record duration but never increment errors. Track duration
        # directly to match the ``purpose=`` label convention used elsewhere;
        # generic failures surface via the warning log inside
        # ``select_relevant``. The one exception that *does* propagate is
        # ``SerpOffTopicError`` — see the except block below.
        try:
            filtered = await select_relevant(
                objective=objective,
                results=results,
                language_model_service=self.language_model_service,
                language_model=cfg.language_model,
                config=SnippetJudgeConfig(
                    max_urls_to_select=cfg.max_results,
                    max_results_per_domain=cfg.max_results_per_domain,
                    min_score=cfg.min_score,
                ),
                query=query,
                gap=gap,
            )
        except SerpOffTopicError:
            delta_time = time() - time_start
            llm_duration.labels(purpose="serp_filter").observe(delta_time)
            # Record the off-topic signal in the debug step *before* re-raising
            # so the operator UI shows the same shape it always has for
            # serp_filter steps: ``before``, ``after`` (=0 here), the kept/
            # dropped URLs (everything dropped), and a structured
            # ``serp_quality="off_topic"`` flag that the rental-rate trace
            # would have shown instead of the misleading
            # ``fell_back_to_unfiltered=true`` it currently emits.
            self.debug_info.steps.append(
                StepDebugInfo(
                    step_name="SEARCH.serp_filter",
                    execution_time=delta_time,
                    config=cfg.language_model.name,
                    extra={
                        "before": len(results),
                        "after": 0,
                        "min_score": cfg.min_score,
                        "serp_quality": "off_topic",
                        "objective": objective,
                        "query": query,
                        "gap": gap,
                        "kept_urls": [],
                        "kept_scores": {},
                        "dropped_urls": [r.url for r in results],
                    },
                )
            )
            raise
        delta_time = time() - time_start
        llm_duration.labels(purpose="serp_filter").observe(delta_time)

        # Fail-safe: if the judge ran successfully but every result fell below
        # ``min_score``, returning [] would hide the SERP URLs from the agent —
        # and the V3 prompts explicitly tell it to "fetch the most relevant URL
        # already in your SERP results" when a search yields no usable result.
        # Falling back to the unfiltered list lets the agent make that call.
        # The empty signal is still surfaced via the debug step so operators
        # can see when this fallback fired.
        fell_back = False
        if not filtered:
            _LOGGER.info(
                "SERP filter found no results ≥ min_score=%.2f; falling back to "
                "unfiltered SERP so the agent can choose to fetch.",
                cfg.min_score,
            )
            filtered = list(results)
            fell_back = True

        _LOGGER.info(
            "SERP filter: %d → %d results in %.2fs%s",
            len(results),
            len(filtered),
            delta_time,
            " (fallback: nothing above threshold)" if fell_back else "",
        )
        kept_urls = {r.url for r in filtered}
        # Per-URL judge scores for the kept set. The score signal is what the
        # agent reads (≥0.85 → prefer fetch; <0.40 across SERP → reformulate) —
        # surfacing it here lets operators see *why* the agent decided to fetch
        # vs. search again. Empty when the filter fell back to unfiltered
        # (those results were never selected with scores attached).
        kept_scores = {
            r.url: round(r.relevance_score, 2)
            for r in filtered
            if r.relevance_score is not None
        }
        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="SEARCH.serp_filter",
                execution_time=delta_time,
                config=cfg.language_model.name,
                extra={
                    "before": len(results),
                    "after": len(filtered),
                    "min_score": cfg.min_score,
                    "fell_back_to_unfiltered": fell_back,
                    "objective": objective,
                    "query": query,
                    "gap": gap,
                    "kept_urls": [r.url for r in filtered],
                    "kept_scores": kept_scores,
                    "dropped_urls": [r.url for r in results if r.url not in kept_urls],
                },
            )
        )
        return filtered

    def _make_reformulate_chunk(
        self, *, query: str | None, gap: str | None
    ) -> ContentChunk:
        """Synthetic chunk surfaced when the SERP filter judged every result
        off-topic for the gap.

        Tells the agent in structured form that this particular query yielded
        nothing usable, so it should reformulate (different keywords, scope,
        language, timeframe) rather than fetch one of the rejected URLs or
        retry with similar keywords. The V3 system prompt already covers the
        ``<0.40 across SERP → reformulate`` band; this chunk is the
        tool-output-level cue for the stronger ``raw judgments=0`` case where
        the judge couldn't even score anything as worth a number.

        Returned as a single ``ContentChunk`` with an empty URL (signalling
        "no source") and ``serp_quality="off_topic"`` in the JSON payload so
        downstream consumers can distinguish it from a real result.
        """
        payload = {
            "serp_quality": "off_topic",
            "query_issued": query,
            "gap": gap,
            "instructions": (
                "The SERP filter judged every result as off-topic for this "
                "gap (raw LLM judge returned zero usable scores). Do not "
                "fetch any of the rejected URLs and do not retry this query "
                "with similar keywords — reformulate instead. Practical "
                "moves: change entity spelling, switch language "
                "(e.g. Thai ↔ English), narrow or broaden the geographic "
                "scope, shift the timeframe, or drop the most specific "
                "term to widen recall."
            ),
        }
        text = json.dumps(payload, ensure_ascii=False)
        return ContentChunk(
            id="serp_filter_no_results",
            text=text,
            order=0,
            start_page=None,
            end_page=None,
            key="serp_filter_no_results",
            chunk_id="0",
            url="",
            title="No relevant results — reformulate query",
        )

    def _serp_results_to_content_chunks(
        self, results: list[WebSearchResult]
    ) -> list[ContentChunk]:
        """One chunk per SERP row; ``text`` is JSON with url, domain, title, snippet."""
        out: list[ContentChunk] = []
        for i, r in enumerate(results):
            payload = {
                "url": r.url,
                "domain": r.display_link,
                "title": r.title,
                "snippet": r.snippet,
            }
            if r.content:
                payload["content"] = r.content
            # Surface the SERP filter's relevance score to the agent. Two decimals
            # is enough resolution for the band-based guidance in the prompt
            # (≥0.85 = primary source, prefer fetch over another search). Absent
            # when the filter was disabled, fell back, or the LLM judge failed —
            # the agent then falls back to snippet-text heuristics.
            if r.relevance_score is not None:
                payload["relevance_score"] = round(r.relevance_score, 2)

            text = json.dumps(payload, ensure_ascii=False)

            title_ascii = unidecode(r.title)
            name = f'{r.display_link}: "{title_ascii}"'
            out.append(
                ContentChunk(
                    id=name,
                    text=text,
                    order=i,
                    start_page=None,
                    end_page=None,
                    key=name,
                    chunk_id=str(i),
                    url=r.url,
                    title=name,
                )
            )
        return out

    async def _run_fetch_urls(
        self,
        *,
        urls: list[str],
        objective: str,
    ) -> list[ContentChunk]:
        self.notify_name = "**Reading Web Pages**"
        self.notify_message = objective
        await self.notify_callback()

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="FETCH_URLS",
                execution_time=0,
                config={
                    "objective": objective,
                    "urls": list(urls),
                },
            )
        )

        urls = list(urls)
        crawler = self.crawler_service.config.crawler_type.value
        time_start = time()
        _LOGGER.info("Company %s Crawling %s URLs", self.company_id, len(urls))
        await self._message_log_callback.log_queries(urls)
        with metric_scope(crawl_duration, crawl_errors, crawler=crawler):
            contents = await self.crawler_service.crawl(urls)
        delta_time = time() - time_start

        results = [
            WebSearchResult(url=u, content=c, snippet="", title="")
            for u, c in zip(urls, contents)
        ]
        await self._message_log_callback.log_web_search_results(results)

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="FETCH_URLS.crawl",
                execution_time=delta_time,
                config=self.crawler_service.config.crawler_type.name,
                extra={"urls": urls, "number_of_results": len(results)},
            )
        )

        self.notify_name = "**Analyzing Web Pages**"
        self.notify_message = objective
        await self.notify_callback()
        await self._message_log_callback.log_progress("_Analyzing Web Pages_")

        content_focus = objective
        content_results = await self._content_processing(content_focus, results)

        if self.chunk_relevancy_sort_config.enabled:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = objective
            await self.notify_callback()
            await self._message_log_callback.log_progress("_Resorting Sources_")

        flat_chunks = await self._select_relevant_sources(
            content_focus, content_results
        )
        return flat_chunks
