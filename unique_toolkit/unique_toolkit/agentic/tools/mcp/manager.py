import logging
from typing import overload

from typing_extensions import deprecated

from unique_toolkit.agentic.tools.config import (
    ToolBuildConfig,
    ToolIcon,
    ToolSelectionPolicy,
)
from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig
from unique_toolkit.agentic.tools.mcp.tool_wrapper import MCPToolWrapper
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent, McpServer
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model import LanguageModelService

_EVENT_INJECTION_DEPRECATED = (
    "Passing event is deprecated. Inject chat_service and language_model_service."
)


class MCPManager:
    @overload
    def __init__(
        self,
        mcp_servers: list[McpServer],
        *,
        tool_progress_reporter: ToolProgressReporter,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
    ) -> None: ...

    @overload
    @deprecated(_EVENT_INJECTION_DEPRECATED)
    def __init__(
        self,
        mcp_servers: list[McpServer],
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
    ) -> None: ...

    def __init__(
        self,
        mcp_servers: list[McpServer],
        event: ChatEvent | None = None,
        tool_progress_reporter: ToolProgressReporter | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
    ) -> None:
        if tool_progress_reporter is None:
            raise TypeError("tool_progress_reporter is required")

        self._mcp_servers = mcp_servers
        self._tool_progress_reporter = tool_progress_reporter
        self._chat_service = chat_service
        self._language_model_service = language_model_service

        if chat_service is not None and language_model_service is not None:
            self._event = event
        elif event is not None:
            self._event = event
        else:
            raise ValueError(
                "MCPManager requires event or injected chat_service and "
                "language_model_service"
            )

    def get_mcp_servers(self):
        return self._mcp_servers

    def get_mcp_server_by_id(self, id: str):
        return next((server for server in self._mcp_servers if server.id == id), None)

    def get_all_mcp_tools(self) -> list[Tool[BaseToolConfig]]:
        selected_tools = []
        for server in self._mcp_servers:
            if not hasattr(server, "tools"):
                continue
            if not server.tools:
                continue

            for tool in server.tools:
                try:
                    config = MCPToolConfig(
                        server_id=server.id,
                        server_name=server.name,
                        server_system_prompt=server.system_prompt,
                        server_user_prompt=server.user_prompt,
                        mcp_source_id=server.id,
                    )
                    if (
                        self._chat_service is not None
                        and self._language_model_service is not None
                    ):
                        wrapper = MCPToolWrapper(
                            mcp_server=server,
                            mcp_tool=tool,
                            config=config,
                            tool_progress_reporter=self._tool_progress_reporter,
                            chat_service=self._chat_service,
                            language_model_service=self._language_model_service,
                        )
                    elif self._event is not None:
                        wrapper = MCPToolWrapper(
                            mcp_server=server,
                            mcp_tool=tool,
                            config=config,
                            event=self._event,
                            tool_progress_reporter=self._tool_progress_reporter,
                        )
                    else:
                        raise ValueError(
                            "MCPManager requires event or injected chat_service and "
                            "language_model_service"
                        )
                    wrapper.settings = ToolBuildConfig(  # TODO: this must be refactored to behave like the other tools.
                        name=tool.name,
                        configuration=config,
                        display_name=tool.title or tool.name,
                        is_exclusive=False,
                        is_enabled=True,
                        icon=ToolIcon.BOOK,
                        selection_policy=ToolSelectionPolicy.BY_USER,
                    )
                    selected_tools.append(wrapper)
                except Exception as e:
                    logging.error(
                        f"Error creating MCP tool wrapper for {tool.name}: {e}"
                    )
        return selected_tools
