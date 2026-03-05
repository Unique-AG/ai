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
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
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
from unique_toolkit.chat.cancellation import CancellationEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService
from unique_toolkit.content.schemas import Content
from unique_toolkit.language_model import LanguageModelAssistantMessage
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
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
        agent_file_registry: list[str] | None = None,
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
        self._agent_file_registry: list[str] = agent_file_registry if agent_file_registry is not None else []
        self._pdf_fallback_occurred = False
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
    async def _on_cancellation(self, _event: CancellationEvent) -> None:
        """Subscriber called by the cancellation event bus."""
        self._logger.info("Agent stopped by user request.")
        await self._chat_service.modify_assistant_message_async(
            set_completed_at=True,
        )

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

        sub = self._chat_service.cancellation.on_cancellation.subscribe(
            self._on_cancellation
            
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

            if self._pdf_fallback_occurred:
                await self._report_pdf_fallback_step()
                self._pdf_fallback_occurred = False

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
        try:
            max_iterations = self._effective_max_loop_iterations
            for i in range(max_iterations):
                if await self._chat_service.cancellation.check_cancellation_async():
                    break

                self.current_iteration_index = i
                self._logger.info(f"Starting iteration {i + 1}...")

                loop_response = await self._plan_or_execute()
                self._logger.info("Done with _plan_or_execute")

                if await self._chat_service.cancellation.check_cancellation_async():
                    break

                self._reference_manager.add_references(loop_response.message.references)
                self._logger.info("Done with adding references")

                self._thinking_manager.update_tool_progress_reporter(loop_response)

                exit_loop = await self._process_plan(loop_response)
                self._logger.info("Done with _process_plan")

                if await self._chat_service.cancellation.check_cancellation_async():
                    break

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

            if not self._chat_service.cancellation.is_cancelled:
                await self._update_debug_info_if_tool_took_control()
                await self._chat_service.modify_assistant_message_async(
                    set_completed_at=not self._tool_took_control,
                )
        finally:
            sub.cancel()

    _OPEN_PDF_TOOL_NAME = "OpenPdf"


    # @track()
    async def _plan_or_execute(self) -> LanguageModelStreamResponse:
        self._logger.info("Planning or executing the loop.")
        messages = await self._compose_message_plan_execution()

        self._logger.info("Done composing message plan execution.")

        tool_definitions = self._tool_manager.get_tool_definitions()

        try:
            return await self._loop_iteration_runner(
                messages=messages,
                iteration_index=self.current_iteration_index,
                streaming_handler=self._streaming_handler,  # type: ignore (constructor accepts only compatible arguments)
                model=self._config.space.language_model,
                tools=tool_definitions,  # type: ignore (as above)
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self._config.agent.experimental.temperature,
                tool_choices=self._tool_manager.get_forced_tools(),  # type: ignore (as above)
                other_options=self._config.agent.experimental.additional_llm_options,
            )
        except Exception as exc:
            if not self._should_retry_without_pdf_files(exc):
                raise
            return await self._retry_without_pdf_files(messages)

    _RETRY_SIGNALS = (
        "too large",
        "payload too large",
        "request entity too large",
        "content_length_exceeded",
        "max_tokens",
        "context_length_exceeded",
        "413",
        "request too large",
        "403 forbidden",
        "application-gateway",
    )

    def _should_retry_without_pdf_files(self, exc: Exception) -> bool:
        """Return True when the error looks like a payload-too-large or related
        backend rejection that can be resolved by dropping the PDF file parts."""
        cfg = self._config.agent.experimental.open_pdf_tool_config
        if not cfg.send_pdf_files_in_payload and not cfg.send_uploaded_pdf_in_payload:
            return False
        if not self._agent_file_registry and not self._get_uploaded_documents():
            return False
        error_text = str(exc).lower()
        return any(s in error_text for s in self._RETRY_SIGNALS)

    _PDF_TOO_LARGE_TOOL_RESPONSE = (
        "ERROR: The PDF file is too large to open. "
        "Could not include the document in the context. "
        "Please inform the user that the file is too large to process directly "
        "and suggest asking an admin to include the document in the knowledge base."
    )

    async def _retry_without_pdf_files(
        self, messages: LanguageModelMessages
    ) -> LanguageModelStreamResponse:
        """Strip PDF file parts from messages, remove the OpenPdf tool, and retry.

        Two different strategies depending on the source:
        - KB PDFs (via OpenPdf + InternalSearch): strip the OpenPdf tool call
          and tool response entirely.  The LLM falls back to the InternalSearch
          chunks it already has.
        - Uploaded PDFs: inject a synthetic OpenPdf tool call + error response
          so the LLM knows the files could not be opened and can inform the user.
        """
        self._logger.warning(
            "LLM call failed (likely payload too large). "
            "Retrying without PDF files."
        )

        self._tool_manager.remove_tool(self._OPEN_PDF_TOOL_NAME)
        self._pdf_fallback_occurred = True

        messages = self._strip_file_parts_from_messages(messages)
        self._strip_open_pdf_messages(messages)
        self._inject_uploaded_pdf_fallback_messages(messages)
        self._agent_file_registry.clear()
        tool_definitions = self._tool_manager.get_tool_definitions()

        return await self._loop_iteration_runner(
            messages=messages,
            iteration_index=self.current_iteration_index,
            streaming_handler=self._streaming_handler,  # type: ignore
            model=self._config.space.language_model,
            tools=tool_definitions,  # type: ignore
            content_chunks=self._reference_manager.get_chunks(),
            start_text=self.start_text,
            debug_info=self._debug_info_manager.get(),
            temperature=self._config.agent.experimental.temperature,
            tool_choices=self._tool_manager.get_forced_tools(),  # type: ignore
            other_options=self._config.agent.experimental.additional_llm_options,
        )

    def _strip_open_pdf_messages(
        self, messages: LanguageModelMessages
    ) -> None:
        """Remove OpenPdf tool calls from assistant messages and their
        corresponding tool response messages entirely.
        The LLM falls back to InternalSearch chunks."""
        open_pdf_call_ids: set[str] = set()

        for msg in messages.root:
            if not isinstance(msg, LanguageModelAssistantMessage):
                continue
            if not msg.tool_calls:
                continue
            for tc in msg.tool_calls:
                if tc.function.name == self._OPEN_PDF_TOOL_NAME:
                    open_pdf_call_ids.add(tc.id or tc.function.id)

        if not open_pdf_call_ids:
            return

        # Remove tool response messages for OpenPdf calls
        messages.root[:] = [
            msg for msg in messages.root
            if not (
                isinstance(msg, LanguageModelToolMessage)
                and msg.tool_call_id in open_pdf_call_ids
            )
        ]

        # Remove OpenPdf tool calls from assistant messages
        for msg in messages.root:
            if not isinstance(msg, LanguageModelAssistantMessage):
                continue
            if not msg.tool_calls:
                continue
            msg.tool_calls = [
                tc for tc in msg.tool_calls
                if tc.function.name != self._OPEN_PDF_TOOL_NAME
            ]

    def _inject_uploaded_pdf_fallback_messages(
        self, messages: LanguageModelMessages
    ) -> None:
        """For uploaded PDFs that were silently attached, inject a synthetic
        OpenPdf tool call + error response so the LLM knows why the files
        are gone and can inform the user."""
        uploaded_docs = self._get_uploaded_documents()
        if not uploaded_docs:
            return

        content_ids = [doc.id for doc in uploaded_docs if doc.id]
        if not content_ids:
            return

        func = LanguageModelFunction(
            name=self._OPEN_PDF_TOOL_NAME,
            arguments={"content_ids": content_ids},
        )
        assistant_msg = LanguageModelAssistantMessage.from_functions([func])
        tool_msg = LanguageModelToolMessage(
            content=self._PDF_TOO_LARGE_TOOL_RESPONSE,
            name=self._OPEN_PDF_TOOL_NAME,
            tool_call_id=func.id,
        )
        messages.root.append(assistant_msg)
        messages.root.append(tool_msg)

    async def _report_pdf_fallback_step(self) -> None:
        """Add a step entry indicating the PDF was too large to open."""
        self._message_step_logger.create_message_log_entry(
            text=(
                "**Open PDF:** The PDF file is too large to open. "
                "Please ask an admin to include the document in the knowledge base."
            ),
            references=[],
        )

    @staticmethod
    def _strip_file_parts_from_messages(
        messages: LanguageModelMessages,
    ) -> LanguageModelMessages:
        """Remove file/input_file parts from user messages, keeping only text."""
        for i, msg in enumerate(messages.root):
            if msg.role != LanguageModelMessageRole.USER:
                continue
            if not isinstance(msg.content, list):
                continue
            text_parts = [
                p for p in msg.content
                if isinstance(p, dict) and p.get("type") in ("text", "input_text")
            ]
            if text_parts:
                text = " ".join(p.get("text", "") for p in text_parts).strip()
                messages.root[i] = LanguageModelUserMessage(content=text)
        return messages

    _OPEN_PDF_SYSTEM_REMINDER = (
        "<|system_reminder|>PDF documents were found in the search results. "
        "For any PDF you want to reference or reason over, call the OpenPdf tool "
        "with the content_id from the search results. The document name is shown "
        "inside <|document|>…<|/document|> tags in the content field. "
        "The full PDF provides far better information than the extracted text "
        "chunks (tables, charts, layout, and cross-page context are preserved)."
        "<|/system_reminder|>"
    )

    def _inject_open_pdf_reminder(
        self, tool_call_responses: list,
    ) -> None:
        """When OpenPdf is available, append a system reminder to InternalSearch
        responses that contain PDF content_ids so the LLM is nudged to open them."""
        if not self._tool_manager.get_tool_by_name(self._OPEN_PDF_TOOL_NAME):
            return

        for resp in tool_call_responses:
            if resp.name != "InternalSearch":
                continue
            has_pdf_chunks = any(
                chunk.key and chunk.key.split(" : ")[0].lower().endswith(".pdf")
                for chunk in (resp.content_chunks or [])
            )
            if has_pdf_chunks:
                existing = resp.system_reminder or ""
                resp.system_reminder = (
                    f"{existing}\n{self._OPEN_PDF_SYSTEM_REMINDER}".strip()
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

        responses_cfg = self._config.agent.experimental.responses_api_config
        pdf_cfg = self._config.agent.experimental.open_pdf_tool_config
        if (responses_cfg.use_responses_api or self._config.agent.experimental.use_responses_api) and (
            pdf_cfg.send_pdf_files_in_payload
            or pdf_cfg.send_uploaded_pdf_in_payload
        ):
            messages = self._inject_content_files_into_user_message(messages)

        return messages

    def _get_uploaded_documents(self) -> list[Content]:
        """Lazily fetch and cache non-expired PDF documents uploaded to this chat."""
        if not hasattr(self, "_cached_uploaded_documents"):
            now = datetime.now(timezone.utc)
            all_docs = self._content_service.get_documents_uploaded_to_chat()
            self._cached_uploaded_documents = [
                doc
                for doc in all_docs
                if (doc.expired_at is None or doc.expired_at > now)
                and doc.key.lower().endswith(".pdf")
            ]
        return self._cached_uploaded_documents

    def _collect_content_file_parts(self) -> list[dict]:
        """Collect file parts to include in the LLM payload.

        Two independent sources, each gated by its own config flag:
        - Uploaded PDFs (send_uploaded_pdf_in_payload) — included automatically.
        - Knowledge-base PDFs (send_pdf_files_in_payload) — included when the
          agent calls OpenPdfTool with a content_id from search results.

        file_data uses a unique://content/<id> URL. The backend resolves this
        to the actual PDF bytes and base64-encodes them before forwarding to OpenAI.
        """
        cfg = self._config.agent.experimental.open_pdf_tool_config
        seen_ids: set[str] = set()
        file_parts: list[dict] = []

        if cfg.send_uploaded_pdf_in_payload:
            for doc in self._get_uploaded_documents():
                if doc.id and doc.id not in seen_ids:
                    seen_ids.add(doc.id)
                    file_parts.append(
                        {
                            "type": "file",
                            "file": {
                                "filename": doc.key or doc.id,
                                "file_data": f"unique://content/{doc.id}",
                            },
                        }
                    )

        if cfg.send_pdf_files_in_payload:
            for content_id in self._agent_file_registry:
                if content_id not in seen_ids:
                    seen_ids.add(content_id)
                    file_parts.append(
                        {
                            "type": "file",
                            "file": {
                                "filename": content_id,
                                "file_data": f"unique://content/{content_id}",
                            },
                        }
                    )

        return file_parts

    def _inject_content_files_into_user_message(
        self, messages: LanguageModelMessages
    ) -> LanguageModelMessages:
        """Append content file references to the last user message as input_file parts."""
        file_parts = self._collect_content_file_parts()
        if not file_parts:
            return messages

        for i in range(len(messages.root) - 1, -1, -1):
            msg = messages.root[i]
            if msg.role == LanguageModelMessageRole.USER:
                text_content = msg.content if isinstance(msg.content, str) else ""
                messages.root[i] = LanguageModelUserMessage(
                    content=[{"type": "text", "text": text_content}] + file_parts
                )
                break

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

        # Combine custom instructions and user instructions
        custom_instructions = self._config.space.custom_instructions
        if self._config.space.user_space_instructions:
            custom_instructions += (
                "\n\nAdditional instructions provided by the user:\n"
                + self._config.space.user_space_instructions
            )

        system_message = system_prompt_template.render(
            model_info=self._config.space.language_model.model_dump(mode="json"),
            date_string=date_string,
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            project_name=self._config.space.project_name,
            custom_instructions=custom_instructions,
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
        if self._agent_file_registry:
            selected_evaluation_names = [
                n for n in selected_evaluation_names
                if n != EvaluationMetricName.HALLUCINATION
            ]
            self._logger.info(
                "OpenPdf was used — skipping hallucination check "
                "(LLM has full PDF content, not just search chunks)."
            )
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

        self._inject_open_pdf_reminder(tool_call_responses)

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
