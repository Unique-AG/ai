import json
import logging
from typing import Unpack

from openai import AsyncOpenAI
from openai.types.responses import (
    Response,
    ResponseFormatTextJSONSchemaConfigParam,
    ResponseInputItemParam,
    ResponseOutputMessage,
    ResponseTextConfigParam,
)
from pydantic import BaseModel, Field

from unique_toolkit import LanguageModelService
from unique_toolkit._common.execution import failsafe_async
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    ResponsesLoopIterationRunner,
    _LoopIterationRunnerKwargs,
    _ResponsesLoopIterationRunnerKwargs,
)
from unique_toolkit.agentic.loop_runner.middleware.planning.schema import (
    PlanningSchemaConfig,
    get_planning_schema,
)
from unique_toolkit.chat.responses_api import convert_messages_to_openai
from unique_toolkit.chat.service import LanguageModelStreamResponse
from unique_toolkit.language_model import (
    LanguageModelAssistantMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    ResponsesLanguageModelStreamResponse,
)

_LOGGER = logging.getLogger(__name__)


def _get_first_output_text(response: Response) -> str | None:
    """
    The Responses API can return multiple output items when doing structured output
    (https://community.openai.com/t/multiple-outputs-from-responses-api/1291026),
    We should tell the model not to do this in the schema, as well as extract only the first one
    """
    if len(response.output) > 1:
        _LOGGER.warning(
            "Model returned %i outputs, keeping only the first one",
            len(response.output),
        )

    for item in response.output:
        if isinstance(item, ResponseOutputMessage):
            for content in item.content:
                if content.type == "output_text" and content.text:
                    return content.text
    return None


class PlanningConfig(BaseModel):
    model_config = get_configuration_dict()

    planning_schema_config: PlanningSchemaConfig = PlanningSchemaConfig()
    ignored_options: list[str] = Field(
        default=["parallel_tool_calls"],
        description="A list of options to ignore when calling the LLM for the planning step.",
    )


class PlanningMiddleware(LoopIterationRunner):
    def __init__(
        self,
        *,
        loop_runner: LoopIterationRunner,
        config: PlanningConfig,
        llm_service: LanguageModelService,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self._config = config
        self._loop_runner = loop_runner
        self._history_manager = history_manager
        self._llm_service = llm_service

    @failsafe_async(failure_return_value=None, logger=_LOGGER)
    async def _run_plan_step(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelAssistantMessage | None:
        planning_schema = get_planning_schema(self._config.planning_schema_config)

        other_options = {
            k: v
            for k, v in kwargs.get("other_options", {}).items()
            if k not in self._config.ignored_options
        }
        response = await self._llm_service.complete_async(
            messages=kwargs["messages"],
            model_name=kwargs["model"].name,
            structured_output_model=planning_schema,
            other_options=other_options,
        )

        if response.choices[0].message.parsed is None:
            _LOGGER.info("Error parsing planning response")
            return None

        return LanguageModelAssistantMessage(
            content=json.dumps(response.choices[0].message.parsed)
        )

    async def __call__(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        assistant_message = await self._run_plan_step(**kwargs)

        if assistant_message is None:
            _LOGGER.info(
                "Error executing planning step, proceeding without planning step"
            )
            return await self._loop_runner(**kwargs)

        if self._history_manager is not None:
            self._history_manager.add_assistant_message(assistant_message)

        kwargs["messages"] = (
            kwargs["messages"].builder().append(assistant_message).build()
        )
        return await self._loop_runner(**kwargs)


class ResponsesPlanningMiddleware(ResponsesLoopIterationRunner):
    def __init__(
        self,
        *,
        loop_runner: ResponsesLoopIterationRunner,
        config: PlanningConfig,
        openai_client: AsyncOpenAI,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self._config = config
        self._loop_runner = loop_runner
        self._history_manager = history_manager
        self._openai_client = openai_client

    @failsafe_async(failure_return_value=None, logger=_LOGGER)
    async def _run_plan_step(
        self,
        openai_messages: str | list[ResponseInputItemParam],
        model_name: str,
    ) -> str | None:
        planning_schema = get_planning_schema(self._config.planning_schema_config)

        response = await self._openai_client.responses.create(
            model=model_name,
            input=openai_messages,
            text=ResponseTextConfigParam(
                {
                    "format": ResponseFormatTextJSONSchemaConfigParam(
                        {
                            "type": "json_schema",
                            "name": planning_schema.get("title", "Plan"),
                            "schema": planning_schema,
                            "strict": False,
                        }
                    )
                }
            ),
        )

        output_text = _get_first_output_text(response)
        if not output_text:
            _LOGGER.info("Empty planning response")
            return None

        return output_text

    async def __call__(
        self, **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs]
    ) -> ResponsesLanguageModelStreamResponse:
        openai_messages = convert_messages_to_openai(kwargs["messages"])

        output_text = await self._run_plan_step(
            openai_messages=openai_messages,
            model_name=kwargs["model"].name,
        )

        if output_text is None:
            _LOGGER.info(
                "Error executing planning step, proceeding without planning step"
            )
            return await self._loop_runner(**kwargs)

        assistant_message = LanguageModelAssistantMessage(content=output_text)

        if self._history_manager is not None:
            self._history_manager.add_assistant_message(assistant_message)

        if isinstance(kwargs["messages"], str):
            kwargs["messages"] = [
                LanguageModelUserMessage(content=kwargs["messages"]),
                assistant_message,
            ]
        elif isinstance(kwargs["messages"], LanguageModelMessages):
            kwargs["messages"] = (
                kwargs["messages"].builder().append(assistant_message).build()
            )
        else:
            kwargs["messages"] = list(kwargs["messages"]) + [assistant_message]

        return await self._loop_runner(**kwargs)
