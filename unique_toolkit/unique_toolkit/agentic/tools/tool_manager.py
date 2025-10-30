import asyncio
from abc import ABC, abstractmethod
from logging import Logger, getLogger
from typing import Literal, override

from openai.types.chat import (
    ChatCompletionNamedToolChoiceParam,
)
from openai.types.responses import ToolParam, response_create_params
from pydantic import BaseModel, Field

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
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.agentic.tools.utils.execution.execution import (
    Result,
    SafeTaskExecutor,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class ForcedToolOption:
    type: str = "function"

    def __init__(self, name: str):
        self.name = name


class ToolManagerConfig(BaseModel):
    tools: list[ToolBuildConfig] = Field(
        default=[],
        description="List of tools that the agent can use.",
    )

    max_tool_calls: int = Field(
        default=10,
        ge=1,
        description="Maximum number of tool calls that can be executed in one iteration.",
    )


class BaseToolManager(ABC):
    def __init__(self, config: ToolManagerConfig):
        self._config = config
        # this needs to be a set of strings to avoid duplicates
        self._tool_evaluation_check_list: set[EvaluationMetricName] = set()

    @abstractmethod
    def get_tool_by_name(self, name: str) -> Tool | None:
        raise NotImplementedError()

    @abstractmethod
    def get_tool_choices(self) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_exclusive_tools(self) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def filter_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
        tool_types: list[Literal["mcp", "internal", "subagent"]],
    ) -> list[LanguageModelFunction]:
        """
        Filter tool calls by their types.

        Args:
            tool_calls: List of tool calls to filter
            tool_types: List of tool types to include (e.g., ["mcp", "internal", "subagent"])

        Returns:
            Filtered list of tool calls matching the specified types
        """
        raise NotImplementedError()

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
        tool_calls = tool_calls

        tool_calls = self.filter_duplicate_tool_calls(
            tool_calls=tool_calls,
        )
        num_tool_calls = len(tool_calls)

        if num_tool_calls > self._config.max_tool_calls:
            self._logger.warning(
                (
                    "Number of tool calls %s exceeds the allowed maximum of %s."
                    "The tool calls will be reduced to the first %s."
                ),
                num_tool_calls,
                self._config.max_tool_calls,
                self._config.max_tool_calls,
            )
            tool_calls = tool_calls[: self._config.max_tool_calls]

        tool_call_responses = await self._execute_parallelized(tool_calls)
        return tool_call_responses

    async def _execute_parallelized(
        self,
        tool_calls: list[LanguageModelFunction],
    ) -> list[ToolCallResponse]:
        self._logger.info("Execute tool calls")

        task_executor = SafeTaskExecutor(
            logger=self._logger,
        )

        # Create tasks for each tool call
        tasks = [
            task_executor.execute_async(
                self.execute_tool_call,
                tool_call=tool_call,
            )
            for tool_call in tool_calls
        ]

        # Wait until all tasks are finished
        tool_call_results = await asyncio.gather(*tasks)
        tool_call_results_unpacked: list[ToolCallResponse] = []
        for i, result in enumerate(tool_call_results):
            unpacked_tool_call_result = self._create_tool_call_response(
                result, tool_calls[i]
            )
            if unpacked_tool_call_result.debug_info is None:
                unpacked_tool_call_result.debug_info = {}
            unpacked_tool_call_result.debug_info["is_exclusive"] = (
                tool_calls[i].name in self.get_exclusive_tools()
            )
            unpacked_tool_call_result.debug_info["is_forced"] = (
                tool_calls[i].name in self.get_tool_choices()
            )
            tool_call_results_unpacked.append(unpacked_tool_call_result)

        return tool_call_results_unpacked

    async def execute_tool_call(
        self, tool_call: LanguageModelFunction
    ) -> ToolCallResponse:
        self._logger.info(f"Processing tool call: {tool_call.name}")

        tool_instance = self.get_tool_by_name(
            tool_call.name
        )  # we need to copy this as it will have problematic interference on multi calls.

        if tool_instance:
            # Execute the tool
            tool_response: ToolCallResponse = await tool_instance.run(
                tool_call=tool_call
            )
            evaluation_checks = tool_instance.evaluation_check_list()
            self._tool_evaluation_check_list.update(evaluation_checks)

            return tool_response

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=tool_call.name,
            error_message=f"Tool of name {tool_call.name} not found",
        )

    def _create_tool_call_response(
        self, result: Result[ToolCallResponse], tool_call: LanguageModelFunction
    ) -> ToolCallResponse:
        if not result.success:
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=tool_call.name,
                error_message=str(result.exception),
            )
        unpacked = result.unpack()
        if not isinstance(unpacked, ToolCallResponse):
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=tool_call.name,
                error_message="Tool call response is not of type ToolCallResponse",
            )
        return unpacked

    def filter_duplicate_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
    ) -> list[LanguageModelFunction]:
        """
        Filter out duplicate tool calls based on name and arguments.
        """

        unique_tool_calls = []

        for call in tool_calls:
            if all(not call == other_call for other_call in unique_tool_calls):
                unique_tool_calls.append(call)

        if len(tool_calls) != len(unique_tool_calls):
            self._logger = getLogger(__name__)
            self._logger.warning(
                f"Filtered out {len(tool_calls) - len(unique_tool_calls)} duplicate tool calls."
            )
        return unique_tool_calls

    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._tool_evaluation_check_list)


