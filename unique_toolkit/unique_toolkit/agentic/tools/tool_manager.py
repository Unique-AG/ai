import asyncio
from logging import Logger, getLogger
from typing import Generic, Literal, TypeVar, overload

from openai.types.chat import (
    ChatCompletionNamedToolChoiceParam,
)
from openai.types.responses import (
    ToolParam,
    response_create_params,
)
from pydantic import BaseModel, Field

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a import A2AManager, SubAgentTool
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
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


_ApiMode = TypeVar("_ApiMode", Literal["completions"], Literal["responses"])


class _ToolManager(Generic[_ApiMode]):
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
        api_mode: _ApiMode,
        builtin_tool_manager: OpenAIBuiltInToolManager | None = None,
    ) -> None:
        self._logger = logger
        self._config = config
        self._tool_progress_reporter = tool_progress_reporter
        self._tools: list[Tool | OpenAIBuiltInTool] = []
        self._tool_choices = event.payload.tool_choices
        self._disabled_tools = event.payload.disabled_tools
        self._exclusive_tools = [
            tool.name for tool in self._config.tools if tool.is_exclusive
        ]
        # this needs to be a set of strings to avoid duplicates
        self._tool_evaluation_check_list: set[EvaluationMetricName] = set()
        self._mcp_manager = mcp_manager
        self._a2a_manager = a2a_manager
        self._builtin_tool_manager = builtin_tool_manager
        self._api_mode = api_mode
        self._init__tools(event)

    def _init__tools(self, event: ChatEvent) -> None:
        tool_choices = self._tool_choices
        tool_configs = self._config.tools
        self._logger.info("Initializing tool definitions...")
        self._logger.info(f"Tool choices: {tool_choices}")

        tool_configs, sub_agents = self._a2a_manager.get_all_sub_agents(
            tool_configs, event
        )
        self._sub_agents = sub_agents

        registered_tool_names = set(t.name for t in self._sub_agents)

        self._builtin_tools = []
        if self._builtin_tool_manager and self._api_mode == "responses":
            self._builtin_tools = (
                self._builtin_tool_manager.get_all_openai_builtin_tools()
            )

        registered_tool_names.update(t.name for t in self._builtin_tools)

        # Get MCP tools (these are already properly instantiated)
        self._mcp_tools = self._mcp_manager.get_all_mcp_tools()

        registered_tool_names.update(t.name for t in self._mcp_tools)

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
            if t.name not in registered_tool_names  # Skip already handled tools
            and t.name not in OpenAIBuiltInToolName  # Safeguard
        ]

        # Combine all types of tools
        self.available_tools = (
            self._internal_tools
            + self._mcp_tools
            + self._sub_agents
            + self._builtin_tools
        )

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

    def filter_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
        tool_types: list[Literal["mcp", "internal", "subagent", "openai_builtin"]],
    ) -> list[LanguageModelFunction]:
        filtered_calls = []

        # Build sets for efficient lookup
        internal_tool_names = {tool.name for tool in self._internal_tools}
        mcp_tool_names = {tool.name for tool in self._mcp_tools}
        sub_agent_names = {tool.name for tool in self._sub_agents}
        builtin_tool_names = {tool.name for tool in self._builtin_tools}

        for tool_call in tool_calls:
            if "internal" in tool_types and tool_call.name in internal_tool_names:
                filtered_calls.append(tool_call)
            elif "mcp" in tool_types and tool_call.name in mcp_tool_names:
                filtered_calls.append(tool_call)
            elif "subagent" in tool_types and tool_call.name in sub_agent_names:
                filtered_calls.append(tool_call)
            elif (
                "openai_builtin" in tool_types and tool_call.name in builtin_tool_names
            ):
                filtered_calls.append(tool_call)

        return filtered_calls

    @property
    def sub_agents(self) -> list[SubAgentTool]:
        return self._sub_agents

    def log_loaded_tools(self):
        self._logger.info(f"Loaded tools: {[tool.name for tool in self._tools]}")

    def get_tool_choices(self) -> list[str]:
        return self._tool_choices.copy()

    def get_exclusive_tools(self) -> list[str]:
        return self._exclusive_tools.copy()

    def get_tool_prompts(self) -> list[ToolPrompts]:
        return [tool.get_tool_prompts() for tool in self._tools]

    def add_forced_tool(self, name):
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        if tool.name not in self._tool_choices:
            self._tool_choices.append(tool.name)

    def does_a_tool_take_control(self, tool_calls: list[LanguageModelFunction]) -> bool:
        for tool_call in tool_calls:
            tool_instance = self.get_tool_by_name(tool_call.name)
            if tool_instance and tool_instance.takes_control():
                return True
        return False

    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._tool_evaluation_check_list)

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

        assert isinstance(tool_instance, Tool)  # Should always be the case

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

    @overload
    def get_tool_by_name(
        self: "_ToolManager[Literal['completions']]", name: str
    ) -> Tool | None: ...

    @overload
    def get_tool_by_name(
        self: "_ToolManager[Literal['responses']]", name: str
    ) -> Tool | OpenAIBuiltInTool | None: ...

    @overload  # Unknown API mode typing
    def get_tool_by_name(
        self: "_ToolManager", name: str
    ) -> Tool | OpenAIBuiltInTool | None: ...

    def get_tool_by_name(self, name: str) -> Tool | OpenAIBuiltInTool | None:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    @overload
    def get_tools(self: "_ToolManager[Literal['completions']]") -> list[Tool]: ...

    @overload
    def get_tools(
        self: "_ToolManager[Literal['responses']]",
    ) -> list[Tool | OpenAIBuiltInTool]: ...

    def get_tools(self) -> list[Tool] | list[Tool | OpenAIBuiltInTool]:
        return self._tools.copy()

    @overload
    def get_forced_tools(
        self: "_ToolManager[Literal['completions']]",
    ) -> list[ChatCompletionNamedToolChoiceParam]: ...

    @overload
    def get_forced_tools(
        self: "_ToolManager[Literal['responses']]",
    ) -> list[response_create_params.ToolChoice]: ...

    def get_forced_tools(
        self,
    ) -> (
        list[ChatCompletionNamedToolChoiceParam]
        | list[response_create_params.ToolChoice]
    ):
        return [
            _convert_to_forced_tool(t.name, mode=self._api_mode)
            for t in self._tools
            if t.name in self._tool_choices
        ]  # type: ignore

    @overload
    def get_tool_definitions(
        self: "_ToolManager[Literal['completions']]",
    ) -> list[LanguageModelToolDescription]: ...

    @overload
    def get_tool_definitions(
        self: "_ToolManager[Literal['responses']]",
    ) -> list[LanguageModelToolDescription | ToolParam]: ...

    def get_tool_definitions(
        self,
    ) -> (
        list[LanguageModelToolDescription]
        | list[LanguageModelToolDescription | ToolParam]
    ):
        return [tool.tool_description() for tool in self._tools]


def _convert_to_forced_tool(
    tool_name: str, mode: Literal["completions", "responses"]
) -> ChatCompletionNamedToolChoiceParam | response_create_params.ToolChoice:
    if mode == "completions":
        return {
            "type": "function",
            "function": {"name": tool_name},
        }
    else:
        if tool_name in OpenAIBuiltInToolName:
            # Built-in have a special syntax for forcing
            return {"type": tool_name}  # type: ignore
        else:
            return {
                "name": tool_name,
                "type": "function",
            }


class ToolManager(_ToolManager[Literal["completions"]]):
    def __init__(
        self,
        logger: Logger,
        config: ToolManagerConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
    ) -> None:
        super().__init__(
            logger=logger,
            config=config,
            event=event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
            api_mode="completions",
            builtin_tool_manager=None,
        )


class ResponsesApiToolManager(_ToolManager[Literal["responses"]]):
    def __init__(
        self,
        logger: Logger,
        config: ToolManagerConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
        builtin_tool_manager: OpenAIBuiltInToolManager,
    ) -> None:
        super().__init__(
            logger=logger,
            config=config,
            event=event,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
            api_mode="responses",
            builtin_tool_manager=builtin_tool_manager,
        )
