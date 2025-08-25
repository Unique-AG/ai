import asyncio
from logging import Logger, getLogger
from typing import Any

from pydantic import BaseModel, Field

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelTool,
    LanguageModelToolDescription,
)
from unique_toolkit.tools.config import ToolBuildConfig
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import ToolCallResponse, ToolPrompts
from unique_toolkit.tools.tool import Tool
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.tools.utils.execution.execution import Result, SafeTaskExecutor
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.tools.mcp.manager import MCPManager

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
        logger: Logger,
        config: ToolManagerConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
    ):
        self._logger = logger
        self._config = config
        self._tool_progress_reporter = tool_progress_reporter
        self._tools = []
        self._tool_choices = event.payload.tool_choices
        self._disabled_tools = event.payload.disabled_tools
        # this needs to be a set of strings to avoid duplicates
        self._tool_evaluation_check_list: set[EvaluationMetricName] = set()
        self._mcp_manager = mcp_manager
        self._init__tools(event)


    def _init__tools(self, event: ChatEvent) -> None:
        tool_choices = self._tool_choices
        tool_configs = self._config.tools
        self._logger.info("Initializing tool definitions...")
        self._logger.info(f"Tool choices: {tool_choices}")
        self._logger.info(f"Tool configs: {tool_configs}")
        mcp_tools = self._mcp_manager.get_all_mcp_tools(tool_choices)

        tool_configs.extend([t.settings.configuration for t in mcp_tools])
        
        self.available_tools = [
            ToolFactory.build_tool_with_settings(
                t.name,
                t,
                t.configuration,
                event,
                tool_progress_reporter=self._tool_progress_reporter,
            )
            for t in tool_configs
        ]

        for t in self.available_tools:
            if t.is_exclusive():
                self._tools = [t]
                return
            if not t.is_enabled():
                continue
            if t.name in self._disabled_tools:
                continue
            if len(tool_choices) > 0 and t.name not in tool_choices:
                continue

            self._tools.append(t)

    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._tool_evaluation_check_list)

    def log_loaded_tools(self):
        self._logger.info(f"Loaded tools: {[tool.name for tool in self._tools]}")

    def get_tools(self) -> list[Tool]:
        return self._tools

    def get_tool_by_name(self, name: str) -> Tool | None:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    def get_forced_tools(self) -> list[dict[str, Any]]:
        return [
            self._convert_to_forced_tool(t.name)
            for t in self._tools
            if t.name in self._tool_choices
        ]

    def add_forced_tool(self, name):
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")
        self._tools.append(tool)
        self._tool_choices.append(tool.name)

    def get_tool_definitions(
        self,
    ) -> list[LanguageModelTool | LanguageModelToolDescription]:
        return [tool.tool_description() for tool in self._tools]

    def get_tool_prompts(self) -> list[ToolPrompts]:
        return [tool.get_tool_prompts() for tool in self._tools]

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

    from typing import Any

    def _convert_to_forced_tool(self, tool_name: str) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": tool_name},
        }