class ToolManager(BaseToolManager):
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
        logger: Logger,
        config: ToolManagerConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
    ):
        super().__init__(config)
        self._logger = logger
        self._config = config
        self._tool_progress_reporter = tool_progress_reporter
        self._tools = []
        self._tool_choices = event.payload.tool_choices
        self._disabled_tools = event.payload.disabled_tools
        self._exclusive_tools = [
            tool.name for tool in self._config.tools if tool.is_exclusive
        ]
        # this needs to be a set of strings to avoid duplicates
        self._tool_evaluation_check_list: set[EvaluationMetricName] = set()
        self._mcp_manager = mcp_manager
        self._a2a_manager = a2a_manager
        self._init__tools(event)

    def _init__tools(self, event: ChatEvent) -> None:
        tool_choices = self._tool_choices
        tool_configs = self._config.tools
        self._logger.info("Initializing tool definitions...")
        self._logger.info(f"Tool choices: {tool_choices}")

        tool_configs, sub_agents = self._a2a_manager.get_all_sub_agents(
            tool_configs, event
        )

        # Build internal tools from configurations
        self._internal_tools = [
            ToolFactory.build_tool_with_settings(
                t.name,
                t,
                t.configuration,
                event,
                tool_progress_reporter=self._tool_progress_reporter,
            )
            for t in tool_configs
        ]

        # Get MCP tools (these are already properly instantiated)
        self._mcp_tools = self._mcp_manager.get_all_mcp_tools()
        # Combine both types of tools
        self.available_tools = self._internal_tools + self._mcp_tools + sub_agents
        self._sub_agents = sub_agents

        for t in self.available_tools:
            if not t.is_enabled():
                continue
            if t.name in self._disabled_tools:
                continue
            # if tool choices are given, only include those tools
            if len(self._tool_choices) > 0 and t.name not in self._tool_choices:
                continue
            # is the tool exclusive and has been choosen by the user?
            if t.is_exclusive() and len(tool_choices) > 0 and t.name in tool_choices:
                self._tools = [t]  # override all other tools
                break
            # if the tool is exclusive but no tool choices are given, skip it
            if t.is_exclusive():
                continue

            self._tools.append(t)

    @override
    def filter_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
        tool_types: list[Literal["mcp", "internal", "subagent"]],
    ) -> list[LanguageModelFunction]:
        filtered_calls = []

        # Build sets for efficient lookup
        internal_tool_names = {tool.name for tool in self._internal_tools}
        mcp_tool_names = {tool.name for tool in self._mcp_tools}
        sub_agent_names = {tool.name for tool in self._sub_agents}

        for tool_call in tool_calls:
            if "internal" in tool_types and tool_call.name in internal_tool_names:
                filtered_calls.append(tool_call)
            elif "mcp" in tool_types and tool_call.name in mcp_tool_names:
                filtered_calls.append(tool_call)
            elif "subagent" in tool_types and tool_call.name in sub_agent_names:
                filtered_calls.append(tool_call)

        return filtered_calls

    @property
    def sub_agents(self) -> list[SubAgentTool]:
        return self._sub_agents

    @property
    def internal_tools(self) -> list[Tool]:
        return self._internal_tools

    @property
    def mcp_tools(self) -> list[Tool]:
        return self._mcp_tools

    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._tool_evaluation_check_list)

    def log_loaded_tools(self):
        self._logger.info(f"Loaded tools: {[tool.name for tool in self._tools]}")

    @override
    def get_tool_by_name(self, name: str) -> Tool | None:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    @override
    def get_tool_choices(self) -> list[str]:
        return self._tool_choices

    @override
    def get_exclusive_tools(self) -> list[str]:
        return self._exclusive_tools

    def get_tools(self) -> list[Tool]:
        return self._tools  # type: ignore

    def get_forced_tools(
        self,
    ) -> list[ChatCompletionNamedToolChoiceParam]:
        return [
            self._convert_to_forced_tool(t.name)
            for t in self._tools
            if t.name in self._tool_choices
        ]

    def get_tool_definitions(
        self,
    ) -> list[LanguageModelToolDescription]:
        return [tool.tool_description() for tool in self._tools]

    def get_tool_prompts(self) -> list[ToolPrompts]:
        return [tool.get_tool_prompts() for tool in self._tools]

    def add_forced_tool(self, name):
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        if tool.name not in self._tool_choices:
            self._tool_choices.append(tool.name)

    def _convert_to_forced_tool(
        self, tool_name: str
    ) -> ChatCompletionNamedToolChoiceParam:
        return {
            "type": "function",
            "function": {"name": tool_name},
        }

    def tool_choices(self) -> list[str]:
        return self._tool_choices.copy()


