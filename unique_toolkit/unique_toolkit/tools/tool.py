from abc import ABC, abstractmethod
from logging import getLogger
from typing import Any, Generic, TypeVar, cast

from typing_extensions import deprecated

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import (
    ChatService,
)
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model import LanguageModelToolDescription
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
)
from unique_toolkit.language_model.service import LanguageModelService
from unique_toolkit.tools.config import ToolBuildConfig, ToolSelectionPolicy
from unique_toolkit.tools.schemas import BaseToolConfig, ToolCallResponse, ToolPrompts
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter

from unique_toolkit.tools.agent_chunks_hanlder import AgentChunksHandler

ConfigType = TypeVar("ConfigType", bound=BaseToolConfig)


class Tool(ABC, Generic[ConfigType]):
    name: str
    settings: ToolBuildConfig

    def display_name(self) -> str:
        """The display name of the tool."""
        return self.settings.display_name

    def icon(self) -> str:
        """The icon of the tool."""
        return self.settings.icon

    def selection_policy(self) -> ToolSelectionPolicy:
        """The selection policy of the tool."""
        return self.settings.selection_policy

    def is_exclusive(self) -> bool:
        """Whether the tool is exclusive or not."""
        return self.settings.is_exclusive

    def is_enabled(self) -> bool:
        """Whether the tool is enabled or not."""
        return self.settings.is_enabled

    @abstractmethod
    def tool_description(self) -> LanguageModelToolDescription:
        raise NotImplementedError

    def tool_description_as_json(self) -> dict[str, Any]:
        parameters = self.tool_description().parameters
        if not isinstance(parameters, dict):
            return parameters.model_json_schema()
        else:
            return cast("dict[str, Any]", parameters)

    def tool_description_for_system_prompt(self) -> str:
        return ""

    def tool_format_information_for_system_prompt(self) -> str:
        return ""

    def tool_description_for_user_prompt(self) -> str:
        return ""

    def tool_format_information_for_user_prompt(self) -> str:
        return ""

    def tool_format_reminder_for_user_prompt(self) -> str:
        """A short reminder for the user prompt for formatting rules for the tool.
        You can use this if the LLM fails to follow the formatting rules.
        """
        return ""

    @deprecated("Do not use as is bound to loop agent only")
    @abstractmethod
    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        raise NotImplementedError

    @deprecated(
        "Do not use. The tool should not determine how"
        "it is checked. This should be defined by the user"
        "of the tool."
    )
    @abstractmethod
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        raise NotImplementedError

    @abstractmethod
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        raise NotImplementedError

    @deprecated(
        "Do not use as the evaluation checks should not be determined by\n"
        "the tool. The decision on what check should be done is up to the\n"
        "user of the tool or the dev.",
    )
    @abstractmethod
    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        raise NotImplementedError

    def get_tool_prompts(self) -> ToolPrompts:
        return ToolPrompts(
            name=self.name,
            display_name=self.display_name(),
            tool_description=self.tool_description().description,
            tool_system_prompt=self.tool_description_for_system_prompt(),
            tool_format_information_for_system_prompt=self.tool_format_information_for_system_prompt(),
            input_model=self.tool_description_as_json(),
            tool_user_prompt=self.tool_description_for_user_prompt(),
            tool_format_information_for_user_prompt=self.tool_format_information_for_user_prompt(),
        )

    # Properties that we should soon deprecate

    @property
    @deprecated("Never reuse event. Dangerous")
    def event(self) -> ChatEvent:
        return self._event

    @property
    @deprecated("Do not use this property as directly tied to chat frontend")
    def chat_service(self) -> ChatService:
        return self._chat_service

    @property
    @deprecated("Do not use this property as directly tied to chat frontend")
    def language_model_service(self) -> LanguageModelService:
        return self._language_model_service

    @property
    @deprecated("Do not use this as directly tied to chat frontend")
    def tool_progress_reporter(self) -> ToolProgressReporter | None:
        return self._tool_progress_reporter

    def __init__(
        self,
        config: ConfigType,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ):
        self.settings = ToolBuildConfig(
            name=self.name,
            configuration=config,  # type: ignore
            # the ToolBuildConfig has a wrong type in it to be fixed later.
        )

        self.config = config
        module_name = "default overwrite for module name"
        self.logger = getLogger(f"{module_name}.{__name__}")
        self.debug_info: dict = {}

        # TODO: Remove these properties as soon as possible
        self._event: ChatEvent = event
        self._tool_progress_reporter: ToolProgressReporter | None = (
            tool_progress_reporter
        )

        self._chat_service = ChatService(event)
        self._language_model_service = LanguageModelService(event)
