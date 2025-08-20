from abc import ABC, abstractmethod
import logging


from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelMessages,
    LanguageModelStreamResponse,
)
from unique_toolkit.language_model.service import LanguageModelService
from unique_toolkit.base_agents.loop_agent.config import LoopAgentConfig

from unique_toolkit.base_agents.loop_agent.schemas import (
    DebugInfoManager,
)
from unique_toolkit.base_agents.loop_agent.thinking_manager import (
    ThinkingManager,
    ThinkingManagerConfig,
)
from unique_toolkit.evaluators.schemas import EvaluationMetricName
from unique_toolkit.reference_manager.reference_manager import (
    ReferenceManager,
)
from unique_toolkit.tools.agent_chunks_handler import AgentChunksHandler
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import Tool
from unique_toolkit.tools.tool_manager import (
    ToolManager,
    ToolManagerConfig,
)
from unique_toolkit.tools.tool_progress_reporter import (
    ToolProgressReporter,
)

from evals.evaluation_manager import EvaluationManager
from evals.hallucination.constants import HallucinationConfig
from evals.hallucination.hallucination_evaluation import HallucinationEvaluation
from history_manager.history_manager import HistoryManager, HistoryManagerConfig
from postprocessor.postprocessor_manager import PostprocessorManager



logger = logging.getLogger(__name__)


