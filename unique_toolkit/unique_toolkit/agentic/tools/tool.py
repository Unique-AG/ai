from __future__ import annotations

from abc import ABC, abstractmethod
from logging import getLogger
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from typing_extensions import deprecated

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.config import ToolBuildConfig, ToolSelectionPolicy
from unique_toolkit.agentic.tools.schemas import (
    BaseToolConfig,
    ToolCallResponse,
    ToolPrompts,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model import LanguageModelToolDescription

if TYPE_CHECKING:
    pass
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)

if TYPE_CHECKING:
    from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
    from unique_toolkit.app.schemas import ChatEvent

ConfigType = TypeVar("ConfigType", bound=BaseToolConfig)

ToolBuildConfig.model_rebuild()


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

    def takes_control(self) -> bool:
        """
        Some tools require to take control of the conversation with the user and do not want the orchestrator to intervene.
        this function indicates whether the tool takes control or not. It yanks the control away from the orchestrator.
        A typical use-case is deep-research.
        """
        return False

    @property
    def configuration(self) -> BaseToolConfig:
        """The configuration of the tool."""
        return self.settings.configuration

    @abstractmethod
    def tool_description(self) -> LanguageModelToolDescription:
        raise NotImplementedError

    def tool_description_as_json(self) -> dict[str, Any]:
        parameters = self.tool_description().parameters
        if not isinstance(parameters, dict):
            return parameters.model_json_schema()
        else:
            return parameters

    # TODO: This method should be a property
    def tool_description_for_system_prompt(self) -> str:
        return ""

    # TODO: This method should be a property
    def tool_format_information_for_system_prompt(self) -> str:
        return ""

    # TODO: This method should be a property
    def tool_description_for_user_prompt(self) -> str:
        return ""

    # TODO: This method should be a property
    def tool_format_information_for_user_prompt(self) -> str:
        return ""

    # TODO: This method should be a property
    def tool_format_reminder_for_user_prompt(self) -> str:
        """A short reminder for the user prompt for formatting rules for the tool.
        You can use this if the LLM fails to follow the formatting rules.
        """
        return ""

    # TODO: This method should be a property
    def tool_system_reminder(self) -> str:
        """A per-turn ``<system-reminder>`` block for the tool.

        Override this when the tool's state changes between turns and
        the model must see the fresh state on every loop iteration
        (e.g. the Skill tool's listing of currently available skills).
        The returned string is injected by the orchestrator as its own
        ``{"type": "text"}`` part on the latest user message, alongside
        ``tool_description_for_user_prompt``. Return ``""`` when there
        is nothing to inject.
        """
        return ""

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
            tool_system_reminder=self.tool_system_reminder(),
        )

    @overload
    def __init__(self, config: ConfigType) -> None: ...

    @overload
    def __init__(
        self,
        config: ConfigType,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    def __init__(
        self,
        config: ConfigType,
        event: ChatEvent | None = None,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ) -> None:
        """Initialize the tool.

        Preferred (decoupled): `Tool(config)` — configuration only.

        Backward compatible: `Tool(config, event, tool_progress_reporter)` — creates
        deprecated chat_service, language_model_service, message_step_logger for
        legacy subclasses.
        """
        self.settings = ToolBuildConfig(
            name=self.name,
            configuration=config,
        )

        self.config = config
        module_name = "default overwrite for module name"
        self.logger = getLogger(f"{module_name}.{__name__}")
        self.debug_info: dict[str, Any] = {}

        if event is not None:
            from unique_toolkit.agentic.message_log_manager.service import (
                MessageStepLogger,
            )
            from unique_toolkit.chat.service import ChatService
            from unique_toolkit.language_model.service import LanguageModelService

            self._event = event
            self._tool_progress_reporter = tool_progress_reporter
            self._chat_service = ChatService(event)
            self._language_model_service = LanguageModelService.from_event(event)
            self._message_step_logger = MessageStepLogger(
                chat_service=self._chat_service,
            )

    @property
    @deprecated(
        "Never reuse event. Dangerous. Prefer Tool(config) and inject context in run()."
    )
    def event(self) -> ChatEvent:
        if not hasattr(self, "_event"):
            raise AttributeError(
                "event not available (tool was initialized with config only). "
            )
        return self._event

    @property
    @deprecated(
        "Do not use; tied to chat frontend. Prefer Tool(config) and inject in run()."
    )
    def chat_service(self):
        if not hasattr(self, "_chat_service"):
            raise AttributeError(
                "chat_service not available (tool was initialized with config only). "
            )
        return self._chat_service

    @property
    @deprecated(
        "Do not use; tied to chat frontend. Prefer Tool(config) and inject in run()."
    )
    def language_model_service(self):
        if not hasattr(self, "_language_model_service"):
            raise AttributeError(
                "language_model_service not available (tool was initialized with config only). "
            )
        return self._language_model_service

    @property
    @deprecated(
        "Do not use; tied to chat frontend. Prefer Tool(config) and inject in run()."
    )
    def tool_progress_reporter(self) -> ToolProgressReporter | None:
        return getattr(self, "_tool_progress_reporter", None)
