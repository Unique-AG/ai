import asyncio
import time
from logging import Logger, getLogger
from typing import Any, Generic, Literal, TypeVar, overload

from openai.types.chat import (
    ChatCompletionNamedToolChoiceParam,
)
from openai.types.responses import (
    ResponseIncludable,
    ToolParam,
    response_create_params,
)
from pydantic import BaseModel, Field
from typing_extensions import Self

from unique_toolkit._common.execution import (
    Result,
    SafeTaskExecutor,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a import A2AManager, SubAgentTool
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.mcp.manager import MCPManager
from unique_toolkit.agentic.tools.names import (
    INTERNAL_SEARCH_TOOL_NAME,
    UPLOADED_SEARCH_TOOL_NAME,
)
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.manager import OpenAIBuiltInToolManager
from unique_toolkit.agentic.tools.run_context import ToolRunContext
from unique_toolkit.agentic.tools.schemas import ToolCallResponse, ToolPrompts
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelService
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
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
    ) -> None:
        self._setup(
            logger=logger,
            config=config,
            run_context=ToolRunContext.from_chat_event(event),
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
            api_mode=api_mode,
            builtin_tool_manager=builtin_tool_manager,
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
        )

    @classmethod
    def from_run_context(
        cls,
        logger: Logger,
        config: ToolManagerConfig,
        *,
        run_context: ToolRunContext,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
        api_mode: _ApiMode,
        builtin_tool_manager: OpenAIBuiltInToolManager | None = None,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
    ) -> Self:
        instance = cls.__new__(cls)
        instance._setup(
            logger=logger,
            config=config,
            run_context=run_context,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
            api_mode=api_mode,
            builtin_tool_manager=builtin_tool_manager,
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
        )
        return instance

    def _setup(
        self,
        *,
        logger: Logger,
        config: ToolManagerConfig,
        run_context: ToolRunContext,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
        api_mode: _ApiMode,
        builtin_tool_manager: OpenAIBuiltInToolManager | None,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
    ) -> None:
        self._logger = logger
        self._config = config
        self._tool_progress_reporter = tool_progress_reporter
        self._chat_service = chat_service
        self._language_model_service = language_model_service
        self._content_service = content_service
        self._tools: list[Tool[Any] | OpenAIBuiltInTool[Any]] = []
        self._tool_choices = run_context.tool_choices
        self._disabled_tools = run_context.disabled_tools
        self._exclusive_tools = [
            tool.name
            for tool in self._config.tools
            if tool.is_exclusive and tool.is_enabled
        ]
        # this needs to be a set of strings to avoid duplicates
        self._tool_evaluation_check_list: set[EvaluationMetricName] = set()
        self._mcp_manager = mcp_manager
        self._a2a_manager = a2a_manager
        self._builtin_tool_manager = builtin_tool_manager
        self._api_mode = api_mode
        self._sub_agents: list[SubAgentTool] = []
        self._builtin_tools: list[OpenAIBuiltInTool[Any]] = []
        self._mcp_tools: list[Tool[Any]] = []
        self._internal_tools: list[Tool[Any]] = []
        self.available_tools: list[
            Tool[Any] | OpenAIBuiltInTool[Any] | SubAgentTool
        ] = []
        self._init__tools(run_context.tool_init_event)

    def _inject_shared_services(
        self, tool: Tool[Any], tool_init_event: ChatEvent | None = None
    ) -> None:
        if self._chat_service is None or self._language_model_service is None:
            return
        if not hasattr(tool, "_chat_service"):
            return
        from unique_toolkit.agentic.message_log_manager.service import (
            MessageStepLogger,
        )

        tool._chat_service = self._chat_service
        tool._language_model_service = self._language_model_service
        tool._message_step_logger = MessageStepLogger(
            chat_service=self._chat_service,
        )
        if tool_init_event is not None:
            tool._event = tool_init_event
        if self._content_service is not None:
            tool._content_service = self._content_service
        tool._on_services_injected()

    def _init__tools(self, tool_init_event: ChatEvent | None) -> None:
        tool_choices = self._tool_choices
        tool_configs = self._config.tools
        self._logger.info("Initializing tool definitions...")
        self._logger.info(f"Tool choices: {tool_choices}")

        if self._chat_service is not None and self._language_model_service is not None:
            tool_configs, sub_agents = self._a2a_manager.get_all_sub_agents(
                tool_configs,
                chat_service=self._chat_service,
                language_model_service=self._language_model_service,
            )
        elif tool_init_event is not None:
            tool_configs, sub_agents = self._a2a_manager.get_all_sub_agents(
                tool_configs,
                tool_init_event,
            )
        else:
            tool_configs = [
                tool_config
                for tool_config in tool_configs
                if not tool_config.is_sub_agent
            ]
            sub_agents = []
        self._sub_agents = sub_agents

        registered_tool_names = set(t.name for t in self._sub_agents)

        self._builtin_tools = []
        if self._builtin_tool_manager is not None and self._api_mode == "responses":
            self._builtin_tools = (
                self._builtin_tool_manager.get_all_openai_builtin_tools()
            )

        registered_tool_names.update(t.name for t in self._builtin_tools)

        # Get MCP tools (these are already properly instantiated)
        self._mcp_tools = self._mcp_manager.get_all_mcp_tools()

        registered_tool_names.update(t.name for t in self._mcp_tools)

        # Build internal tools from configurations, skipping disabled and failing tools
        self._internal_tools.clear()
        safe_executor = SafeTaskExecutor(logger=self._logger, log_exceptions=False)
        for t in tool_configs:
            if t.name in registered_tool_names:
                continue
            if t.name in OpenAIBuiltInToolName:
                continue
            if not t.is_enabled:
                self._logger.info("Skipping disabled tool '%s'", t.name)
                continue
            if tool_init_event is None:
                self._logger.info(
                    "Skipping internal tool '%s' (requires chat event for initialization)",
                    t.name,
                )
                continue
            if (
                self._chat_service is not None
                and self._language_model_service is not None
            ):
                result = safe_executor.execute(
                    ToolFactory.build_tool_with_settings,
                    t.name,
                    t,
                    t.configuration,
                    tool_progress_reporter=self._tool_progress_reporter,
                    chat_service=self._chat_service,
                    language_model_service=self._language_model_service,
                )
            else:
                result = safe_executor.execute(
                    ToolFactory.build_tool_with_settings,
                    t.name,
                    t,
                    t.configuration,
                    tool_init_event,
                    tool_progress_reporter=self._tool_progress_reporter,
                )
            if result.success:
                tool = result.unpack()
                self._inject_shared_services(tool, tool_init_event)
                self._internal_tools.append(tool)
            else:
                self._logger.warning(
                    "Skipping tool '%s' due to initialization failure.",
                    t.name,
                    exc_info=result.exception,
                )

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
                self._restore_uploaded_search_for_internal_search_if_available(
                    exclusive_tool=t
                )
                break
            # if the tool is exclusive but no tool choices are given, skip it
            if t.is_exclusive():
                continue

            self._tools.append(t)

        # Capability tools bypass tool_choices filtering — they are always
        # included when enabled, regardless of what was force-selected.
        active_names = {t.name for t in self._tools}
        for t in self.available_tools:
            if (
                t.is_enabled()
                and t.name not in self._disabled_tools
                and t.is_capability()
                and t.name not in active_names
            ):
                self._tools.append(t)

    def _restore_uploaded_search_for_internal_search_if_available(
        self,
        exclusive_tool: Tool[Any] | OpenAIBuiltInTool[Any],
    ) -> None:
        """Keep UploadedSearch available when InternalSearch wins exclusivity."""
        if exclusive_tool.name != INTERNAL_SEARCH_TOOL_NAME:
            return

        uploaded_search_tool = next(
            (
                tool
                for tool in self.available_tools
                if tool.name == UPLOADED_SEARCH_TOOL_NAME
            ),
            None,
        )
        if uploaded_search_tool is None:
            return

        self._tools.append(uploaded_search_tool)

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

    def add_tool(self, tool: Tool[Any]) -> None:
        """Inject an externally constructed tool into the manager.

        Use this for tools that require custom constructor arguments (e.g. a
        shared registry) that cannot be built through ToolFactory.
        """
        self._internal_tools.append(tool)
        self.available_tools.append(tool)
        self._tools.append(tool)

    def exclude_tool(self, name: str) -> bool:
        """Exclude a tool by name from the active tool set.

        The tool is removed from all internal tracking lists so it will no
        longer be offered to the model or executed.  Returns True if the tool
        was present in at least one list.
        """
        found = False

        filtered_tools = [tool for tool in self._tools if tool.name != name]
        found = found or len(filtered_tools) != len(self._tools)
        self._tools = filtered_tools

        filtered_internal_tools = [
            tool for tool in self._internal_tools if tool.name != name
        ]
        found = found or len(filtered_internal_tools) != len(self._internal_tools)
        self._internal_tools = filtered_internal_tools

        filtered_mcp_tools = [tool for tool in self._mcp_tools if tool.name != name]
        found = found or len(filtered_mcp_tools) != len(self._mcp_tools)
        self._mcp_tools = filtered_mcp_tools

        filtered_sub_agents = [tool for tool in self._sub_agents if tool.name != name]
        found = found or len(filtered_sub_agents) != len(self._sub_agents)
        self._sub_agents = filtered_sub_agents

        filtered_builtin_tools = [
            tool for tool in self._builtin_tools if tool.name != name
        ]
        found = found or len(filtered_builtin_tools) != len(self._builtin_tools)
        self._builtin_tools = filtered_builtin_tools

        filtered_available_tools = [
            tool for tool in self.available_tools if tool.name != name
        ]
        found = found or len(filtered_available_tools) != len(self.available_tools)
        self.available_tools = filtered_available_tools

        return found

    def add_forced_tool(self, name):
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")

        if tool.name not in self._tool_choices:
            self._tool_choices.append(tool.name)

    def _get_tool_calls_that_take_control(
        self, tool_calls: list[LanguageModelFunction]
    ) -> list[LanguageModelFunction]:
        tools = []
        for tool_call in tool_calls:
            tool_instance = self.get_tool_by_name(tool_call.name)
            if tool_instance and tool_instance.takes_control():
                tools.append(tool_call)

        return tools

    def does_a_tool_take_control(self, tool_calls: list[LanguageModelFunction]) -> bool:
        return len(self._get_tool_calls_that_take_control(tool_calls)) > 0

    def get_evaluation_check_list(self) -> list[EvaluationMetricName]:
        return list(self._tool_evaluation_check_list)

    def _take_control_conflict_response(
        self,
        tool_call: LanguageModelFunction,
        take_control_names: list[str],
    ) -> ToolCallResponse:
        if tool_call.name in take_control_names:
            content = (
                f"ERROR: Tool `{tool_call.name}` directly returns its response to the user and therefore must be called on its own. "
                "None of the tools in this batch were executed. "
                f"You may recover by first calling the other tools, then calling `{tool_call.name}` alone."
            )
        else:
            names = ", ".join(f"`{n}`" for n in take_control_names)
            content = f"ERROR: Not executed because the following tool(s) must be called on their own: {names}"

        return ToolCallResponse(
            id=tool_call.id,
            name=tool_call.name,
            content=content,
        )

    async def execute_selected_tools(
        self,
        tool_calls: list[LanguageModelFunction],
    ) -> list[ToolCallResponse]:
        if len(tool_calls) > 1:
            take_control_tools = [
                t.name for t in self._get_tool_calls_that_take_control(tool_calls)
            ]

            if len(take_control_tools) > 0:
                self._logger.warning(
                    "Tool(s) %s take control and cannot be called alongside other tools. "
                    "Returning error for all %d tool calls.",
                    take_control_tools,
                    len(tool_calls),
                )
                return [
                    self._take_control_conflict_response(tool_call, take_control_tools)
                    for tool_call in tool_calls
                ]

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
        return result.unpack()

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
    ) -> Tool[Any] | None: ...

    @overload
    def get_tool_by_name(
        self: "_ToolManager[Literal['responses']]", name: str
    ) -> Tool[Any] | OpenAIBuiltInTool[Any] | None: ...

    @overload  # Unknown API mode typing
    def get_tool_by_name(
        self: "_ToolManager[Any]", name: str
    ) -> Tool[Any] | OpenAIBuiltInTool[Any] | None: ...

    def get_tool_by_name(self, name: str) -> Tool[Any] | OpenAIBuiltInTool[Any] | None:
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None

    @overload
    def get_tools(self: "_ToolManager[Literal['completions']]") -> list[Tool[Any]]: ...

    @overload
    def get_tools(
        self: "_ToolManager[Literal['responses']]",
    ) -> list[Tool[Any] | OpenAIBuiltInTool[Any]]: ...

    def get_tools(self) -> list[Tool[Any]] | list[Tool[Any] | OpenAIBuiltInTool[Any]]:
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
        # TODO(UN-19531): split into two branches with literal mode strings to eliminate this ignore
        return [  # pyright: ignore[reportReturnType]
            _convert_to_forced_tool(t.name, mode=self._api_mode)
            for t in self._tools
            if t.name in self._tool_choices
        ]

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
            return {"type": tool_name}  # pyright: ignore[reportReturnType]  # TODO(UN-19531)
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
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
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
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
        )

    @classmethod
    def from_run_context(
        cls,
        logger: Logger,
        config: ToolManagerConfig,
        *,
        run_context: ToolRunContext,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
        api_mode: Literal["completions"] = "completions",
        builtin_tool_manager: OpenAIBuiltInToolManager | None = None,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
    ) -> Self:
        return super().from_run_context(
            logger=logger,
            config=config,
            run_context=run_context,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
            api_mode=api_mode,
            builtin_tool_manager=builtin_tool_manager,
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
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
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
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
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
        )

    @classmethod
    def from_run_context(
        cls,
        logger: Logger,
        config: ToolManagerConfig,
        *,
        run_context: ToolRunContext,
        tool_progress_reporter: ToolProgressReporter,
        mcp_manager: MCPManager,
        a2a_manager: A2AManager,
        api_mode: Literal["responses"] = "responses",
        builtin_tool_manager: OpenAIBuiltInToolManager | None = None,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
    ) -> Self:
        if builtin_tool_manager is None:
            msg = "builtin_tool_manager is required for ResponsesApiToolManager"
            raise ValueError(msg)
        return super().from_run_context(
            logger=logger,
            config=config,
            run_context=run_context,
            tool_progress_reporter=tool_progress_reporter,
            mcp_manager=mcp_manager,
            a2a_manager=a2a_manager,
            api_mode=api_mode,
            builtin_tool_manager=builtin_tool_manager,
            chat_service=chat_service,
            language_model_service=language_model_service,
            content_service=content_service,
        )

    def get_required_include_params(self) -> list[ResponseIncludable]:
        """Return Responses API include params required by all active built-in tools."""
        return self._builtin_tool_manager.get_required_include_params()
