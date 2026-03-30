"""Argument screening service for web search tool calls.

This module provides an LLM-based screening agent that inspects tool call
arguments for sensitive information before execution. When the agent determines
arguments are unsafe, it raises an exception to block the tool call.
"""

import json
import logging

from jinja2 import Template
from pydantic import Field
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.services.argument_screening.config import (
    ArgumentScreeningConfig,
)
from unique_web_search.services.argument_screening.exceptions import (
    ArgumentScreeningException,
)

_LOGGER = logging.getLogger(__name__)


class ArgumentScreeningResult(StructuredOutputModel):
    """Structured LLM output for the screening verdict."""

    go: bool = Field(
        description="True if the arguments are safe to proceed, False if they should be blocked."
    )
    reason: str = Field(description="A concise one-liner explaining the verdict.")


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

    async def __call__(self, arguments: dict) -> None:
        """Screen tool call arguments; raises on rejection.

        Args:
            arguments: The raw tool call arguments dict.

        Raises:
            ArgumentScreeningException: If the screening agent flags the arguments.
        """
        if not self._config.enabled:
            return

        _LOGGER.info("Running argument screening agent...")

        serialized_args = json.dumps(arguments, indent=2, default=str)
        user_prompt = Template(self._config.user_prompt_template).render(
            arguments=serialized_args,
            guidelines=self._config.guidelines,
        )

        messages = (
            MessagesBuilder()
            .system_message_append(self._config.system_prompt)
            .user_message_append(user_prompt)
            .build()
        )

        response = await self._language_model_service.complete_async(
            messages,
            model_name=self._language_model.name,
            structured_output_model=ArgumentScreeningResult,
            structured_output_enforce_schema=True,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            _LOGGER.warning(
                "Argument screening returned unparseable response, allowing execution."
            )
            return

        result = ArgumentScreeningResult.model_validate(parsed)
        _LOGGER.info(
            f"Argument screening verdict: go={result.go}, reason={result.reason}"
        )

        if not result.go:
            raise ArgumentScreeningException(reason=result.reason)
