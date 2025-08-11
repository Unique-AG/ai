import logging

from pydantic import BaseModel, ValidationError
from quart import g, has_app_context
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    ModelCapabilities,
)
from unique_toolkit.language_model.prompt import Prompt
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
)
from unique_toolkit.language_model.service import (
    LanguageModelService,
)

from _common.evaluators.config import (
    EvaluationMetricConfig,
)
from _common.evaluators.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
)
from _common.evaluators.exception import EvaluatorException
from _common.evaluators.output_parser import (
    parse_eval_metric_result,
    parse_eval_metric_result_structured_output,
)
from _common.evaluators.schemas import (
    EvaluationMetricInput,
    EvaluationMetricInputFieldName,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from default_language_model import DEFAULT_GPT_35_TURBO

from .prompts import (
    CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
    CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG_STRUCTURED_OUTPUT,
    CONTEXT_RELEVANCY_METRIC_USER_MSG,
    CONTEXT_RELEVANCY_METRIC_USER_MSG_STRUCTURED_OUTPUT,
)

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"

default_config = EvaluationMetricConfig(
    enabled=False,
    name=EvaluationMetricName.CONTEXT_RELEVANCY,
    language_model=LanguageModelInfo.from_name(DEFAULT_GPT_35_TURBO),
    custom_prompts={
        SYSTEM_MSG_KEY: CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
        USER_MSG_KEY: CONTEXT_RELEVANCY_METRIC_USER_MSG,
    },
)

relevancy_required_input_fields = [
    EvaluationMetricInputFieldName.INPUT_TEXT,
    EvaluationMetricInputFieldName.CONTEXT_TEXTS,
]


class ContextRelevancyEvaluator:
    def __init__(
        self,
        event: ChatEvent,
    ):
        self.chat_service = ChatService(event)
        self.language_model_service = LanguageModelService(event)
        module_name = (
            getattr(g, "module_name", "NO_CONTEXT")
            if has_app_context()
            else ""
        )
        self.logger = logging.getLogger(f"{module_name}.{__name__}")

    async def analyze(
        self,
        input: EvaluationMetricInput,
        config: EvaluationMetricConfig = default_config,
        structured_output_schema: type[BaseModel] | None = None,
    ) -> EvaluationMetricResult | None:
        """
        Analyzes the level of relevancy of a context by comparing
        it with the input text.

        Args:
            input (EvaluationMetricInput): The input for the metric.
            config (EvaluationMetricConfig): The configuration for the metric.

        Returns:
            EvaluationMetricResult | None

        Raises:
            EvaluatorException: If the context texts are empty or required fields are missing or error occurred during evaluation.
        """
        if config.enabled is False:
            self.logger.info("Hallucination metric is not enabled.")
            return None

        input.validate_required_fields(relevancy_required_input_fields)

        if len(input.context_texts) == 0:
            error_message = "No context texts provided."
            raise EvaluatorException(
                user_message=error_message,
                error_message=error_message,
            )

        try:
            # Handle structured output if enabled and supported by the model
            if (
                structured_output_schema
                and ModelCapabilities.STRUCTURED_OUTPUT
                in config.language_model.capabilities
            ):
                return await self._handle_structured_output(
                    input, config, structured_output_schema
                )

            # Handle regular output
            return await self._handle_regular_output(input, config)

        except Exception as e:
            error_message = "Unknown error occurred during context relevancy metric analysis"
            raise EvaluatorException(
                error_message=f"{error_message}: {e}",
                user_message=error_message,
                exception=e,
            )

    async def _handle_structured_output(
        self,
        input: EvaluationMetricInput,
        config: EvaluationMetricConfig,
        structured_output_schema: type[BaseModel],
    ) -> EvaluationMetricResult:
        """Handle the structured output case for context relevancy evaluation."""
        self.logger.info(
            "Using structured output for context relevancy evaluation."
        )
        msgs = self._compose_msgs(input, config, enable_structured_output=True)
        result = await self.language_model_service.complete_async(
            messages=msgs,
            model_name=config.language_model.name,
            structured_output_model=structured_output_schema,
            structured_output_enforce_schema=True,
            other_options=config.additional_llm_options,
        )

        try:
            result_content = EvaluationSchemaStructuredOutput.model_validate(
                result.choices[0].message.parsed
            )
        except ValidationError as e:
            error_message = "Error occurred during structured output validation of the context relevancy evaluation."
            raise EvaluatorException(
                error_message=error_message,
                user_message=error_message,
                exception=e,
            )

        return parse_eval_metric_result_structured_output(
            result_content, EvaluationMetricName.CONTEXT_RELEVANCY
        )

    async def _handle_regular_output(
        self,
        input: EvaluationMetricInput,
        config: EvaluationMetricConfig,
    ) -> EvaluationMetricResult:
        """Handle the regular output case for context relevancy evaluation."""
        msgs = self._compose_msgs(
            input, config, enable_structured_output=False
        )
        result = await self.language_model_service.complete_async(
            messages=msgs,
            model_name=config.language_model.name,
            other_options=config.additional_llm_options,
        )

        result_content = result.choices[0].message.content
        if not result_content or not isinstance(result_content, str):
            error_message = (
                "Context relevancy evaluation did not return a result."
            )
            raise EvaluatorException(
                error_message=error_message,
                user_message=error_message,
            )

        return parse_eval_metric_result(
            result_content, EvaluationMetricName.CONTEXT_RELEVANCY
        )

    def _compose_msgs(
        self,
        input: EvaluationMetricInput,
        config: EvaluationMetricConfig,
        enable_structured_output: bool,
    ) -> LanguageModelMessages:
        """
        Composes the messages for the relevancy metric.
        """
        system_msg_content = self._get_system_prompt(
            config, enable_structured_output
        )
        system_msg = Prompt(system_msg_content).to_system_msg()

        user_msg = Prompt(
            self._get_user_prompt(config, enable_structured_output),
            input_text=input.input_text,
            context_texts=input.get_joined_context_texts(),
        ).to_user_msg()

        return LanguageModelMessages([system_msg, user_msg])

    def _get_system_prompt(
        self,
        config: EvaluationMetricConfig,
        enable_structured_output: bool,
    ):
        if (
            enable_structured_output
            and ModelCapabilities.STRUCTURED_OUTPUT
            in config.language_model.capabilities
        ):
            return config.custom_prompts.setdefault(
                SYSTEM_MSG_KEY,
                CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG_STRUCTURED_OUTPUT,
            )
        else:
            return config.custom_prompts.setdefault(
                SYSTEM_MSG_KEY,
                CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
            )

    def _get_user_prompt(
        self,
        config: EvaluationMetricConfig,
        enable_structured_output: bool,
    ):
        if enable_structured_output:
            return config.custom_prompts.setdefault(
                USER_MSG_KEY,
                CONTEXT_RELEVANCY_METRIC_USER_MSG_STRUCTURED_OUTPUT,
            )
        else:
            return config.custom_prompts.setdefault(
                USER_MSG_KEY,
                CONTEXT_RELEVANCY_METRIC_USER_MSG,
            )
