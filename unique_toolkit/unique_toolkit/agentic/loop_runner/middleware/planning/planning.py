import json
import logging
from typing import Unpack

from pydantic import BaseModel

from unique_toolkit import LanguageModelService
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    _LoopIterationRunnerKwargs,
)
from unique_toolkit.agentic.loop_runner.middleware.planning.schema import (
    PlanningSchemaConfig,
    get_planning_schema,
)
from unique_toolkit.agentic.tools.utils import failsafe_async
from unique_toolkit.chat.service import LanguageModelStreamResponse
from unique_toolkit.language_model import (
    LanguageModelAssistantMessage,
)

_LOGGER = logging.getLogger(__name__)


class PlanningConfig(BaseModel):
    model_config = get_configuration_dict()

    planning_schema_config: PlanningSchemaConfig = PlanningSchemaConfig()


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

        response = await self._llm_service.complete_async(
            messages=kwargs["messages"],
            model_name=kwargs["model"].name,
            structured_output_model=planning_schema,
            other_options=kwargs.get("other_options", {}),
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
