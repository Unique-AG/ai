from logging import Logger
from typing import overload

from typing_extensions import deprecated

from unique_toolkit.agentic.tools.a2a.response_watcher import SubAgentResponseWatcher
from unique_toolkit.agentic.tools.a2a.tool import SubAgentTool, SubAgentToolConfig
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model import LanguageModelService

_EVENT_INJECTION_DEPRECATED = (
    "Passing event is deprecated. Inject chat_service and language_model_service."
)


class A2AManager:
    def __init__(
        self,
        logger: Logger,
        tool_progress_reporter: ToolProgressReporter,
        response_watcher: SubAgentResponseWatcher,
    ):
        self._logger = logger
        self._tool_progress_reporter = tool_progress_reporter
        self._response_watcher = response_watcher

    @overload
    def get_all_sub_agents(
        self,
        tool_configs: list[ToolBuildConfig],
        *,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
    ) -> tuple[list[ToolBuildConfig], list[SubAgentTool]]: ...

    @overload
    @deprecated(_EVENT_INJECTION_DEPRECATED)
    def get_all_sub_agents(
        self,
        tool_configs: list[ToolBuildConfig],
        event: ChatEvent,
    ) -> tuple[list[ToolBuildConfig], list[SubAgentTool]]: ...

    def get_all_sub_agents(
        self,
        tool_configs: list[ToolBuildConfig],
        event: ChatEvent | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
    ) -> tuple[list[ToolBuildConfig], list[SubAgentTool]]:
        sub_agents = []

        for tool_config in tool_configs:
            if not tool_config.is_sub_agent:
                continue

            if not tool_config.is_enabled:
                self._logger.info(
                    "Skipping disabled sub-agent '%s'",
                    tool_config.name,
                )
                continue

            if not isinstance(tool_config.configuration, SubAgentToolConfig):
                self._logger.error(
                    "tool_config.configuration must be of type SubAgentToolConfig"
                )
                continue

            sub_agent_tool_config = tool_config.configuration

            try:
                if chat_service is not None and language_model_service is not None:
                    sub_agent = SubAgentTool(
                        configuration=sub_agent_tool_config,
                        tool_progress_reporter=self._tool_progress_reporter,
                        name=tool_config.name,
                        display_name=tool_config.display_name,
                        response_watcher=self._response_watcher,
                        chat_service=chat_service,
                        language_model_service=language_model_service,
                    )
                elif event is not None:
                    sub_agent = SubAgentTool(
                        configuration=sub_agent_tool_config,
                        event=event,
                        tool_progress_reporter=self._tool_progress_reporter,
                        name=tool_config.name,
                        display_name=tool_config.display_name,
                        response_watcher=self._response_watcher,
                    )
                else:
                    raise ValueError(
                        "get_all_sub_agents requires event or injected "
                        "chat_service and language_model_service"
                    )
                sub_agents.append(sub_agent)
            except Exception:
                self._logger.warning(
                    "Skipping sub-agent '%s' due to initialization failure.",
                    tool_config.name,
                    exc_info=True,
                )

        filtered_tool_config = [
            tool_config for tool_config in tool_configs if not tool_config.is_sub_agent
        ]

        return filtered_tool_config, sub_agents
