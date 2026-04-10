from __future__ import annotations

import asyncio
import time
from logging import Logger, getLogger
from typing import Generic, Iterable, Literal, TypeVar, cast, overload

from openai.types.chat import (
    ChatCompletionNamedToolChoiceParam,
)
from openai.types.responses import (
    ResponseIncludable,
    ToolParam,
    response_create_params,
)
from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit._common.execution import (
    Result,
    SafeTaskExecutor,
)
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


class ToolManagerState(BaseModel):
    """Snapshot of tool-manager runtime data.

    Transitions are **functional**: methods like :meth:`with_added_tool` return a new
    instance; :class:`_ToolManager` applies them via :meth:`_ToolManager._replace_state`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool_choices: list[str] = Field(
        default_factory=list,
        description="User/session tool choice names; may grow via add_forced_tool.",
    )
    disabled_tools: list[str] = Field(
        default_factory=list,
        description="Tool names disabled for this event.",
    )
    exclusive_tools: list[str] = Field(
        default_factory=list,
        description="Names of tools configured as exclusive (from ToolBuildConfig).",
    )
    tool_evaluation_check_list: set[EvaluationMetricName] = Field(
        default_factory=set,
        description="Accumulated evaluation metrics from executed tools.",
    )

    tools: list[Tool | OpenAIBuiltInTool] = Field(
        default_factory=list,
        description="Active tools offered to the model after filtering.",
    )
    internal_tools: list[Tool] = Field(
        default_factory=list,
        description="Tools built from ToolFactory for this session.",
    )
    mcp_tools: list[Tool] = Field(
        default_factory=list,
        description="MCP-backed tools from MCPManager.",
    )
    sub_agents: list[SubAgentTool] = Field(
        default_factory=list,
        description="Sub-agent tools from A2AManager.",
    )
    builtin_tools: list[OpenAIBuiltInTool] = Field(
        default_factory=list,
        description="OpenAI built-in tools (Responses API only).",
    )
    available_tools: list[Tool | OpenAIBuiltInTool] = Field(
        default_factory=list,
        description="Union of internal, MCP, sub-agent, and built-in tools before choice filtering.",
    )

    def with_added_tool(self, tool: Tool) -> ToolManagerState:
        """Return a new state with ``tool`` appended to internal, available, and active lists."""
        return self.model_copy(
            update={
                "internal_tools": [*self.internal_tools, tool],
                "available_tools": [*self.available_tools, tool],
                "tools": [*self.tools, tool],
            }
        )

    def without_tool_named(self, name: str) -> tuple[ToolManagerState, bool]:
        """Return a new state with ``name`` removed from all tool lists; ``found`` if anything changed."""
        filtered_tools = [t for t in self.tools if t.name != name]
        filtered_internal = [t for t in self.internal_tools if t.name != name]
        filtered_mcp = [t for t in self.mcp_tools if t.name != name]
        filtered_sub = [t for t in self.sub_agents if t.name != name]
        filtered_builtin = [t for t in self.builtin_tools if t.name != name]
        filtered_available = [t for t in self.available_tools if t.name != name]
        found = (
            len(filtered_tools) != len(self.tools)
            or len(filtered_internal) != len(self.internal_tools)
            or len(filtered_mcp) != len(self.mcp_tools)
            or len(filtered_sub) != len(self.sub_agents)
            or len(filtered_builtin) != len(self.builtin_tools)
            or len(filtered_available) != len(self.available_tools)
        )
        return (
            self.model_copy(
                update={
                    "tools": filtered_tools,
                    "internal_tools": filtered_internal,
                    "mcp_tools": filtered_mcp,
                    "sub_agents": filtered_sub,
                    "builtin_tools": filtered_builtin,
                    "available_tools": filtered_available,
                }
            ),
            found,
        )

    def with_tool_choice(self, name: str) -> ToolManagerState:
        """Return a new state with ``name`` appended to ``tool_choices`` if missing."""
        if name in self.tool_choices:
            return self
        return self.model_copy(update={"tool_choices": [*self.tool_choices, name]})

    def with_evaluation_checks(
        self, checks: Iterable[EvaluationMetricName]
    ) -> ToolManagerState:
        """Return a new state merging evaluation metrics into ``tool_evaluation_check_list``."""
        merged = set(self.tool_evaluation_check_list) | set(checks)
        return self.model_copy(update={"tool_evaluation_check_list": merged})


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
        self._mcp_manager = mcp_manager
        self._a2a_manager = a2a_manager
        self._builtin_tool_manager = builtin_tool_manager
        self._api_mode = api_mode
        self._state = ToolManagerState(
            tool_choices=list(event.payload.tool_choices),
            disabled_tools=list(event.payload.disabled_tools),
            exclusive_tools=[
                tool.name for tool in self._config.tools if tool.is_exclusive
            ],
        )
        self._init__tools(event)

    def _replace_state(self, new_state: ToolManagerState) -> None:
        self._state = new_state

    def _build_initialized_state(self, event: ChatEvent) -> ToolManagerState:
        """Assemble tool lists and active set; does not mutate ``self._state``."""
        base = self._state
        self._logger.info("Initializing tool definitions...")
        self._logger.info(f"Tool choices: {base.tool_choices}")

        tool_configs, sub_agents = self._a2a_manager.get_all_sub_agents(
            self._config.tools, event
        )

        registered_tool_names = {t.name for t in sub_agents}

        builtin_tools: list[OpenAIBuiltInTool] = []
        if self._builtin_tool_manager is not None and self._api_mode == "responses":
            builtin_tools = self._builtin_tool_manager.get_all_openai_builtin_tools()

        registered_tool_names.update(t.name for t in builtin_tools)

        mcp_tools = self._mcp_manager.get_all_mcp_tools()
        registered_tool_names.update(t.name for t in mcp_tools)

        internal_tools = [
            ToolFactory.build_tool_with_settings(
                t.name,
                t,
                t.configuration,
                event,
                tool_progress_reporter=self._tool_progress_reporter,
            )
            for t in tool_configs
            if t.name not in registered_tool_names
            and t.name not in OpenAIBuiltInToolName
        ]

        available_tools = cast(
            list[Tool | OpenAIBuiltInTool],
            [*internal_tools, *mcp_tools, *sub_agents, *builtin_tools],
        )

        active: list[Tool | OpenAIBuiltInTool] = []
        for t in available_tools:
            if not t.is_enabled():
                continue
            if t.name in base.disabled_tools:
                continue
            if len(base.tool_choices) > 0 and t.name not in base.tool_choices:
                if t.name == OpenAIBuiltInToolName.CODE_INTERPRETER:
                    active.append(t)
                continue
            if (
                t.is_exclusive()
                and len(base.tool_choices) > 0
                and t.name in base.tool_choices
            ):
                return ToolManagerState(
                    tool_choices=base.tool_choices,
                    disabled_tools=base.disabled_tools,
                    exclusive_tools=base.exclusive_tools,
                    tool_evaluation_check_list=base.tool_evaluation_check_list,
                    sub_agents=sub_agents,
                    builtin_tools=builtin_tools,
                    mcp_tools=mcp_tools,
                    internal_tools=internal_tools,
                    available_tools=available_tools,
                    tools=[t],
                )
            if t.is_exclusive():
                continue

            active.append(t)

        return ToolManagerState(
            tool_choices=base.tool_choices,
            disabled_tools=base.disabled_tools,
            exclusive_tools=base.exclusive_tools,
            tool_evaluation_check_list=base.tool_evaluation_check_list,
            sub_agents=sub_agents,
            builtin_tools=builtin_tools,
            mcp_tools=mcp_tools,
            internal_tools=internal_tools,
            available_tools=available_tools,
            tools=active,
        )

    def _init__tools(self, event: ChatEvent) -> None:
        self._replace_state(self._build_initialized_state(event))

    def filter_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
        tool_types: list[Literal["mcp", "internal", "subagent", "openai_builtin"]],
    ) -> list[LanguageModelFunction]:
        filtered_calls = []

        # Build sets for efficient lookup
        internal_tool_names = {tool.name for tool in self._state.internal_tools}
        mcp_tool_names = {tool.name for tool in self._state.mcp_tools}
        sub_agent_names = {tool.name for tool in self._state.sub_agents}
        builtin_tool_names = {tool.name for tool in self._state.builtin_tools}

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
    def state(self) -> ToolManagerState:
        return self._state

    @property
    def available_tools(self) -> list[Tool | OpenAIBuiltInTool]:
        return self._state.available_tools

    @available_tools.setter
    def available_tools(self, value: list[Tool | OpenAIBuiltInTool]) -> None:
        self._replace_state(self._state.model_copy(update={"available_tools": value}))

    @property
    def sub_agents(self) -> list[SubAgentTool]:
        return self._state.sub_agents

    def log_loaded_tools(self):
        self._logger.info(f"Loaded tools: {[tool.name for tool in self._state.tools]}")

    def get_tool_choices(self) -> list[str]:
        return self._state.tool_choices.copy()

    def get_exclusive_tools(self) -> list[str]:
        return self._state.exclusive_tools.copy()

    def get_tool_prompts(self) -> list[ToolPrompts]:
        return [tool.get_tool_prompts() for tool in self._state.tools]

    def add_tool(self, tool: Tool) -> None:
        """Inject an externally constructed tool into the manager.

        Use this for tools that require custom constructor arguments (e.g. a
        shared registry) that cannot be built through ToolFactory.
        """
        self._replace_state(self._state.with_added_tool(tool))

    def exclude_tool(self, name: str) -> bool:
        """Exclude a tool by name from the active tool set.

        The tool is removed from all internal tracking lists so it will no
        longer be offered to the model or executed.  Returns True if the tool
        was present in at least one list.
        """
        new_state, found = self._state.without_tool_named(name)
        self._replace_state(new_state)
        return found

    def add_forced_tool(self, name):
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        self._replace_state(self._state.with_tool_choice(tool.name))

    def does_a_tool_take_control(self, tool_calls: list[LanguageModelFunction]) -> bool:
        for tool_call in tool_calls:
            tool_instance = self.get_tool_by_name(tool_call.name)
            if tool_instance and tool_instance.takes_control():
                return True
        return False

    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._state.tool_evaluation_check_list)

    async def execute_selected_tools(
        self,
        tool_calls: list[LanguageModelFunction],
    ) -> list[ToolCallResponse]:
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

        if not isinstance(tool_instance, Tool):
            raise ValueError(f"Tool {tool_call.name} cannot be run")

        if tool_instance:
            tool_start = time.perf_counter()
            tool_response: ToolCallResponse = await tool_instance.run(
                tool_call=tool_call
            )
            tool_execution_time = round(time.perf_counter() - tool_start, 3)

            if tool_response.debug_info is None:
                tool_response.debug_info = {}
            tool_response.debug_info["execution_time_s"] = tool_execution_time

            evaluation_checks = tool_instance.evaluation_check_list()
            self._replace_state(self._state.with_evaluation_checks(evaluation_checks))

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

    def filter_tool_calls_by_max_tool_calls_allowed(
        self, tool_calls: list[LanguageModelFunction]
    ) -> list[LanguageModelFunction]:
        if len(tool_calls) > self._config.max_tool_calls:
            self._logger.warning(
                (
                    "Number of tool calls %s exceeds the allowed maximum of %s."
                    "The tool calls will be reduced to the first %s."
                ),
                len(tool_calls),
                self._config.max_tool_calls,
                self._config.max_tool_calls,
            )
            return tool_calls[: self._config.max_tool_calls]
        return tool_calls

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
        for tool in self._state.tools:
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
        return self._state.tools.copy()

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
            for t in self._state.tools
            if t.name in self._state.tool_choices
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
        return [tool.tool_description() for tool in self._state.tools]


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
        self._builtin_tool_manager = builtin_tool_manager
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

    def get_required_include_params(self) -> list[ResponseIncludable]:
        """Return Responses API include params required by all active built-in tools."""
        return self._builtin_tool_manager.get_required_include_params()
