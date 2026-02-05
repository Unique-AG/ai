import asyncio
from datetime import datetime, timezone
from logging import Logger
from typing import overload

import jinja2
from typing_extensions import deprecated
from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
)
from unique_toolkit.agentic.evaluation.evaluation_manager import EvaluationManager
from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.loop_runner import (
    LoopIterationRunner,
    ResponsesLoopIterationRunner,
    is_qwen_model,
)
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    PostprocessorManager,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.thinking_manager.thinking_manager import ThinkingManager
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    SafeTaskExecutor,
    ToolManager,
)
from unique_toolkit.app.schemas import ChatEvent, McpServer
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelAssistantMessage
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelStreamResponse,
)
from unique_toolkit.protocols.support import (
    ResponsesSupportCompleteWithReferences,
    SupportCompleteWithReferences,
)

from unique_orchestrator.config import UniqueAIConfig

EMPTY_MESSAGE_WARNING = (
    "⚠️ **The language model was unable to produce an output.**\n"
    "It did not generate any content or perform a tool call in response to your request. "
    "This is a limitation of the language model itself.\n\n"
    "**Please try adapting or simplifying your prompt.** "
    "Rewording your input can often help the model respond successfully."
)


class UniqueAI:
    start_text = ""
    current_iteration_index = 0

    @overload
    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: UniqueAIConfig,
        chat_service: ChatService,
        content_service: ContentService,
        debug_info_manager: DebugInfoManager,
        streaming_handler: SupportCompleteWithReferences,
        reference_manager: ReferenceManager,
        thinking_manager: ThinkingManager,
        tool_manager: ToolManager,
        history_manager: HistoryManager,
        evaluation_manager: EvaluationManager,
        postprocessor_manager: PostprocessorManager,
        message_step_logger: MessageStepLogger,
        mcp_servers: list[McpServer],
        loop_iteration_runner: LoopIterationRunner,
    ) -> None: ...

    # Responses API Dependencies
    @overload
    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: UniqueAIConfig,
        chat_service: ChatService,
        content_service: ContentService,
        debug_info_manager: DebugInfoManager,
        streaming_handler: ResponsesSupportCompleteWithReferences,
        reference_manager: ReferenceManager,
        thinking_manager: ThinkingManager,
        tool_manager: ResponsesApiToolManager,
        history_manager: HistoryManager,
        evaluation_manager: EvaluationManager,
        postprocessor_manager: PostprocessorManager,
        message_step_logger: MessageStepLogger,
        mcp_servers: list[McpServer],
        loop_iteration_runner: ResponsesLoopIterationRunner,
    ) -> None: ...

    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: UniqueAIConfig,
        chat_service: ChatService,
        content_service: ContentService,
        debug_info_manager: DebugInfoManager,
        streaming_handler: ResponsesSupportCompleteWithReferences
        | SupportCompleteWithReferences,
        reference_manager: ReferenceManager,
        thinking_manager: ThinkingManager,
        tool_manager: ResponsesApiToolManager | ToolManager,
        history_manager: HistoryManager,
        evaluation_manager: EvaluationManager,
        postprocessor_manager: PostprocessorManager,
        message_step_logger: MessageStepLogger,
        mcp_servers: list[McpServer],
        loop_iteration_runner: LoopIterationRunner | ResponsesLoopIterationRunner,
    ) -> None:
        self._logger = logger
        self._event = event
        self._config = config
        self._chat_service = chat_service
        self._content_service = content_service

        self._debug_info_manager = debug_info_manager
        self._reference_manager = reference_manager
        self._thinking_manager = thinking_manager
        self._tool_manager = tool_manager

        self._history_manager = history_manager

        self._evaluation_manager = evaluation_manager
        self._postprocessor_manager = postprocessor_manager
        self._latest_assistant_id: str = event.payload.assistant_message.id
        self._mcp_servers = mcp_servers
        self._streaming_handler = streaming_handler

        self._message_step_logger = message_step_logger
        # Helper variable to support control loop
        self._tool_took_control = False
        self._loop_iteration_runner = loop_iteration_runner

    @property
    def _effective_max_loop_iterations(self) -> int:
        """Get the effective max loop iterations based on the model type."""
        if is_qwen_model(model=self._config.space.language_model):
            qwen_config = (
                self._config.agent.experimental.loop_configuration.model_specific.qwen
            )
            return qwen_config.max_loop_iterations
        return self._config.agent.max_loop_iterations

    ############################################################
    # Override of base methods
    ############################################################
    # @track(name="loop_agent_run")  # Group traces together
    async def run(self):
        """
        Main loop of the agent. The agent will iterate through the loop, runs the plan and
        processes tool calls if any are returned.
        """
        self._logger.info("Start LoopAgent...")

        if not feature_flags.enable_new_answers_ui_un_14411.is_enabled(
            self._event.company_id
        ):
            self._chat_service.modify_assistant_message(
                content="Starting agentic loop..."  # TODO: this must be more informative
            )

        ## Loop iteration
        max_iterations = self._effective_max_loop_iterations
        for i in range(max_iterations):
            self.current_iteration_index = i
            self._logger.info(f"Starting iteration {i + 1}...")

            # Plan execution
            loop_response = await self._plan_or_execute()
            self._logger.info("Done with _plan_or_execute")

            self._reference_manager.add_references(loop_response.message.references)
            self._logger.info("Done with adding references")

            # Update tool progress reporter
            self._thinking_manager.update_tool_progress_reporter(loop_response)

            # Execute the plan
            exit_loop = await self._process_plan(loop_response)
            self._logger.info("Done with _process_plan")

            if exit_loop:
                self._thinking_manager.close_thinking_steps(loop_response)
                self._logger.info("Exiting loop.")
                break

            if i == max_iterations - 1:
                self._logger.error("Max iterations reached.")
                await self._chat_service.modify_assistant_message_async(
                    content="I have reached the maximum number of self-reflection iterations. Please clarify your request and try again...",
                )
                break

            self.start_text = self._thinking_manager.update_start_text(
                self.start_text, loop_response
            )
        await self._update_debug_info_if_tool_took_control()

        # Only set completed_at if no tool took control. Tools that take control will set the message state to completed themselves.
        await self._chat_service.modify_assistant_message_async(
            set_completed_at=not self._tool_took_control,
        )

    # @track()
    async def _plan_or_execute(self) -> LanguageModelStreamResponse:
        self._logger.info("Planning or executing the loop.")
        messages = await self._compose_message_plan_execution()

        self._logger.info("Done composing message plan execution.")

        return await self._loop_iteration_runner(
            messages=messages,
            iteration_index=self.current_iteration_index,
            streaming_handler=self._streaming_handler,  # type: ignore (constructor accepts only compatible arguments)
            model=self._config.space.language_model,
            tools=self._tool_manager.get_tool_definitions(),  # type: ignore (as above)
            content_chunks=self._reference_manager.get_chunks(),
            start_text=self.start_text,
            debug_info=self._debug_info_manager.get(),
            temperature=self._config.agent.experimental.temperature,
            tool_choices=self._tool_manager.get_forced_tools(),  # type: ignore (as above)
            other_options=self._config.agent.experimental.additional_llm_options,
        )

    async def _process_plan(self, loop_response: LanguageModelStreamResponse) -> bool:
        self._logger.info(
            "Processing the plan, executing the tools and checking for loop exit conditions once all is done."
        )

        if loop_response.is_empty():
            self._logger.debug("Empty model response, exiting loop.")
            self._chat_service.modify_assistant_message(content=EMPTY_MESSAGE_WARNING)
            return True

        call_tools = len(loop_response.tool_calls or []) > 0
        if call_tools:
            self._logger.debug(
                "Tools were called we process them and do not exit the loop"
            )
            await self._create_new_assistant_message_if_loop_response_contains_content(
                loop_response
            )

            return await self._handle_tool_calls(loop_response)

        self._logger.debug("No tool calls. we might exit the loop")

        return await self._handle_no_tool_calls(loop_response)

    async def _compose_message_plan_execution(self) -> LanguageModelMessages:
        original_user_message = self._event.payload.user_message.text
        rendered_user_message_string = await self._render_user_prompt()
        rendered_system_message_string = await self._render_system_prompt()

        messages = await self._history_manager.get_history_for_model_call(
            original_user_message,
            rendered_user_message_string,
            rendered_system_message_string,
            self._postprocessor_manager.remove_from_text,
        )
        return messages

    async def _render_user_prompt(self) -> str:
        user_message_template = jinja2.Template(
            self._config.agent.prompt_config.user_message_prompt_template
        )

        tool_descriptions_with_user_prompts = [
            prompts.tool_user_prompt
            for prompts in self._tool_manager.get_tool_prompts()
        ]

        used_tools = [t.name for t in self._history_manager.get_tool_calls()]
        sub_agent_calls = self._tool_manager.filter_tool_calls(
            self._history_manager.get_tool_calls(), ["subagent"]
        )

        mcp_server_user_prompts = [
            mcp_server.user_prompt for mcp_server in self._mcp_servers
        ]

        user_metadata = self._get_filtered_user_metadata()

        tool_descriptions = self._tool_manager.get_tool_prompts()

        query = self._event.payload.user_message.text

        if (
            self._config.agent.experimental.sub_agents_config.referencing_config
            is not None
            and len(sub_agent_calls) > 0
        ):
            use_sub_agent_references = True
            sub_agent_referencing_instructions = self._config.agent.experimental.sub_agents_config.referencing_config.referencing_instructions_for_user_prompt
        else:
            use_sub_agent_references = False
            sub_agent_referencing_instructions = None

        user_msg = user_message_template.render(
            query=query,
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            mcp_server_user_prompts=list(mcp_server_user_prompts),
            tool_descriptions_with_user_prompts=tool_descriptions_with_user_prompts,
            use_sub_agent_references=use_sub_agent_references,
            sub_agent_referencing_instructions=sub_agent_referencing_instructions,
            user_metadata=user_metadata,
        )
        return user_msg

    async def _render_system_prompt(self) -> str:
        # TODO: Collect tool information here and adapt to system prompt
        tool_descriptions = self._tool_manager.get_tool_prompts()

        used_tools = [t.name for t in self._history_manager.get_tool_calls()]
        sub_agent_calls = self._tool_manager.filter_tool_calls(
            self._history_manager.get_tool_calls(), ["subagent"]
        )

        system_prompt_template = jinja2.Template(
            self._config.agent.prompt_config.system_prompt_template
        )

        date_string = datetime.now().strftime("%A %B %d, %Y")

        user_metadata = self._get_filtered_user_metadata()

        mcp_server_system_prompts = [
            mcp_server.system_prompt for mcp_server in self._mcp_servers
        ]

        if (
            self._config.agent.experimental.sub_agents_config.referencing_config
            is not None
            and len(sub_agent_calls) > 0
        ):
            use_sub_agent_references = True
            sub_agent_referencing_instructions = self._config.agent.experimental.sub_agents_config.referencing_config.referencing_instructions_for_system_prompt
        else:
            use_sub_agent_references = False
            sub_agent_referencing_instructions = None

        uploaded_documents = self._content_service.get_documents_uploaded_to_chat()
        uploaded_documents_expired = [
            doc
            for doc in uploaded_documents
            if doc.expired_at is not None
            and doc.expired_at <= datetime.now(timezone.utc)
        ]

        system_message = system_prompt_template.render(
            model_info=self._config.space.language_model.model_dump(mode="json"),
            date_string=date_string,
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            project_name=self._config.space.project_name,
            custom_instructions=self._config.space.custom_instructions,
            max_tools_per_iteration=self._config.agent.experimental.loop_configuration.max_tool_calls_per_iteration,
            max_loop_iterations=self._effective_max_loop_iterations,
            current_iteration=self.current_iteration_index + 1,
            mcp_server_system_prompts=mcp_server_system_prompts,
            use_sub_agent_references=use_sub_agent_references,
            sub_agent_referencing_instructions=sub_agent_referencing_instructions,
            user_metadata=user_metadata,
            uploaded_documents_expired=uploaded_documents_expired,
        )
        return system_message

    async def _handle_no_tool_calls(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        """Handle the case where no tool calls are returned."""
        task_executor = SafeTaskExecutor(
            logger=self._logger,
        )

        selected_evaluation_names = self._tool_manager.get_evaluation_check_list()
        evaluation_results = task_executor.execute_async(
            self._evaluation_manager.run_evaluations,
            selected_evaluation_names,
            loop_response,
            self._latest_assistant_id,
        )

        postprocessor_result = task_executor.execute_async(
            self._postprocessor_manager.run_postprocessors,
            loop_response.model_copy(deep=True),
        )

        _, evaluation_results = await asyncio.gather(
            postprocessor_result,
            evaluation_results,
        )

        if evaluation_results.success and not all(
            result.is_positive for result in evaluation_results.unpack()
        ):
            self._logger.warning(
                "we should add here the retry counter add an instruction and retry the loop for now we just exit the loop"
            )  # TODO: add retry counter and instruction

        return True

    def _log_tool_calls(self, tool_calls: list) -> None:
        # Create dictionary mapping tool names to display names for efficient lookup
        all_tools_dict: dict[str, str] = {
            tool.name: tool.display_name()
            for tool in self._tool_manager.available_tools
        }

        # Tool names that should not be logged in the message steps
        tool_names_not_to_log = ["DeepResearch"]

        used_tools: dict[str, int] = {}
        for tool_call in tool_calls:
            self._history_manager.add_tool_call(tool_call)
            if tool_call.name in all_tools_dict:
                used_tools[tool_call.name] = used_tools.get(tool_call.name, 0) + 1

        tool_calls_logs = []
        for tool_name, count in used_tools.items():
            if tool_name in tool_names_not_to_log:
                continue
            display_name = all_tools_dict[tool_name] or tool_name
            tool_calls_logs.append(
                f"{display_name} ({count}x)" if count > 1 else f"{display_name}"
            )

        if tool_calls_logs:
            tool_calls_logs_to_string = "\n - ".join(tool_calls_logs)
            self._message_step_logger.create_message_log_entry(
                text=f"**Triggered Tool Calls:**\n - {tool_calls_logs_to_string}",
                references=[],
            )

    async def _handle_tool_calls(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        """Handle the case where tool calls are returned."""
        self._logger.info("Processing tool calls")

        tool_calls = loop_response.tool_calls or []

        # Filter tool calls
        tool_calls = self._tool_manager.filter_duplicate_tool_calls(tool_calls)
        tool_calls = self._tool_manager.filter_tool_calls_by_max_tool_calls_allowed(
            tool_calls
        )

        # Append function calls to history
        self._history_manager._append_tool_calls_to_history(tool_calls)

        # Log tool calls
        self._log_tool_calls(tool_calls)
        # Execute tool calls
        tool_call_responses = await self._tool_manager.execute_selected_tools(
            tool_calls
        )

        # Process results with error handling
        # Add tool call results to history first to stabilize source numbering,
        # then extract referenceable chunks and debug info
        self._history_manager.add_tool_call_results(tool_call_responses)
        self._reference_manager.extract_referenceable_chunks(tool_call_responses)
        self._debug_info_manager.extract_tool_debug_info(
            tool_call_responses, self.current_iteration_index
        )

        self._tool_took_control = self._tool_manager.does_a_tool_take_control(
            tool_calls
        )
        return self._tool_took_control

    async def _create_new_assistant_message_if_loop_response_contains_content(
        self, loop_response: LanguageModelStreamResponse
    ) -> None:
        if self._thinking_manager.thinking_is_displayed():
            return
        if not loop_response.message.text:
            return

        # if anything sets the start text the model did not produce content.
        # So we need to remove that text from the message.
        message_text_without_start_text = loop_response.message.text.replace(
            self.start_text.strip(), ""
        ).strip()
        if message_text_without_start_text == "":
            return

        ###
        # ToDo: Once references on existing assistant messages can be deleted, we will switch from creating a new assistant message to modifying the existing one (with previous references deleted)
        ###
        new_assistant_message = await self._chat_service.create_assistant_message_async(
            content=""
        )

        # the new message must have an id that is valid else we use the old one
        self._latest_assistant_id = (
            new_assistant_message.id or self._latest_assistant_id
        )

        self._history_manager.add_assistant_message(
            LanguageModelAssistantMessage(
                content=loop_response.message.original_text or "",
            )
        )

    def _get_filtered_user_metadata(self) -> dict[str, str]:
        """
        Filter user metadata to only include keys specified in the agent's prompt config.

        Returns:
            Dictionary containing only the metadata keys that are configured to be included.
        """
        user_metadata = {}
        if (
            self._config.agent.prompt_config.user_metadata
            and self._event.payload.user_metadata is not None
        ):
            # Filter metadata to only include selected keys
            user_metadata = {
                k: str(v)
                for k, v in self._event.payload.user_metadata.items()
                if k in self._config.agent.prompt_config.user_metadata
            }
        return user_metadata

    async def _update_debug_info_if_tool_took_control(self) -> None:
        """
        Update debug info when a tool takes control of the conversation.
        DeepResearch is excluded as it handles debug info directly since it calls
        the orchestrator multiple times.
        """
        if not self._tool_took_control:
            return

        tool_names = [tool["name"] for tool in self._debug_info_manager.get()["tools"]]
        if "DeepResearch" in tool_names:
            return

        debug_info_event = {
            "assistant": {
                "id": self._event.payload.assistant_id,
                "name": self._event.payload.name,
            },
            "chosenModule": self._event.payload.name,
            "userMetadata": self._event.payload.user_metadata,
            "toolParameters": self._event.payload.tool_parameters,
            **self._debug_info_manager.get(),
        }

        await self._chat_service.update_debug_info_async(debug_info=debug_info_event)


@deprecated("Use UniqueAI directly instead")
class UniqueAIResponsesApi(UniqueAI):
    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: UniqueAIConfig,
        chat_service: ChatService,
        content_service: ContentService,
        debug_info_manager: DebugInfoManager,
        streaming_handler: ResponsesSupportCompleteWithReferences,
        reference_manager: ReferenceManager,
        thinking_manager: ThinkingManager,
        tool_manager: ResponsesApiToolManager,
        history_manager: HistoryManager,
        evaluation_manager: EvaluationManager,
        postprocessor_manager: PostprocessorManager,
        message_step_logger: MessageStepLogger,
        mcp_servers: list[McpServer],
        loop_iteration_runner: ResponsesLoopIterationRunner,
    ) -> None:
        super().__init__(
            logger,
            event=event,
            config=config,
            chat_service=chat_service,
            content_service=content_service,
            debug_info_manager=debug_info_manager,
            streaming_handler=streaming_handler,
            reference_manager=reference_manager,
            thinking_manager=thinking_manager,
            tool_manager=tool_manager,
            history_manager=history_manager,
            evaluation_manager=evaluation_manager,
            postprocessor_manager=postprocessor_manager,
            message_step_logger=message_step_logger,
            mcp_servers=mcp_servers,
            loop_iteration_runner=loop_iteration_runner,
        )