class ResponsesApiToolManager(BaseToolManager):
    def __init__(
        self,
        logger: Logger,
        config: ToolManagerConfig,
        tool_manager: ToolManager,
        builtin_tools: list[OpenAIBuiltInTool],
    ) -> None:
        super().__init__(config)
        self._logger = logger
        self._config = config
        self._tool_manager = tool_manager
        self._builtin_tools = builtin_tools
        self._tools = self._tool_manager.get_tools()

    @classmethod
    async def build_manager(
        cls,
        logger: Logger,
        config: ToolManagerConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
        builtin_tool_manager: OpenAIBuiltInToolManager,
    ) -> "ResponsesApiToolManager":
        (
            tool_configs,
            builtin_tools,
        ) = await builtin_tool_manager.get_all_openai_builtin_tools(config.tools)

        completions_tool_manager_config = ToolManagerConfig(
            tools=tool_configs, max_tool_calls=config.max_tool_calls
        )
        completions_tool_manager = ToolManager(
            logger=logger,
            config=completions_tool_manager_config,
            event=event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
        )

        return cls(
            logger=logger,
            config=config,
            tool_manager=completions_tool_manager,
            builtin_tools=builtin_tools,
        )

    @override
    def filter_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
        tool_types: list[Literal["mcp", "internal", "subagent"]],
    ) -> list[LanguageModelFunction]:
        """Delegate filtering to the underlying tool manager."""
        return self._tool_manager.filter_tool_calls(tool_calls, tool_types)

    @override
    def get_tool_by_name(self, name: str) -> Tool | None:
        return self._tool_manager.get_tool_by_name(name)

    @override
    def get_tool_choices(self) -> list[str]:
        return self._tool_manager._tool_choices

    @override
    def get_exclusive_tools(self) -> list[str]:
        return self._tool_manager._exclusive_tools

    @property
    def sub_agents(self) -> list[SubAgentTool]:
        return self._tool_manager.sub_agents

    def log_loaded_tools(self):
        self._logger.info(
            f"Loaded tools: {[tool.name for tool in self._tools + self._builtin_tools]}"
        )

    def get_tools(self) -> list[Tool]:
        return self._tool_manager.get_tools()

    def get_forced_tools(
        self,
    ) -> list[response_create_params.ToolChoice]:
        """
        Note that built-in tools cannot be forced at the moment
        """
        return [
            {
                "name": t.name,
                "type": "function",
            }
            for t in self._tools
            if t.name in self._tool_manager.tool_choices()
        ]

    def get_tool_definitions(
        self,
    ) -> list[LanguageModelToolDescription | ToolParam]:
        if len(self._tool_manager.tool_choices()) > 0:
            # We cannot send a builtin tool in this case (api error)
            return [tool.tool_description() for tool in self._tools]
        else:
            return [
                tool.tool_description() for tool in self._tools + self._builtin_tools
            ]

    def get_tool_prompts(self) -> list[ToolPrompts]:
        return [tool.get_tool_prompts() for tool in self._tools + self._builtin_tools]

    def add_forced_tool(self, name: str) -> None:
        self._tool_manager.add_forced_tool(name)