class LoopAgent(ABC):
    def __init__(
        self,
        event: ChatEvent,
        config: LoopAgentConfig,
        agent_chunks_handler: AgentChunksHandler | None = None,
    ):
        self.agent_chunks_handler = (
            agent_chunks_handler  # deprecated, use reference_manager instead
        )
        self._logger = logger
        self._event = event
        self._config = config
        self._chat_service = ChatService(event)
        self._content_service = ContentService.from_event(event)
        self._llm_service = LanguageModelService.from_event(event)

        self._tool_progress_reporter = ToolProgressReporter(
            chat_service=self._chat_service
        )

        self._debug_info_manager = DebugInfoManager()
        self._reference_manager = ReferenceManager()

        thinkingManagerConfig = ThinkingManagerConfig()

        self._thinking_manager = ThinkingManager(
            logger=self._logger,
            config=thinkingManagerConfig,
            tool_progress_reporter=self._tool_progress_reporter,
            chat_service=self._chat_service,
        )

        toolConfig = ToolManagerConfig(
            tools=config.tools,
            max_tool_calls=self._config.loop_configuration.max_tool_calls_per_iteration,
        )

        self._tool_manager = ToolManager(
            logger=self._logger,
            config=toolConfig,
            event=self._event,
            tool_progress_reporter=self._tool_progress_reporter,
        )

        history_manager_config = HistoryManagerConfig(
            
        )

        self._history_manager = HistoryManager(
            logger,
            event,
            history_manager_config,
            self._config.language_model,
            self._reference_manager,
            
        )

        self._evaluation_manager = EvaluationManager(
            logger=self._logger,
            chat_service=self._chat_service,
            assistant_message_id=event.payload.assistant_message.id,
        )

        self._evaluation_manager.add_evaluation(
            HallucinationEvaluation(
                HallucinationConfig(), event, self._reference_manager
            )
        )
        

        self._postprocessor_manager = PostprocessorManager(
            logger=self._logger,
            chat_service=self._chat_service,
        )



        self._tool_evaluation_check_list: list[EvaluationMetricName] = []

        self._start_text = ""

        self.current_iteration_index = 0

        # Post init
        self._optional_initialization_step()

    @property
    def start_text(self) -> str:
        return self._start_text

    @start_text.setter
    def start_text(self, value: str):
        self._start_text = value

    ##############################
    # Main loop
    ##############################
    # @track(name="loop_agent_run")  # Group traces together
    async def run(self):
        """
        Main loop of the agent. The agent will iterate through the loop, runs the plan and
        processes tool calls if any are returned.
        """
        self._logger.info("Start LoopAgent...")

        if self._history_manager.has_no_loop_messages():
            self._chat_service.modify_assistant_message(
                content="Starting agentic loop..."
            )

        ## Loop iteration
        for i in range(self._config.max_loop_iterations):
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

            if i == self._config.max_loop_iterations - 1:
                self._logger.error("Max iterations reached.")
                await self._chat_service.modify_assistant_message_async(
                    content="I have reached the maximum number of self-reflection iterations. Please clarify your request and try again...",
                )
                break

            self.start_text = self._thinking_manager.update_start_text(
                self.start_text, loop_response
            )
            await self._create_new_assistant_message_if_loop_response_contains_content(
                loop_response
            )

        await self._chat_service.modify_assistant_message_async(
            set_completed_at=True,
        )

    async def _plan_or_execute(self) -> LanguageModelStreamResponse:
        self._logger.info("Planning or executing the loop.")
        messages = await self._compose_message_plan_execution()

        self._logger.info("Done composing message plan execution.")
        stream_response = await self._stream_complete_async_wrapper(
            messages=messages,
            model_name=self._config.language_model.name,
            tools=self._tool_manager.get_tool_definitions(),
            content_chunks=self._reference_manager.get_chunks(),
            start_text=self.start_text,
            debug_info=self._debug_info_manager.get(),
            temperature=self._config.temperature,
            other_options=self._config.additional_llm_options,
        )

        return stream_response

    # @track(name="stream_complete_async_run")
    async def _stream_complete_async_wrapper(self, *args, **kwargs):
        return await self._chat_service.complete_with_references_async(*args, **kwargs)

    async def _process_plan(self, loop_response: LanguageModelStreamResponse) -> bool:
        self._logger.info(
            "Processing the plan, executing the tools and checking for loop exit conditions once all is done."
        )

        if not loop_response.is_empty():
            self._logger.debug("Empty model response, exiting loop.")
            self._chat_service.modify_assistant_message(content=EMPTY_MESSAGE_WARNING)
            return True

        are_no_tools_called = len(loop_response.tool_calls or []) == 0
        if are_no_tools_called:
            self._logger.debug("No tool calls. we might exit the loop")
            return await self._handle_no_tool_calls(loop_response)
       
        self._logger.debug(
            "Tools were called we process them and do not exit the loop"
        )
        await self._handle_tool_calls(loop_response)
        return False

    ##############################
    # Abstract methods
    ##############################
    @abstractmethod
    async def _compose_message_plan_execution(self) -> LanguageModelMessages:
        """Composes the message for the plan execution.

        The function will return the messages to be sent to the language model.

        Returns:
            LanguageModelMessages: The messages to be sent to the language model
        """
        raise NotImplementedError()

    @abstractmethod
    async def _handle_no_tool_calls(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        """Handle the case where no tool calls are returned."""
        selected_evaluation_names = self._tool_manager.get_evaluation_check_list()
        evaluation_results = await self._evaluation_manager.run_evaluations(
            selected_evaluation_names, loop_response
        )

        await self._postprocessor_manager.run_postprocessors(loop_response)

        if not all(result.is_positive for result in evaluation_results):
            self._logger.warning(
                "we should add here the retry counter add an instruction and retry the loop for now we just exit the loop"
            )  # TODO: add retry counter and instruction


        return True

    @abstractmethod
    async def _handle_tool_calls(
        self, loop_response: LanguageModelStreamResponse
    ) -> None:
        """Handle the case where tool calls are returned."""
        self._logger.info("Processing tool calls")

        tool_calls = loop_response.tool_calls or []
        
        # Append function call to history
        self._history_manager._append_tool_calls_to_history(tool_calls)

        # Execute tool calls
        tool_call_responses = await self._tool_manager.execute_selected_tools(
            tool_calls
        )

        # Process results with error handling
        self._reference_manager.extract_referenceable_chunks(tool_call_responses)
        self._debug_info_manager.extract_tool_debug_info(tool_call_responses)
        self._history_manager.add_tool_call_results(tool_call_responses)

    ##############################
    # Optional methods to override
    ##############################

    @deprecated(
        "This method is deprecated and will be removed in the future, use _create_new_assistant_message_if_loop_response_contains_content instead."
    )
    async def _process_tool_calls(
        self, tool_calls: list[LanguageModelFunction], ay
    ) -> None:
        pass

    async def _create_new_assistant_message_if_loop_response_contains_content(
        self, loop_response: LanguageModelStreamResponse
    ) -> None:
        if self._thinking_manager.thinking_is_displayed():
            return
        if not loop_response.message.text:
            return
        if loop_response.message.text == "":
            return

        ###
        # ToDo: Once references on existing assistant messages can be deleted, we will switch from creating a new assistant message to modifying the existing one (with previous references deleted)
        ###
        await self._chat_service.create_assistant_message_async(content="")
        self._history_manager.add_assistant_message(
            LanguageModelAssistantMessage(content=loop_response.message.original_text)
        )

    ###############################
    # deprecated methods
    ###############################

    @deprecated(
        "This method is deprecated and will be removed in the future, useself.history_manager in the future."
    )
    async def get_complete_conversation_history_after_streaming_no_tool_calls(
        self,
    ) -> list[LanguageModelMessage]:
        """
        Get the complete conversation history including the current user message and the final
        assistant response after streaming has completed with no tool calls.

        This method should only be called after streaming is complete and when no tool calls
        were made in the final iteration.

        Returns:
            list[LanguageModelMessage]: The complete conversation history with the current
            user message and final assistant response appended.
        """
        return await self._history_manager.get_history(
            self._history_postprocessing_step
        )

    @deprecated(
        "use the history_manager to obtain the history",
    )
    async def _obtain_chat_history_as_llm_messages(
        self,
    ) -> list[LanguageModelMessage]:
        return await self._history_manager.get_history(
            self._history_postprocessing_step
        )

    @deprecated(
        "This method is deprecated and will be removed in the future, use constructor instead with super.",
    )
    def _optional_initialization_step(self) -> None:
        """Additional initialization step for the agent."""
        return

    @deprecated(
        "This method is deprecated and will be removed in the future, use _history_postprocessing_step instead with super.",
    )
    def _history_postprocessing_step(
        self,
        history: list[LanguageModelMessage],
    ) -> list[LanguageModelMessage]:
        """Postprocess the history before performing token reduction."""
        return history
