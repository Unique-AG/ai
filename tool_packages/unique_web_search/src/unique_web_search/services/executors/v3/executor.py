"""Web Search V3 executor: one command per invocation (`search` or `fetch_urls`)."""

from __future__ import annotations

import json
import logging
from time import time

from unidecode import unidecode
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import LanguageModelFunction
from unique_toolkit.monitoring import metric_scope

from unique_web_search.metrics import (
    crawl_duration,
    crawl_errors,
    search_duration,
    search_errors,
    search_total,
)
from unique_web_search.schema import StepDebugInfo
from unique_web_search.services.executors.base_executor import BaseWebSearchExecutor
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v3.schema import (
    WebSearchV3FetchUrlsPayload,
    WebSearchV3SearchPayload,
    WebSearchV3ToolParameters,
)
from unique_web_search.services.search_engine.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)


class WebSearchV3Executor(BaseWebSearchExecutor[WebSearchV3ToolParameters]):
    """Run either ``search`` (SERP-only JSON chunks) or ``fetch_urls`` (crawl + pipeline)."""

    def __init__(
        self,
        services: ExecutorServiceContext,
        config: ExecutorConfiguration,
        callbacks: ExecutorCallbacks,
        tool_call: LanguageModelFunction,
        tool_parameters: WebSearchV3ToolParameters,
    ):
        super().__init__(
            services=services,
            config=config,
            callbacks=callbacks,
            tool_call=tool_call,
            tool_parameters=tool_parameters,
        )

    async def run(self) -> list[ContentChunk]:
        p = self.tool_parameters
        if p.search is not None:
            await self._message_log_callback.log_progress("_Executing Search_")
            return await self._run_search(
                p.search, user_intent=p.user_intent, objective=p.objective
            )
        if p.fetch_urls is not None:
            await self._message_log_callback.log_progress("_Reading Web Pages_")
            return await self._run_fetch_urls(
                p.fetch_urls, user_intent=p.user_intent, objective=p.objective
            )
        msg = "WebSearchV3ToolParameters requires exactly one of search or fetch_urls."
        raise ValueError(msg)

    async def _run_search(
        self,
        cmd: WebSearchV3SearchPayload,
        *,
        user_intent: str,
        objective: str,
    ) -> list[ContentChunk]:
        query_in = cmd.query

        self.notify_name = "**Searching Web**"
        self.notify_message = f"{user_intent} · {objective}"
        await self.notify_callback()

        elicited = await self._ff_elicitate_queries([query_in])
        query = elicited[0]

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="SEARCH",
                execution_time=0,
                config={
                    "user_intent": user_intent,
                    "objective": objective,
                    "query": query,
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
        await self._message_log_callback.log_web_search_results(results)

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

        chunks = self._serp_results_to_content_chunks(results)
        return chunks

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
        cmd: WebSearchV3FetchUrlsPayload,
        *,
        user_intent: str,
        objective: str,
    ) -> list[ContentChunk]:

        self.notify_name = "**Reading Web Pages**"
        self.notify_message = f"{user_intent} · {objective}"
        await self.notify_callback()

        self.debug_info.steps.append(
            StepDebugInfo(
                step_name="FETCH_URLS",
                execution_time=0,
                config={
                    "user_intent": user_intent,
                    "objective": objective,
                    "urls": list(cmd.urls),
                },
            )
        )

        urls = list(cmd.urls)
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
        self.notify_message = f"{user_intent} · {objective}"
        await self.notify_callback()
        await self._message_log_callback.log_progress("_Analyzing Web Pages_")

        content_focus = f"{user_intent}\n\n{objective}"
        content_results = await self._content_processing(content_focus, results)

        if self.chunk_relevancy_sort_config.enabled:
            self.notify_name = "**Resorting Sources**"
            self.notify_message = f"{user_intent} · {objective}"
            await self.notify_callback()
            await self._message_log_callback.log_progress("_Resorting Sources_")

        flat_chunks = await self._select_relevant_sources(
            content_focus, content_results
        )
        return flat_chunks
