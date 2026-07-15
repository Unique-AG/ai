"""Argument screening service for web search tool calls.

This module provides an LLM-based screening agent that inspects tool call
arguments for sensitive information before execution. When the agent determines
arguments are unsafe, it raises an exception to block the tool call.
"""

import json
import logging
from time import time

from jinja2 import Template
from pydantic import Field, PrivateAttr
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model import LanguageModelService

from unique_web_search.schema import StepDebugInfo, WebSearchDebugInfo
from unique_web_search.services.argument_screening.config import (
    ArgumentScreeningConfig,
)
from unique_web_search.services.argument_screening.exceptions import (
    ArgumentScreeningUnparseableResponseException,
)
from unique_web_search.services.argument_screening.prompts import (
    DEFAULT_GUIDELINES_WITH_KEYWORDS_TEMPLATE,
)
from unique_web_search.services.message_log import WebSearchMessageLogger
from unique_web_search.services.structured_llm import (
    StructuredLlmUnparseableResponseError,
    complete_structured_llm,
)

_LOGGER = logging.getLogger(__name__)


class ArgumentScreeningResult(StructuredOutputModel):
    """Structured LLM output for the screening verdict."""

    go: bool = Field(
        description="True if the arguments are safe to proceed, False if they should be blocked."
    )
    reason: str = Field(description="A concise one-liner explaining the verdict.")

    _execution_time: float = PrivateAttr(default=0)

    @property
    def execution_time(self) -> float:
        return self._execution_time


class ArgumentScreeningService:
    """Service that screens tool call arguments using an LLM."""

    def __init__(
        self,
        language_model_service: LanguageModelService,
        language_model: LMI,
        config: ArgumentScreeningConfig,
    ):
        self._language_model_service = language_model_service
        self._language_model = language_model
        self._config = config

    async def __call__(
        self,
        arguments: dict,
        message_log_callback: WebSearchMessageLogger,
        debug_info: WebSearchDebugInfo | None = None,
    ) -> ArgumentScreeningResult:
        """Screen tool call arguments; raises on rejection.

        Args:
            arguments: The raw tool call arguments dict.
            debug_info: when given, receives per-invocation usage stats from the
                screening LLM call via `debug_info.add_invocation(...)`.

        Raises:
            ArgumentScreeningException: If the screening agent flags the arguments.
        """
        if not self._config.enabled:
            return ArgumentScreeningResult(
                go=True, reason="Argument screening disabled"
            )

        await message_log_callback.log_progress("PII Detection running...")

        start_time = time()
        result = await self._screen_arguments(arguments, debug_info)
        result._execution_time = time() - start_time

        if not result.go:
            await message_log_callback.log_progress(f"PII Detection: {result.reason}")
        else:
            await message_log_callback.log_progress("PII Detection completed!")

        return result

    async def _screen_arguments(
        self, arguments: dict, debug_info: WebSearchDebugInfo | None = None
    ) -> ArgumentScreeningResult:
        _LOGGER.info("Running argument screening agent...")

        serialized_args = json.dumps(arguments, indent=2, default=str)
        rendered_guidelines = Template(
            DEFAULT_GUIDELINES_WITH_KEYWORDS_TEMPLATE
        ).render(
            guidelines=self._config.guidelines,
            organization_specific_blocked_keywords=(
                self._config.organization_specific_blocked_keywords
            ),
        )

        user_prompt = Template(self._config.user_prompt_template).render(
            arguments=serialized_args,
            guidelines=rendered_guidelines,
        )

        try:
            result = await complete_structured_llm(
                self._language_model_service,
                self._language_model,
                system_message=self._config.system_prompt,
                user_message=user_prompt,
                response_model=ArgumentScreeningResult,
                debug_info=debug_info,
            )
        except StructuredLlmUnparseableResponseError as e:
            raise ArgumentScreeningUnparseableResponseException(
                reason="Argument screening agent failed to return a valid response"
            ) from e

        _LOGGER.info(f"Argument screening verdict: go={result.go}")
        return result

    def build_step_debug_info_from_result(
        self, result: ArgumentScreeningResult
    ) -> StepDebugInfo:
        return StepDebugInfo(
            step_name="argument_screening",
            execution_time=result.execution_time,
            config=f"Enabled: {self._config.enabled}",
            extra={"compliant": result.go, "reason": result.reason},
        )

    def build_rejection_response(self, result: ArgumentScreeningResult) -> str:
        return Template(self._config.rejection_response_template).render(
            reason=result.reason
        )
