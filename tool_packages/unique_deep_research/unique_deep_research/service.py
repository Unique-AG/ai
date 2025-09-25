from typing import Any, Optional

from openai import Stream
from openai.types.responses import ResponseFunctionWebSearch, ResponseReasoningItem
from openai.types.responses.response_function_web_search import (
    ActionOpenPage,
    ActionSearch,
)
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_refusal import ResponseOutputRefusal
from openai.types.responses.response_output_text import (
    Annotation,
    AnnotationURLCitation,
)
from openai.types.responses.response_stream_event import ResponseStreamEvent
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import (
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

from .config import (
    RESPONSES_API_TIMEOUT_SECONDS,
    TEMPLATE_ENV,
    DeepResearchEngine,
    DeepResearchToolConfig,
)
from .markdown_utils import postprocess_research_result_with_chunks
from .unique_custom.utils import (
    cleanup_request_counter,
    create_message_log_entry,
    get_next_message_order,
)


class DeepResearchToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Dummy field to be able to use the tool
    start_research: bool = Field(
        description="Whether to start research",
        default=False,
    )


class DeepResearchToolResponse(ToolCallResponse):
    content: str | None = None


class MemorySchema(BaseModel):
    message_id: str


class DeepResearchTool(Tool[DeepResearchToolConfig]):
    """
    Deep Research Tool for complex, multi-source research tasks.

    This tool performs in-depth research by:
    - Clarifying user intent through interactive questions when needed
    - Generating comprehensive research briefs
    - Conducting research using the configured engine
    - Synthesizing information with proper citations

    Note: This tool is designed for forced invocation and writes directly to the message log.
    Output should not be post-processed as it includes formatted citations and references.
    """

    name = "DeepResearch"

    def __init__(
        self,
        configuration: DeepResearchToolConfig,
        event: ChatEvent,
        tool_progress_reporter,
    ):
        super().__init__(configuration, event, tool_progress_reporter)
        self.chat_id = event.payload.chat_id
        self.company_id = event.company_id
        self.user_id = event.user_id

        self.client = get_openai_client()
        self.logger.info(f"Using OpenAI client pointed to {self.client.base_url}")

        self.content_service = ContentService(
            company_id=self.company_id, user_id=self.user_id
        )
        self.memory_service = PersistentShortMemoryManager(
            short_term_memory_service=ShortTermMemoryService(
                company_id=self.company_id,
                user_id=self.user_id,
                chat_id=self.chat_id,
                message_id=None,
            ),
            short_term_memory_schema=MemorySchema,
            short_term_memory_name="deep_research:followup_question_message_id",
        )
        self.env = TEMPLATE_ENV
        self.execution_id = event.payload.message_execution_id

    def takes_control(self) -> bool:
        """
        This tool requires taking control of the conversation from the orchestrator.
        The DeepResearch tool performs complex, multi-step research tasks that involve
        clarifying user intent, generating research briefs, and synthesizing information.
        To ensure the research process is uninterrupted and properly managed, it needs
        to take control of the conversation flow.
        """
        return True

    def is_message_execution(self) -> bool:
        """
        Check if the execution id is valid.
        """
        return self.execution_id is not None

    async def get_followup_question_message_id(self) -> str | None:
        """
        Get the follow-up question message id.
        """

        result = await self.memory_service.load_async()
        if not result:
            return None
        return result.message_id

    async def is_followup_question_answer(self) -> bool:
        """
        Check if the message is a follow-up question answer.
        """
        followup_question_message_id = await self.get_followup_question_message_id()
        if not followup_question_message_id:
            return False
        history = await self.chat_service.get_full_history_async()
        if history and history[-1].id == followup_question_message_id:
            return True
        return False

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description="Use this tool for complex research tasks that require deep investigation",
            parameters=DeepResearchToolInput,
        )

    def tool_description_for_system_prompt(self) -> str:
        return (
            "The DeepResearch tool is for complex research tasks that require:\n"
            "- In-depth investigation across multiple sources\n"
            "- Synthesis of information from various perspectives\n"
            "- Comprehensive analysis with citations\n"
            "- Detailed reports on specific topics\n\n"
        )

    def tool_format_information_for_system_prompt(self) -> str:
        return ""

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return [EvaluationMetricName.HALLUCINATION]

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        evaluation_check_list = self.evaluation_check_list()

        # Check if the tool response is empty
        if not tool_response.content_chunks:
            return []
        return evaluation_check_list

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        self.logger.info("Starting Deep Research tool run")

        # Question answer and message execution will have the same message id, so we need to check if it is a message execution
        if await self.is_followup_question_answer() and not self.is_message_execution():
            self.logger.info("This is a follow-up question answer")
            # TODO: Should we also write a message to the user?
            self.write_message_log_text_message("Waiting for deep research to start...")
            self.chat_service.create_message_execution(
                message_id=self.event.payload.assistant_message.id,
                type=MessageExecutionType.DEEP_RESEARCH,
            )
            return DeepResearchToolResponse(
                id=tool_call.id or "",
                name=self.name,
                content="",
            )
        if self.is_message_execution():
            self.logger.info("Starting research")
            # Run research
            self.write_message_log_text_message("Generating research plan...")
            research_brief = self.generate_research_brief_from_dict(
                self.get_history_messages_for_research_brief()
            )
            processed_result, content_chunks = await self.run_research(research_brief)

            # Handle success/failure status updates centrally
            if not processed_result:
                await self._update_execution_status(MessageExecutionUpdateStatus.FAILED)
                await self.chat_service.modify_assistant_message_async(
                    content="Deep Research failed to complete for an unknown reason",
                )
                self.write_message_log_text_message(
                    "Research failed for an unknown reason"
                )
                return DeepResearchToolResponse(
                    id=tool_call.id or "",
                    name=self.name,
                    content=processed_result or "Failed to complete research",
                    error_message="Research process failed or returned empty results",
                )

            await self._update_execution_status(MessageExecutionUpdateStatus.COMPLETED)

            # Return the results
            return DeepResearchToolResponse(
                id=tool_call.id or "",
                name=self.name,
                content=processed_result,
                content_chunks=content_chunks,
            )

        # Ask followup questions
        followup_question_message = await self.clarify_user_request()
        # put message in short term memory to remember that we asked the followup questions
        await self.memory_service.save_async(
            MemorySchema(message_id=self.event.payload.assistant_message.id),
        )
        return DeepResearchToolResponse(
            id=tool_call.id or "",
            name=self.name,
            content=followup_question_message,
        )

    async def _update_execution_status(
        self, status: MessageExecutionUpdateStatus, percentage: Optional[int] = None
    ) -> None:
        """
        Centralized method to update message execution status.

        Args:
            status: The execution status to set
            percentage: Optional completion percentage (defaults based on status)
        """
        if percentage is None:
            percentage = 100 if status == MessageExecutionUpdateStatus.COMPLETED else 0

        await self.chat_service.update_message_execution_async(
            message_id=self.event.payload.assistant_message.id,
            status=status,
            percentage_completed=percentage,
        )

    def write_message_log_text_message(self, text: str):
        create_message_log_entry(
            self.chat_service,
            self.event.payload.assistant_message.id,
            text,
            MessageLogStatus.COMPLETED,
            details=MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=[]),
        )

    def get_history_messages_for_research_brief(self) -> list[dict[str, str]]:
        """
        Get the history messages for the research brief.
        """
        history = self.chat_service.get_full_history()
        history_messages = []
        # Take last user and assistant message pair (assuming it's the clarifying question and answer)
        for msg in history[-4:]:
            if msg.role == "user" or msg.role == "assistant":
                history_messages.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content or "",
                    }
                )
        history_messages.append(
            {
                "role": "user",
                "content": self.get_user_request(),
            }
        )
        return history_messages

    async def run_research(self, research_brief: str) -> tuple[str, list[Any]]:
        """
        Run the research using the configured strategy.
        Returns a tuple of (processed_result, content_chunks)
        """
        try:
            match self.config.engine:
                case DeepResearchEngine.OPENAI:
                    self.logger.info("Running OpenAI research")
                    return await self.openai_research(research_brief)
                case DeepResearchEngine.UNIQUE_CUSTOM:
                    self.logger.info("Running Custom research")
                    return await self.custom_research(research_brief)
        except Exception as e:
            self.logger.error(f"Research failed: {e}")
            return "", []

    async def custom_research(self, research_brief: str) -> tuple[str, list[Any]]:
        """
        Run Custom research using LangGraph multi-agent orchestration.
        Returns a tuple of (processed_result, content_chunks)
        """
        from langchain_core.messages import HumanMessage

        from .unique_custom.agents import custom_agent

        try:
            # Initialize LangGraph state with required services
            initial_state = {
                "messages": [HumanMessage(content=research_brief)],
                "research_brief": research_brief,
                "notes": [],
                "final_report": "",
                "chat_service": self.chat_service,
                "message_id": self.event.payload.assistant_message.id,
                "tool_progress_reporter": self.tool_progress_reporter,
            }

            # Prepare configuration for LangGraph
            config = {
                "configurable": {
                    "engine_config": self.config,
                    "openai_client": self.client,
                    "chat_service": self.chat_service,
                    "content_service": self.content_service,
                    "message_id": self.event.payload.assistant_message.id,
                }
            }

            result = await custom_agent.ainvoke(initial_state, config=config)  # type: ignore[arg-type]

            cleanup_request_counter(self.event.payload.assistant_message.id)

            # Extract final report and content chunks
            research_result = result.get("final_report", "")
            # Postprocess research result to extract links, create references and chunks
            processed_result, annotations, content_chunks = (
                postprocess_research_result_with_chunks(
                    research_result, tool_call_id="", message_id=""
                )
            )
            self.write_message_log_text_message("Research completed successfully")

            # Update the assistant message with the results
            await self.chat_service.modify_assistant_message_async(
                content=processed_result,
                references=annotations,
                set_completed_at=True,
            )
            self.logger.info("Custom research completed successfully")
            return processed_result, content_chunks

        except Exception as e:
            error_msg = f"Custom research failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return error_msg, []

    async def openai_research(self, research_brief: str) -> tuple[str, list[Any]]:
        """
        Run OpenAI-specific research.
        Returns a tuple of (processed_result, content_chunks)
        """
        stream = self.client.responses.create(
            timeout=RESPONSES_API_TIMEOUT_SECONDS,
            model=self.config.research_model.name,
            input=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self.env.get_template(
                                "openai/oai_research_system_message.j2"
                            ).render(),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": research_brief,
                        }
                    ],
                },
            ],
            reasoning={"summary": "auto"},
            tools=[
                {"type": "web_search_preview"},
            ],
            stream=True,
        )

        # Process the stream
        research_result, annotations = self._process_research_stream(stream)

        # Postprocess research result to extract links, create references and chunks
        processed_result, _, content_chunks = postprocess_research_result_with_chunks(
            research_result, tool_call_id="", message_id=""
        )
        # Beautify the report
        processed_result = await self._postprocess_report_with_gpt(processed_result)

        # Convert OpenAI annotations to link references
        link_references = self._convert_annotations_to_references(
            annotations or [], message_id=""
        )
        self.write_message_log_text_message("Research completed successfully")

        # Update the assistant message with the results
        await self.chat_service.modify_assistant_message_async(
            content=processed_result,
            references=link_references,
            set_completed_at=True,
        )

        return processed_result, content_chunks

    def _process_research_stream(
        self, stream: Stream[ResponseStreamEvent]
    ) -> tuple[str, list[Annotation]]:
        """
        Process the OpenAI Realtime API stream and extract the final report.

        Args:
            stream: Stream of ResponseStreamEvent objects from OpenAI Realtime API

        Returns:
            Tuple of (report_text, annotations)
        """
        # This index will have gaps on order in the database as we don't track all events
        # Sorted it will give the correct order of the logs
        for event in stream:
            match event.type:
                case "response.completed":
                    # Extract the final output with annotations
                    if event.response.output and len(event.response.output) > 0:
                        final_output = event.response.output[-1]
                        if not isinstance(final_output, ResponseOutputMessage):
                            self.logger.warning(
                                f"Unexpected output type: {type(final_output)}"
                            )
                            continue
                        content_item = final_output.content[0]

                        # Refusal
                        if isinstance(content_item, ResponseOutputRefusal):
                            return content_item.refusal, []

                        # Extract final report and references
                        report_text = content_item.text
                        annotations = content_item.annotations or []
                        return report_text, annotations
                    return event.response.output_text or "", []
                case "response.incomplete":
                    if event.response.incomplete_details:
                        return (
                            event.response.incomplete_details.reason
                            or "Incomplete due to unknown reason",
                            [],
                        )
                case "response.output_item.done":
                    # This is where we handle the output items and send to frontend
                    if isinstance(event.item, ResponseReasoningItem):
                        for summary in event.item.summary:
                            self.chat_service.create_message_log(
                                message_id=self.event.payload.assistant_message.id,
                                text=summary.text,
                                status=MessageLogStatus.COMPLETED,
                                order=get_next_message_order(
                                    self.event.payload.assistant_message.id
                                ),
                                uncited_references=MessageLogUncitedReferences(
                                    data=[],
                                ),
                                details=MessageLogDetails(
                                    data=[],
                                ),
                            )
                    elif isinstance(event.item, ResponseFunctionWebSearch):
                        if isinstance(event.item.action, ActionSearch) and isinstance(
                            event.item.action.query, str
                        ):
                            self.chat_service.create_message_log(
                                message_id=self.event.payload.assistant_message.id,
                                text="Searching the web",
                                status=MessageLogStatus.COMPLETED,
                                order=get_next_message_order(
                                    self.event.payload.assistant_message.id
                                ),
                                uncited_references=MessageLogUncitedReferences(
                                    data=[],
                                ),
                                details=MessageLogDetails(
                                    data=[
                                        MessageLogEvent(
                                            type="WebSearch",
                                            text=event.item.action.query,
                                        )
                                    ],
                                ),
                            )
                        elif isinstance(event.item.action, ActionOpenPage):
                            self.chat_service.create_message_log(
                                message_id=self.event.payload.assistant_message.id,
                                text="Reviewing Web Sources",
                                status=MessageLogStatus.COMPLETED,
                                order=get_next_message_order(
                                    self.event.payload.assistant_message.id
                                ),
                                uncited_references=MessageLogUncitedReferences(
                                    data=[
                                        ContentReference(
                                            name=event.item.action.url,
                                            url=event.item.action.url,
                                            sequence_number=0,
                                            source="deep-research-citations",
                                            source_id=event.item.action.url,
                                        )
                                    ],
                                ),
                                details=MessageLogDetails(
                                    data=[],
                                ),
                            )
                case "response.failed":
                    self.chat_service.create_message_log(
                        message_id=self.event.payload.assistant_message.id,
                        text=f"Failed to complete research: {event.response.error}",
                        status=MessageLogStatus.FAILED,
                        order=get_next_message_order(
                            self.event.payload.assistant_message.id
                        ),
                        uncited_references=MessageLogUncitedReferences(
                            data=[],
                        ),
                        details=MessageLogDetails(
                            data=[],
                        ),
                    )
                    if event.response.error:
                        return event.response.error.message, []

        self.logger.warning("Stream ended without completion")
        return "", []

    async def _postprocess_report_with_gpt(self, research_result: str) -> str:
        """
        Post-process the research report with GPT-4.1 to improve markdown formatting.
        Preserves all sup tags while enhancing the overall formatting and readability.

        Args:
            research_result: The raw research result from OpenAI

        Returns:
            The post-processed research result with improved formatting
        """
        self.write_message_log_text_message("Enhancing report formatting...")

        response = self.client.chat.completions.create(
            model=self.config.large_model.name,
            messages=[
                {
                    "role": "system",
                    "content": self.env.get_template(
                        "openai/report_postprocessing_system.j2"
                    ).render(),
                },
                {
                    "role": "user",
                    "content": f"Please improve the markdown formatting of this research report:\n\n{research_result}",
                },
            ],
            temperature=0.1,
            max_tokens=5000,
        )

        formatted_result = response.choices[0].message.content
        if formatted_result:
            self.logger.info("Successfully post-processed research report")
            return formatted_result
        else:
            self.logger.warning("Post-processing returned empty result, using original")
            return research_result

    def get_user_request(self) -> str | None:
        """
        Get the user's request.
        """
        return (
            self.event.payload.user_message.text
            or self.event.payload.user_message.original_text
            or ""
        )

    async def clarify_user_request(self) -> str:
        """
        Clarify the user's request.
        """
        # # Get user query
        last_two_interactions = self.get_history_messages_for_research_brief()

        # Step 1: Generate clarifying questions
        messages = [
            {
                "role": "system",
                "content": self.env.get_template("clarifying_agent.j2").render(),
            },
            *last_two_interactions,
        ]
        response = await self.chat_service.complete_async(
            messages=messages,
            model_name=self.config.small_model.name,
            content_chunks=None,
        )
        assert isinstance(response.choices[0].message.content, str), (
            "No clarifying questions generated"
        )
        return response.choices[0].message.content

    def generate_research_brief_from_dict(self, messages: list[dict[str, str]]) -> str:
        """Generate research brief from dictionary messages."""
        chat_messages: list[Any] = [
            {
                "role": "system",
                "content": self.env.get_template(
                    "research_instructions_agent.j2"
                ).render(),
            }
        ] + messages

        research_response = self.client.chat.completions.create(
            model=self.config.research_model.name,
            messages=chat_messages,
            temperature=0.1,
        )

        research_instructions = research_response.choices[0].message.content
        assert research_instructions, "No research instructions generated"
        return research_instructions

    def generate_research_brief(
        self, messages: list[LanguageModelMessage]
    ) -> str | None:
        """Generate research brief from LanguageModelMessage objects."""
        # Convert to dict format and use the other method
        dict_messages = []
        for message in messages:
            if message.content:
                dict_messages.append(
                    {
                        "role": message.role.value
                        if hasattr(message.role, "value")
                        else str(message.role),
                        "content": message.content,
                    }
                )
        return self.generate_research_brief_from_dict(dict_messages)

    def _convert_annotations_to_references(
        self, annotations: list[Annotation], message_id: str | None = None
    ) -> list[ContentReference]:
        """Convert Deep Research annotations to ContentReferences.

        Args:
            annotations: List of annotation objects from Deep Research API
            message_id: Message ID for the references (defaults to empty string for current message)

        Returns:
            List of ContentReference objects
        """
        references = []
        msg_id = message_id or ""

        for i, annotation in enumerate(annotations):
            if not isinstance(annotation, AnnotationURLCitation):
                continue
            # Create ContentReference directly
            reference = ContentReference(
                message_id=msg_id,
                name=annotation.title or f"Deep Research Citation {i + 1}",
                sequence_number=i + 1,
                source="deep-research-citations",
                source_id=annotation.url,
                url=annotation.url,
            )
            references.append(reference)

        return references

    def get_tool_call_result_for_loop_history(
        self,
        tool_response: DeepResearchToolResponse,
        agent_chunks_handler=None,
    ) -> LanguageModelMessage:
        """
        Process the results of the tool.

        Args:
            tool_response: The tool response.
            loop_history: The loop history.

        Returns:
            The tool result to append to the loop history.
        """
        self.logger.debug(
            f"Appending tool call result to history: {tool_response.name}"
        )
        # Give final report to the user
        # ensure chunks are passed back to the user

        # Append the result to the history
        return LanguageModelToolMessage(
            content=tool_response.content,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )


# Register the tool with the ToolFactory
ToolFactory.register_tool(DeepResearchTool, DeepResearchToolConfig)
