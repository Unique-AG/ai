from logging import Logger

from unique_toolkit.agentic.tools.a2a.config import SubAgentToolConfig
from unique_toolkit.agentic.tools.a2a.service import SubAgentTool, ToolProgressReporter
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent


class A2AManager:
    def __init__(
        self,
        logger: Logger,
        tool_progress_reporter: ToolProgressReporter,
    ):
        self._logger = logger
        self._tool_progress_reporter = tool_progress_reporter

    def get_all_sub_agents(
        self, tool_configs: list[ToolBuildConfig], event: ChatEvent
    ) -> tuple[list[ToolBuildConfig], list[Tool[BaseToolConfig]]]:
        sub_agents = []

        for tool_config in tool_configs:
            if not tool_config.is_sub_agent:
                continue

            if not isinstance(tool_config.configuration, SubAgentToolConfig):
                self._logger.error(
                    "tool_config.configuration must be of type SubAgentToolConfig"
                )
                continue

            sub_agent_tool_config: SubAgentToolConfig = tool_config.configuration

            sub_agents.append(
                SubAgentTool(
                    configuration=sub_agent_tool_config,
                    event=event,
                    tool_progress_reporter=self._tool_progress_reporter,
                )
            )

        filtered_tool_config = [
            tool_config for tool_config in tool_configs if not tool_config.is_sub_agent
        ]

        return filtered_tool_config, sub_agents
