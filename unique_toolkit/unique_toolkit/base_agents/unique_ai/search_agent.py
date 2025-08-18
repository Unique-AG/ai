import hashlib
from datetime import datetime

import jinja2
import tiktoken
import unique_sdk
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import Content
from unique_toolkit.language_model import (
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelToolMessage,
)
from unique_toolkit.language_model.infos import (
    LanguageModelName,
    get_encoder_name,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)

from unique_ai.config import LoopAgentConfig, UniqueAIConfig

from unique_ai.services.reference_manager.reference_manager_service import (
    ReferenceManagerService,
)
from unique_ai.services.reference_manager.utils import (
    reduce_message_length_by_reducing_sources_in_tool_response_excluding_reference_manger_sources,
)
from unique_ai.utils import (
    create_content_reference,
    filter_duplicates_from_list_on_string_representation,
    get_approximate_token_count_sources,
)
from unique_toolkit.base_agents.loop_agent.agent import LoopAgent
from unique_toolkit.base_agents.loop_agent.config import LoopAgentTokenLimitsConfig
from unique_toolkit.tools.config import ToolBuildConfig
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.tool import Tool
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter



class SearchAgent(LoopAgent):
    def __init__(
        self,
        event: ChatEvent,
        config: UniqueAIConfig,
        reference_manager_service: ReferenceManagerService | None = None,
    ):
        loop_agent_config = LoopAgentConfig(
            language_model=config.space.language_model,
            temperature=config.agent.experimental.temperature,
            additional_llm_options=config.agent.experimental.additional_llm_options,
            max_loop_iterations=config.agent.max_loop_iterations,
            tools=config.space.tools,
            thinking_steps_display=config.agent.experimental.thinking_steps_display,
            token_limits=LoopAgentTokenLimitsConfig(
                language_model=config.space.language_model,
                percent_of_max_tokens_for_history=config.agent.input_token_distribution.percent_for_history,
            ),
        )
        if isinstance(
            config.space.language_model.name,
            LanguageModelName,
        ):
            encoder_name = get_encoder_name(
                config.space.language_model.name,
            )
            self.encoding_model = (
                encoder_name.value if encoder_name else "cl100k_base"
            )
        else:
            self.encoding_model = "cl100k_base"

        super().__init__(
            event=event,
            config=loop_agent_config,
        )

        # TOOLS
        self.tool_call_option = None
        self.chat_uploaded_files: list[Content] = (
            self._get_documents_uploaded_to_chat()
        )

        # Note: That the agent is only used once and initialized for each event
        # that is received. This has to be refactored if the same instance would
        # get this multiple times.
        self.unique_ai_config = config

        self.tools = self._temporary_patch_for_uploaded_files()

        # Services
        self._services = ServicesContainer()

        if (
            self.unique_ai_config.agent.services.follow_up_questions_config
            and self.unique_ai_config.agent.services.follow_up_questions_config.number_of_questions
            > 0
        ):
            self._services.follow_up_question_service = FollowUpQuestionService(
                config=self.unique_ai_config.agent.services.follow_up_questions_config,
            )

        if self.unique_ai_config.agent.services.evaluation_config:
            self._services.evaluation_service = EvaluationService(
                chat_service=self.chat_service,
                llm_service=self.llm_service,
                config=self.unique_ai_config.agent.services.evaluation_config,
                company_id=self.event.company_id,
                user_id=self.event.user_id,
            )

        self._services.reference_manager_service = reference_manager_service
        if reference_manager_service:
            self.agent_chunks_handler.replace(reference_manager_service.chunks)

        # Supporting variables
        self.evaluation_result_passed: bool = True
        self.thinking_steps: str = ""
        self.thinking_step_number: int = 1
        self.review_steps: int = 0
        self.user_info_tool_calls: str = ""
        self.messages_to_delete: list[str] = []
        self.internal_search_tool_seen_for_uploaded_content_over_limit: bool = False

    def _temporary_patch_for_uploaded_files(
        self,
    ) -> None:
       
        if len(self.chat_uploaded_files) > 0: 
            found = self._tool_manager.get_tool_by_name("InternalSearchTool")
            if(not found):
                self._chat_service.modify_assistant_message(
                    content=f"⚠️ Configuration is wrong, there must be Internal Search configured for document Uploads. Please report to admin for UniqueAI.\n",
                )
                raise Exception(
                    "InternalSearchTool is not configured in the tools. Please configure it to use the uploaded content."
                )
            # cast found[0] as internal search tool
            internal_search_tool: InternalSearchTool = found
            internal_search_tool.set_chatOnly()



    # @track()
    async def _plan_or_execute(self):
        """Will determine if any tool calls are needed.

        The stream_complete function will return either (1) a final response,
        (2) tool calls or (3) a response with additional tool calls.

        Returns
        -------
        LanguageModelStreamResponse: The response from the stream_complete

        """
        self._logger.info("Planning or executing the loop.")
        messages = await self._compose_message_plan_execution()
        self._logger.info("Done composing message plan execution.")

        # Forces tool calls only in first iteration
        forced_tools = self._tool_manager.get_forced_tools()
        if (
            (len(forced_tools) > 0)
            and self.current_iteration_index == 0
        ):
            responses = [
                await self._chat_service.stream_complete_async(
                    messages=messages,
                    model_name=self.unique_ai_config.space.language_model.name,
                    tools=self._tool_manager.get_tool_definitions(),
                    content_chunks=self.agent_chunks_handler.chunks,
                    start_text=self.start_text,
                    debug_info=self._debug_info_manager.get(),
                    temperature=self.unique_ai_config.agent.experimental.temperature,
                    other_options=self.unique_ai_config.agent.experimental.additional_llm_options
                    | {"toolChoice": opt},
                )
                for opt in forced_tools
            ]

            # Merge responses and refs:
            tool_calls = []
            references = []
            for r in responses:
                if r.tool_calls:
                    tool_calls.extend(r.tool_calls)
                references.extend(r.message.references)

            stream_response = responses[0]
            stream_response.tool_calls = (
                tool_calls if len(tool_calls) > 0 else None
            )
            stream_response.message.references = references
        elif (
            self.current_iteration_index
            == self.unique_ai_config.agent.max_loop_iterations - 1
        ):
            # No tool calls in last iteration
            stream_response = await self._chat_service.stream_complete_async(
                messages=messages,
                model_name=self.unique_ai_config.space.language_model.name,
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self.unique_ai_config.agent.experimental.temperature,
                other_options=self.unique_ai_config.agent.experimental.additional_llm_options,
            )

        else:
            stream_response = await self._chat_service.stream_complete_async(
                messages=messages,
                model_name=self.unique_ai_config.space.language_model.name,
                tools=self._tool_manager.get_tool_definitions(),
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self.unique_ai_config.agent.experimental.temperature,
                other_options=self.unique_ai_config.agent.experimental.additional_llm_options,
            )

    
   
        dedup_tool_calls = (
            filter_duplicates_from_list_on_string_representation(
                stream_response.tool_calls or [],
            )
        )
        stream_response.tool_calls = (
            dedup_tool_calls if len(dedup_tool_calls) > 0 else None
        )
        stream_response.message.references = (
            filter_duplicates_from_list_on_string_representation(
                stream_response.message.references,
            )
        )

        return stream_response

    ############################################################
    ### Required methods to be defined by the BaseAgent class
    ############################################################
    #@track()
    async def _compose_message_plan_execution(self) -> LanguageModelMessages:
        """Compose the system and user messages for the plan execution step, which is evaluating if any further tool calls are required."""

        messages = await self._create_plan_execution_messages()

        token_count = self._count_message_tokens(messages)
        self._log_token_usage(token_count)

        while self._exceeds_token_limit(token_count):
            token_count_before_reduction = token_count
            self._handle_token_limit_exceeded()
            messages = await self._create_plan_execution_messages()
            token_count = self._count_message_tokens(messages)
            self._log_token_usage(token_count)
            token_count_after_reduction = token_count
            if token_count_after_reduction >= token_count_before_reduction:
                break

        return messages

    #@track()
    async def _create_plan_execution_messages(self) -> LanguageModelMessages:
        """Create messages for plan execution with current tools and history."""
        # Load and render the user message template using Jinja2
        history = await self._history_manager.remove_post_processing_manipulations(
            self._services.postprocessor_manager.remove_from_text,
        )

        user_message_template = jinja2.Template(
            self.unique_ai_config.agent.prompt_config.user_message_prompt_template
        )

        query = self._event.payload.user_message.text

        user_msg = user_message_template.render(
            query=query,
        )

        # Chat history integrates the user message already, here we modify eventually
        if history[-1].role == LanguageModelMessageRole.USER:
            m = history[-1]

            if isinstance(m.content, list):
                # Replace the last text element but be careful not to delete data added when merging with contents
                for t in reversed(m.content):
                    field = t.get("type", "")
                    if field == "text" and isinstance(field, dict):
                        inner_field = field.get("text", "")
                        if isinstance(inner_field, str):
                            added_to_message_by_history = inner_field.replace(
                                query,
                                "",
                            )
                            t["text"] = user_msg + added_to_message_by_history
                        break
            elif m.content:
                added_to_message_by_history = m.content.replace(query, "")
                m.content = user_msg + added_to_message_by_history
        else:
            history = history + [
                LanguageModelUserMessage(content=user_msg),
            ]

        system_msg = self._get_system_message_for_plan_execution()

        messages = LanguageModelMessages(
            [system_msg] + history + self._loop_history,
        )

        return messages

    #@track()
    async def _obtain_chat_history_as_llm_messages(
        self,
    ) -> list[LanguageModelMessage]:
        # Get the full history from the reference manager
        if self._services.reference_manager_service:
            full_history = self._services.reference_manager_service.history
        else:
            full_history = get_full_history_with_contents(
                user_message=self._event.payload.user_message,
                chat_id=self._event.payload.chat_id,
                chat_service=self._chat_service,
                content_service=self._content_service,
                file_content_serialization_type=(
                    FileContentSerialization.NONE
                    if self.unique_ai_config.agent.services.uploaded_content_config
                    else FileContentSerialization.FILE_NAME
                ),
            )

      
        full_history.root = remove_ticker_plot_data_from_history(
            history=full_history.root,
        )

        # Apply token limiting to prevent history from growing too large
        limited_history_messages = limit_to_token_window(
            full_history,
            self.unique_ai_config.agent.input_token_distribution.max_history_tokens(
                self.unique_ai_config.space.language_model.token_limits.token_limit_input,
            ),
            self.unique_ai_config.space.language_model.encoder_name,
        )

        # If reduced to 0, we take the last message assumed to be the user message
        if len(limited_history_messages.root) == 0:
            limited_history_messages.root = full_history.root[-1:]

        self.logger.info(
            f"Reduced history to {len(limited_history_messages.root)} messages from {len(full_history.root)}",
        )

        """
        
        As the token limit can be reached in the middle of a gpt_request, 
        we move forward to the next user message,to avoid confusing messages for the LLM
        """
        idx = 0
        for idx, message in enumerate(limited_history_messages):
            if message.role == LanguageModelMessageRole.USER:
                break

        # FIXME: This might reduce the history by a lot if we have a lot of tool calls / references in the history. Could make sense to summarize the messages and include
        # FIXME: We should remove chunks no longer in history from handler
        return limited_history_messages[idx:]

    def _count_message_tokens(self, messages: LanguageModelMessages) -> int:
        """Count tokens in messages using the configured encoding model."""
        encoder = tiktoken.get_encoding(self.encoding_model)
        return num_token_for_language_model_messages(
            messages=messages,
            encode=encoder.encode,
        )

    def _log_token_usage(self, token_count: int) -> None:
        """Log token usage and update debug info."""
        self.logger.info(f"Token messages: {token_count}")
        self.agent_debug_info.add("token_messages", token_count)

    def _exceeds_token_limit(self, token_count: int) -> bool:
        """Check if token count exceeds the maximum allowed limit and if at least one tool call has more than one source."""
        # At least one tool call should have more than one chunk as answer
        has_multiple_chunks_for_a_tool_call = any(
            len(self.agent_chunks_handler.tool_chunks[tool_call_id]["chunks"])
            > 1
            for tool_call_id in self.agent_chunks_handler.tool_chunks
        )

        # TODO: This is not fully correct at the moment as the token_count
        # include system_prompt and user question already
        # TODO: There is a problem if we exceed but only have one chunk per tool call
        exceeds_limit = (
            token_count
            > self.unique_ai_config.space.language_model.token_limits.token_limit_input
        )

        return has_multiple_chunks_for_a_tool_call and exceeds_limit

    def _handle_token_limit_exceeded(self) -> None:
        """Handle case where token limit is exceeded by reducing sources in tool responses."""
        self._logger.warning(
            f"Length of messages is exceeds limit of {self.unique_ai_config.space.language_model.token_limits.token_limit_input} tokens. "
            "Reducing number of sources per tool call.",
        )
        if self._services.reference_manager_service:
            # TODO: Validate
            self._loop_history, self.agent_chunks_handler = (
                reduce_message_length_by_reducing_sources_in_tool_response_excluding_reference_manger_sources(
                    history=self._loop_history,
                    chunks_handler=self.agent_chunks_handler,
                    source_offset=self._services.reference_manager_service.chunk_sequence_number,
                    protected_tool_call_ids=self._services.reference_manager_service.tool_call_ids_protected_from_reduction,
                )
            )
        else:
            self._loop_history, self.agent_chunks_handler = (
                reduce_message_length_by_reducing_sources_in_tool_response(
                    history=self._loop_history,
                    chunks_handler=self.agent_chunks_handler,
                )
            )

    

    def _get_documents_uploaded_to_chat(self) -> list[Content]:
        from _common.utils.experimental.chat_history import is_file_content

        chat_contents = self._content_service.search_contents(
            where={
                "ownerId": {
                    "equals": self._event.payload.chat_id,
                },
            },
        )

        content: list[Content] = []
        for c in chat_contents:
            if is_file_content(c.key):
                content.append(c)

        return content



    ############################################################
    ### Prompt generation
    ############################################################

    def _get_system_message_for_plan_execution(
        self,
    ) -> LanguageModelSystemMessage:

        tool_descriptions = [{
               "name":t.display_name,
               "display_name":t.name,
               "tool_description":t.tool_description,
               "tool_format_information_for_system_prompt":t.tool_format_information_for_system_prompt,
               "input_model":t.input_model,
            }
            for t in self._tool_manager.get_tool_prompts()

        ]

        used_tools = [ # replace for for loop in the jinja template and do not do a contains description check dont just get the name filter the tool
            m.name
            for m in self._loop_history
            if isinstance(m, LanguageModelToolMessage)
        ]

        system_prompt_template = jinja2.Template(
            self.unique_ai_config.agent.prompt_config.system_prompt_template
        )

        system_message = system_prompt_template.render(
            model_info=self.unique_ai_config.space.language_model.model_dump(
                mode="json"
            ),
            date_string=datetime.now().strftime("%A %B %d, %Y"),
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            project_name=self.unique_ai_config.space.project_name,
            custom_instructions=self.unique_ai_config.space.custom_instructions,
            max_tools_per_iteration=self._config.loop_configuration.max_tool_calls_per_iteration,
            max_loop_iterations=self._config.max_loop_iterations,
            current_iteration=self.current_iteration_index + 1,
            files_uploaded= len(self.chat_uploaded_files) > 0,
        )

        system_message = LanguageModelSystemMessage(content=system_message)

        return system_message
