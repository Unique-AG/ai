"""LLM judge for V3 `search` outcomes: snippet sufficiency, fetch hint, follow-up queries."""

import json
import logging
from time import time

from jinja2 import Template
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model import LanguageModelService

from unique_web_search.services.executors.context import MessageLogCallback
from unique_web_search.services.executors.v3.llm_judge.config import V3LlmJudgeConfig
from unique_web_search.services.executors.v3.llm_judge.schema import (
    V3SearchOutcomeJudgeResult,
)
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.structured_llm import complete_structured_llm

_LOGGER = logging.getLogger(__name__)


def _format_numbered_results(results: list[WebSearchResult]) -> str:
    lines: list[dict] = []
    for i, r in enumerate(results):
        result = r.model_dump()
        result["result_index"] = i
        lines.append(result)

    return json.dumps(lines, indent=2)


class V3SearchOutcomeJudge:
    """Runs a structured LLM over SERP rows to advise fetch vs snippets-only."""

    def __init__(
        self,
        language_model_service: LanguageModelService,
        language_model: LMI,
        config: V3LlmJudgeConfig,
    ):
        self._language_model_service = language_model_service
        self._language_model = language_model
        self._config = config

    async def judge(
        self,
        objective: str,
        results: list[WebSearchResult],
        message_log: MessageLogCallback,
    ) -> V3SearchOutcomeJudgeResult:
        if not self._config.enabled or not results:
            return V3SearchOutcomeJudgeResult(
                url_indices_to_fetch=[],
                suggested_follow_up_queries=[],
                rationale="Search-outcome judge disabled or no results.",
            )

        await message_log.post_message("Scanning search results_")

        numbered_results = _format_numbered_results(results)
        ctx = {"objective": objective, "numbered_results": numbered_results}
        system_message = Template(self._config.system_prompt).render(**ctx)
        user_message = Template(self._config.user_prompt_template).render(**ctx)

        start = time()
        verdict = await complete_structured_llm(
            self._language_model_service,
            self._language_model,
            system_message=system_message,
            user_message=user_message,
            response_model=V3SearchOutcomeJudgeResult,
        )
        elapsed = time() - start

        _LOGGER.info(
            "V3 search-outcome judge finished in %.2fs",
            elapsed,
        )

        await message_log.log_progress("_Scanning search results completed_")

        return verdict
