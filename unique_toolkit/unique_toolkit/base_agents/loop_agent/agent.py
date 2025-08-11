
from abc import ABC, abstractmethod
import logging

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.service import LanguageModelService
from unique_toolkit.unique_toolkit.base_agents.loop_agent.config import LoopAgentConfig
from unique_toolkit.unique_toolkit.base_agents.loop_agent.helpers import get_history 
from unique_toolkit.unique_toolkit.base_agents.loop_agent.history_manager.history_manager import HistoryManager, HistoryManagerConfig
from unique_toolkit.unique_toolkit.base_agents.loop_agent.schemas import  DebugInfoManager
from unique_toolkit.unique_toolkit.base_agents.loop_agent.thinking_manager import ThinkingManager, ThinkingManagerConfig
from unique_toolkit.unique_toolkit.evaluators.schemas import EvaluationMetricName
from unique_toolkit.unique_toolkit.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.unique_toolkit.tools.agent_chunks_handler import AgentChunksHandler
from unique_toolkit.unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.unique_toolkit.tools.tool import Tool
from unique_toolkit.unique_toolkit.tools.tool_manager import ToolManager, ToolManagerConfig
from unique_toolkit.unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter




logger = logging.getLogger(__name__)

class LoopAgent(ABC):
    def __init__(
        self,
        event: ChatEvent,
        config: LoopAgentConfig,
        agent_chunks_handler: AgentChunksHandler,
    ):
        self.agent_chunks_handler = agent_chunks_handler # deprecated, use reference_manager instead
        self.logger = logger
        self.event = event
        self.config = config
        self.chat_service = ChatService(event)
        self.content_service = ContentService.from_event(event)
        self.llm_service = LanguageModelService.from_event(event)
            
        self.debug_info_manager = DebugInfoManager()
        self.reference_manager = ReferenceManager()
        self.tool_progress_reporter = ToolProgressReporter(
            chat_service=self.chat_service
        )

        thinkingManagerConfig = ThinkingManagerConfig()

        self.thinking_manager= ThinkingManager(
            logger=self.logger,
            config = thinkingManagerConfig,
            tool_progress_reporter=self.tool_progress_reporter,
            chat_service=self.chat_service
        )

        toolConfig = ToolManagerConfig(
            tools = config.tools, 
            max_tool_calls=self.config.loop_configuration.max_tool_calls_per_iteration
        )

        self.tool_manager = ToolManager(
            logger=self.logger,
            config=toolConfig,
            event=self.event,
            tool_progress_reporter=self.tool_progress_reporter,
        )

        history_manager_config = HistoryManagerConfig(
            full_sources_serialize_dump=False # this used to come from the tools but makes no sense, as it should alway be the same for all of them
        )

        self.history_manager = HistoryManager(
            logger,
            history_manager_config,
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
        self.logger.info("Start LoopAgent...")

        self.history = await self._obtain_chat_history_as_llm_messages()
        if self.history_manager.has_no_loop_messages():
            self.chat_service.modify_assistant_message(
                content="Starting agentic loop..."
            )

        ## Loop iteration
        for i in range(self.config.max_loop_iterations):
            self.current_iteration_index = i
            self.logger.info(f"Starting iteration {i + 1}...")

            # Plan execution
            loop_response = await self._plan_or_execute()
            self.logger.info("Done with _plan_or_execute")

            # Update tool progress reporter
            self.thinking_manager.update_tool_progress_reporter(loop_response)
            
            # Execute the plan
            exit_loop = await self._process_plan(loop_response)
            self.logger.info("Done with _process_plan")

            if exit_loop:
                self.thinking_manager.close_thinking_steps(loop_response)
                self.logger.info("Exiting loop.")
                break

            if i == self.config.max_loop_iterations - 1:
                self.logger.error("Max iterations reached.")
                await self.chat_service.modify_assistant_message_async(
                    content="I have reached the maximum number of self-reflection iterations. Please clarify your request and try again...",
                )
                break

            self.start_text = self.thinking_manager.update_start_text(self.start_text,loop_response)
            await self._create_new_assistant_message_if_loop_response_contains_content(loop_response)

        await self.chat_service.modify_assistant_message_async(
            set_completed_at=True,
        )

    async def _plan_or_execute(self) -> LanguageModelStreamResponse:
        """Determine if any tool calls are needed.

        The stream_complete function will return either
        (1) a final response,
        (2) tool calls
        (3) a response with additional tool calls.

        Returns:
            LanguageModelStreamResponse: The response from the stream_complete function
        """
        self.logger.info("Planning or executing the loop.")
        messages = self._compose_message_plan_execution()
        self.logger.info("Done composing message plan execution.")
        stream_response = await self._stream_complete_async_wrapper(
            messages=messages,
            model_name=self.config.language_model.name,
            tools=self.tool_manager.get_tool_definitions(),
            content_chunks=self.reference_manager.get_chunks(),
            start_text=self.start_text,
            debug_info=self.debug_info_manager.get(),
            temperature=self.config.temperature,
            other_options=self.config.additional_llm_options,
        )
        self.reference_manager.add_references(
            references=stream_response.message.references,
        )
        return stream_response

    # @track(name="stream_complete_async_run")
    async def _stream_complete_async_wrapper(self, *args, **kwargs):
        return await self.chat_service.stream_complete_async(*args, **kwargs)

    async def _process_plan(self, loop_response: LanguageModelStreamResponse) -> bool:

        self.logger.info("Processing the plan, executing the tools and checking for loop exit conditions once all is done.")

        is_model_response_empty = self.handle_empty_model_response(loop_response)
        are_no_tools_called = len(loop_response.tool_calls or []) == 0

        if is_model_response_empty:
            self.logger.debug("the was an empty model response. This is bizarre. we exit the loop")
            return True
        elif are_no_tools_called:
            self.logger.debug("No tool calls. we might exit the loop")
            return await self._handle_no_tool_calls(loop_response)
        else:
            self.logger.debug("cool were called we process them and do not exit the loop")
            await self._handle_tool_calls(loop_response)
            return False



    def handle_empty_model_response(
        self,
        language_model_response: LanguageModelStreamResponse,
    ) -> bool:
        if (
            language_model_response.message.original_text
            or language_model_response.tool_calls
        ):
            return False
        
        self.logger.debug(
            "Stream response contains no text and no tool calls."
        )

        message = (
            "⚠️ **The language model was unable to produce an output.**\n"
            "It did not generate any content or perform a tool call in response to your request. "
            "This is a limitation of the language model itself.\n\n"
            "**Please try adapting or simplifying your prompt.** "
            "Rewording your input can often help the model respond successfully."
        )
        self.chat_service.modify_assistant_message(content=message)
        return True


    ##############################
    # Abstract methods
    ##############################
    @abstractmethod
    def _compose_message_plan_execution(self) -> LanguageModelMessages:
        """Composes the message for the plan execution.

        The function will return the messages to be sent to the language model.

        Returns:
            LanguageModelMessages: The messages to be sent to the language model
        """
        raise NotImplementedError()

    @abstractmethod
    async def _handle_no_tool_calls(self,loop_response: LanguageModelStreamResponse) -> bool:
        """Handle the case where no tool calls are returned.

        The function will return True if the loop should exit, False otherwise.
        If the loop should be exited depends on the evaluation checks.

        Returns:
            bool: True if the loop should exit, False otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    async def _handle_tool_calls(self,loop_response: LanguageModelStreamResponse) -> None:
        """Handle the case where tool calls are returned."""
        raise NotImplementedError()

    ##############################
    # Optional methods to override
    ##############################
    async def _obtain_chat_history_as_llm_messages(
        self,
    ) -> list[LanguageModelMessage]:
        return await get_history(
            chat_service=self.chat_service,
            content_service=self.content_service,
            max_history_tokens=self.config.token_limits.max_history_tokens,
            postprocessing_step=self._history_postprocessing_step,
        )

    def _optional_initialization_step(self) -> None:
        """Additional initialization step for the agent."""
        return

    def _history_postprocessing_step(
        self,
        history: list[LanguageModelMessage],
    ) -> list[LanguageModelMessage]:
        """Postprocess the history before performing token reduction."""
        return history

    ##############################
    # Tool processing
    ##############################


    async def _process_tool_calls(
        self,
        tool_calls: list[LanguageModelFunction],
    ) -> None:
        self.logger.info("Processing tool calls")
        """
        Function to process tool calls. The function will first append the tool calls to the history, 
        then create tasks for each tool call and wait until all tasks are finished. Finally, the function 
        will append the tool results to the history.

        Args:
            tool_calls (list): List of tool calls
        """

        # Append function call to history
        self.history_manager._append_tool_calls_to_history(tool_calls)

        # Execute tool calls
        tool_call_responses = await self.tool_manager.execute_selected_tools(tool_calls)

        # Process results with error handling
        self._handle_tool_call_results(tool_call_responses)


    def _handle_tool_call_results(
        self, tool_call_results: list[ToolCallResponse]
    ) -> None:
        self.logger.debug("Handling tool call results")
        self.reference_manager.extract_referenceable_chunks(tool_call_results)
        self.debug_info_manager.extract_tool_debug_info(tool_call_results)
        self.history_manager.add_tool_call_results(tool_call_results)

        for tool_response in tool_call_results:

            # Process tool result
            tool_instance = self.tool_manager.get_tool_by_name(tool_response.name)
            if tool_instance:
                if tool_response.successful:
                    # Update evaluation checks
                    self._update_evaluation_checks(
                        tool_instance, tool_response
                    )
            else:
                self.logger.error(
                    f"Tool instance not found for tool call: {tool_response.name}"
                )


    def _update_evaluation_checks(
        self, tool_instance: Tool, tool_response: ToolCallResponse
    ) -> None:
        """
        Update the list of evaluation checks.

        Args:
            tool_instance (Tool): Tool instance
            tool_response (ToolCallResponse): Tool response
        """
        self.logger.debug("Updating evaluation checks")
        evaluation_checks = (
            tool_instance.get_evaluation_checks_based_on_tool_response(
                tool_response=tool_response
            )
        )

        for check in evaluation_checks:
            if check not in self._tool_evaluation_check_list:
                self._tool_evaluation_check_list.append(check)




    def get_complete_conversation_history_after_streaming_no_tool_calls(
        self,
        loop_response: LanguageModelStreamResponse
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
        complete_history = self.history.copy()

        # Add current user message if not already in history
        current_user_msg = LanguageModelUserMessage(
            content=self.event.payload.user_message.text
        )
        
        if not any(
            msg.role == LanguageModelMessageRole.USER
            and msg.content == current_user_msg.content
            for msg in complete_history
        ):
            complete_history.append(current_user_msg)

        # Add final assistant response - this should be available when this method is called
        if (
            loop_response
            and loop_response.message.text
        ):
            complete_history.append(
                LanguageModelAssistantMessage(
                    content=loop_response.message.text
                )
            )
        else:
            self.logger.warning(
                "Called get_complete_conversation_history_after_streaming_no_tool_calls but no loop_response.message.text is available"
            )

        return complete_history

   

    async def _create_new_assistant_message_if_loop_response_contains_content(
        self,
        loop_response: LanguageModelStreamResponse
    ) -> None:
        if self.thinking_manager.thinking_is_displayed(): 
           return
        if not loop_response.message.text:
          return
        if loop_response.message.text =="" :
            return

        ###
        # ToDo: Once references on existing assistant messages can be deleted, we will switch from creating a new assistant message to modifying the existing one (with previous references deleted)
        ###
        await self.chat_service.create_assistant_message_async(content="")
        self.history_manager.add_assistant_message(
            LanguageModelAssistantMessage(
                content=loop_response.message.original_text
            )
        )
