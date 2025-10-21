import logging
from typing import Literal, Sequence, TypeVar, overload

from openai.types.chat import (
    ChatCompletionNamedToolChoiceParam,
)
from openai.types.responses import ToolParam, response_create_params
from pydantic import BaseModel, Field
from typing_extensions import deprecated

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a import A2AManager, SubAgentTool
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
)
from unique_toolkit.agentic.tools.openai_builtin.manager import OpenAIBuiltInToolManager
from unique_toolkit.agentic.tools.schemas import ToolCallResponse, ToolPrompts
from unique_toolkit.agentic.tools.tool import HasSettingsProtocol, Tool
from unique_toolkit.agentic.tools.tool_manager._utils import (
    execute_tools_parallelized,
    filter_duplicate_tool_calls,
)
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

logger = logging.getLogger(__name__)


class ToolManagerConfig(BaseModel):
    max_tool_calls: int = Field(
        default=10,
        ge=1,
        description="Maximum number of tool calls that can be executed in one iteration.",
    )

    log_exceptions_to_debug_info: bool = Field(
        default=True,
        description="Whether to log exception tracebacks to the debug info of the tool call responses.",
    )


class ToolManager:
    """
    Manages the tools available to the agent and executes tool calls.

    This class is responsible for:
    - Initializing tools based on the provided configuration and runtime events.
    - Filtering tools based on availability, exclusivity, and user-defined constraints.
    - Managing the lifecycle of tools, including retrieval, execution, and logging.
    - Executing tool calls in parallel when possible to optimize performance.
    - Enforcing limits on the number of tool calls and handling duplicate requests.

    Key Features:
    - Dynamic Tool Initialization: Tools are dynamically selected and initialized
      based on runtime events and user preferences.
    - Parallel Execution: Supports asynchronous execution of tools for efficiency.
    - Error Handling: Provides detailed error messages and logs for failed tool calls.
    - Scalability: Designed to handle a large number of tools and tool calls efficiently.

    Only the ToolManager is allowed to interact with the tools directly.
    """

    def __init__(
        self,
        config: ToolManagerConfig,
        tools: list[Tool],
        a2a_tools: list[SubAgentTool],
        mcp_tools: list[Tool],
        builtin_tools: list[OpenAIBuiltInTool],
        tool_choices: list[str] | None = None,
        disabled_tools: list[str] | None = None,
    ) -> None:
        self._config = config
        # Single source of truth - all tools by category
        self._tools = tools
        self._a2a_tools = a2a_tools
        self._mcp_tools = mcp_tools
        self._builtin_tools = builtin_tools
        # Filter state
        self._tool_choices = tool_choices or []
        self._disabled_tools = disabled_tools or []
        self._tool_evaluation_check_list = set()
        # Cached filtered result (private, only accessed via property)
        self._available_tools_cache: (
            list[Tool | SubAgentTool | OpenAIBuiltInTool] | None
        ) = None

    @classmethod
    async def build_manager(
        cls,
        tool_configs: list[ToolBuildConfig],
        config: ToolManagerConfig,
        tool_progress_reporter: ToolProgressReporter,
        event: ChatEvent,
        mcp_manager: MCPManager | None = None,
        a2a_manager: A2AManager | None = None,
        builtin_tool_manager: OpenAIBuiltInToolManager | None = None,
    ) -> "ToolManager":
        tool_choices = event.payload.tool_choices
        disabled_tools = event.payload.disabled_tools

        logger.info("Initializing tools ...")
        logger.info("Tool choices: %s", tool_choices)
        logger.info("Disabled tools: %s", disabled_tools)
        logger.info("Tools: %s", [tool.name for tool in tool_configs])

        sub_agents = []
        if a2a_manager:
            tool_configs, sub_agents = a2a_manager.get_all_sub_agents(
                tool_configs=tool_configs, event=event
            )

        mcp_tools = []
        if mcp_manager:
            # Get MCP tools (these are already properly instantiated)
            mcp_tools = mcp_manager.get_all_mcp_tools()

        builtin_tools = []
        if builtin_tool_manager:
            (
                tool_configs,
                builtin_tools,
            ) = await builtin_tool_manager.get_all_openai_builtin_tools(
                tool_configs=tool_configs
            )

        # Build internal tools from configurations
        internal_tools = [
            ToolFactory.build_tool_with_settings(
                t.name,
                t,
                t.configuration,
                event,
                tool_progress_reporter=tool_progress_reporter,
            )
            for t in tool_configs
        ]

        return ToolManager(
            config=config,
            tools=internal_tools,
            a2a_tools=sub_agents,
            mcp_tools=mcp_tools,
            builtin_tools=builtin_tools,
            tool_choices=tool_choices,
            disabled_tools=disabled_tools,
        )

    ### Helpers ###
    @property
    def _all_tools(self) -> list[Tool | SubAgentTool | OpenAIBuiltInTool]:
        return self._tools + self._a2a_tools + self._mcp_tools + self._builtin_tools

    @property
    def _available_tools(self) -> list[Tool | SubAgentTool | OpenAIBuiltInTool]:
        if self._available_tools_cache is None:
            self._available_tools_cache = _compute_available_tools(
                tools=self._all_tools,
                tool_choices=self._tool_choices,
                disabled_tools=self._disabled_tools,
            )
        return self._available_tools_cache

    def _invalidate_cache(self) -> None:
        self._available_tools_cache = None

    def get_exclusive_tools(self) -> list[str]:
        return [tool.name for tool in self._all_tools if tool.is_exclusive()]

    def get_tool_choices(self) -> list[str]:
        return self._tool_choices.copy()

    def get_tool_by_name(self, name: str) -> Tool | None:
        for tool in self._tools + self._a2a_tools + self._mcp_tools:
            if tool.name == name:
                return tool
        return None

    def get_builtin_tool_by_name(self, name: str) -> OpenAIBuiltInTool | None:
        for tool in self._builtin_tools:
            if tool.name == name:
                return tool
        return None

    @property
    def sub_agent_tools(self) -> list[SubAgentTool]:
        return self._a2a_tools.copy()

    ### Methods scoped to available tools only ###
    def get_tool_prompts(self) -> list[ToolPrompts]:
        return [tool.get_tool_prompts() for tool in self._available_tools]

    @overload
    def get_forced_tools(
        self, responses_api: Literal[False] = False
    ) -> list[ChatCompletionNamedToolChoiceParam]: ...

    @overload
    def get_forced_tools(
        self, responses_api: Literal[True]
    ) -> list[response_create_params.ToolChoice]: ...

    def get_forced_tools(
        self, responses_api: bool = False
    ) -> (
        list[ChatCompletionNamedToolChoiceParam]
        | list[response_create_params.ToolChoice]
    ):
        """
        Note that built-in tools cannot be forced at the moment (API Error)
        """
        return [
            _get_forced_tool_definition(t.name, responses_api=responses_api)  # type: ignore (checked inside function)
            for t in self._available_tools
            if isinstance(t, Tool) and t.name in self.get_tool_choices()
        ]

    @overload
    def get_tool_definitions(
        self,
        include_builtin_tools: Literal[False] = False,
    ) -> list[LanguageModelToolDescription]: ...

    @overload
    def get_tool_definitions(
        self,
        include_builtin_tools: Literal[True],
    ) -> list[LanguageModelToolDescription | ToolParam]: ...

    def get_tool_definitions(
        self,
        include_builtin_tools: bool = False,
    ) -> (
        list[LanguageModelToolDescription]
        | list[LanguageModelToolDescription | ToolParam]
    ):
        tool_definitions = []

        for tool in self._available_tools:
            if isinstance(tool, OpenAIBuiltInTool) and not include_builtin_tools:
                continue
            tool_definitions.append(tool.tool_description())

        return tool_definitions

    @overload
    def get_available_tools(
        self,
        include_builtin_tools: Literal[False] = False,
    ) -> list[Tool]: ...

    @overload
    def get_available_tools(
        self,
        include_builtin_tools: Literal[True],
    ) -> list[Tool | OpenAIBuiltInTool]: ...

    def get_available_tools(
        self,
        include_builtin_tools: bool = False,
    ) -> list[Tool] | list[Tool | OpenAIBuiltInTool]:
        if include_builtin_tools:
            return self._available_tools
        return [tool for tool in self._available_tools if isinstance(tool, Tool)]

    @deprecated("Use get_available_tools instead")
    def get_tools(self) -> list[Tool]:
        return self.get_available_tools()

    ### Other Methods ###
    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._tool_evaluation_check_list)

    def log_loaded_tools(self):
        logger.info(
            "Loaded tools: %s",
            [tool.name for tool in self._all_tools],
        )
        logger.info(
            "Available tools: %s", [tool.name for tool in self._available_tools]
        )

    def add_forced_tool(self, name: str) -> None:
        """Add a tool to the forced tool choices, invalidating the cache."""
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        if tool.name not in self._tool_choices:
            self._tool_choices.append(tool.name)
            self._invalidate_cache()

    def clear_forced_tools(self) -> None:
        """Clear all forced tool choices, invalidating the cache."""
        self._tool_choices = []
        self._invalidate_cache()

    ### Tool Execution ###
    def does_a_tool_take_control(self, tool_calls: list[LanguageModelFunction]) -> bool:
        for tool_call in tool_calls:
            tool_instance = self.get_tool_by_name(tool_call.name)
            if tool_instance and tool_instance.takes_control():
                return True
        return False

    async def execute_selected_tools(
        self,
        tool_calls: list[LanguageModelFunction],
    ) -> list[ToolCallResponse]:
        tool_calls = filter_duplicate_tool_calls(tool_calls=tool_calls)

        num_tool_calls = len(tool_calls)
        if num_tool_calls > self._config.max_tool_calls:
            logger.warning(
                (
                    "Number of tool calls %s exceeds the allowed maximum of %s."
                    "The tool calls will be reduced to the first %s."
                ),
                num_tool_calls,
                self._config.max_tool_calls,
                self._config.max_tool_calls,
            )
            tool_calls = tool_calls[: self._config.max_tool_calls]

        tool_call_responses = await execute_tools_parallelized(
            tools=self.get_available_tools(),
            tool_calls=tool_calls,
            log_exceptions_to_debug_info=self._config.log_exceptions_to_debug_info,
        )

        for tool_call_response in tool_call_responses:
            self._add_debug_info_to_tool_call_response(
                tool_call_response=tool_call_response
            )

        for tool_call_response in tool_call_responses:
            if tool_call_response.successful:
                tool = self.get_tool_by_name(tool_call_response.name)
                if tool:
                    self._tool_evaluation_check_list.update(
                        tool.evaluation_check_list()
                    )

        return tool_call_responses

    def _add_debug_info_to_tool_call_response(
        self, tool_call_response: ToolCallResponse
    ) -> None:
        tool_call_response.update_debug_info(
            "is_exclusive", (tool_call_response.name in self.get_exclusive_tools())
        )
        tool_call_response.update_debug_info(
            "is_forced", (tool_call_response.name in self.get_tool_choices())
        )


T = TypeVar("T", bound=HasSettingsProtocol)


def _compute_available_tools(
    tools: Sequence[T], tool_choices: list[str], disabled_tools: list[str]
) -> list[T]:
    available_tools = []

    for t in tools:
        if not t.is_enabled():
            continue
        if t.name in disabled_tools:
            continue
        # if tool choices are given, only include those tools
        if len(tool_choices) > 0 and t.name not in tool_choices:
            continue
        # is the tool exclusive and has been choosen by the user?
        if t.is_exclusive() and len(tool_choices) > 0 and t.name in tool_choices:
            available_tools = [t]  # override all other tools
            break
        # if the tool is exclusive but no tool choices are given, skip it
        if t.is_exclusive():
            continue

        available_tools.append(t)

    return available_tools


def _get_forced_tool_definition(
    tool_name: str, responses_api: bool
) -> ChatCompletionNamedToolChoiceParam | response_create_params.ToolChoice:
    if responses_api:
        return {
            "type": "function",
            "name": tool_name,
        }

    return {
        "type": "function",
        "function": {"name": tool_name},
    }
