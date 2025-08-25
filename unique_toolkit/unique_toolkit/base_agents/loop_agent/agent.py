from abc import ABC, abstractmethod
from datetime import datetime
import logging
from warnings import deprecated


import jinja2
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelSystemMessage,
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
from unique_toolkit.tools.mcp.manager import MCPManager

from unique_toolkit.evals.evaluation_manager import EvaluationManager
from unique_toolkit.evals.hallucination.constants import HallucinationConfig
from unique_toolkit.evals.hallucination.hallucination_evaluation import HallucinationEvaluation
from unique_toolkit.history_manager.history_manager import HistoryManager, HistoryManagerConfig
from unique_toolkit.postprocessor.postprocessor_manager import PostprocessorManager



logger = logging.getLogger(__name__)


EMPTY_MESSAGE_WARNING = (
            "⚠️ **The language model was unable to produce an output.**\n"
            "It did not generate any content or perform a tool call in response to your request. "
            "This is a limitation of the language model itself.\n\n"
            "**Please try adapting or simplifying your prompt.** "
            "Rewording your input can often help the model respond successfully."
        )

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

        self._mcp_manager = MCPManager(
            mcp_servers=self._event.payload.mcp_servers,
            event=self._event,
            tool_progress_reporter=self._tool_progress_reporter,
        )
        self._tool_manager = ToolManager(
            logger=self._logger,
            config=toolConfig,
            event=self._event,
            tool_progress_reporter=self._tool_progress_reporter,
            mcp_manager=self._mcp_manager,
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

        # Forces tool calls only in first iteration
        if (
            len(self._tool_manager.get_forced_tools()) > 0
            and self.current_iteration_index == 0
        ):
            responses = [
                await self._chat_service.complete_with_references_async(
                    messages=messages,
                    model_name=self._config.language_model.name,
                    tools=self._tool_manager.get_tool_definitions(),
                    content_chunks=self._reference_manager.get_chunks(),
                    start_text=self.start_text,
                    debug_info=self._debug_info_manager.get(),
                    temperature=self._config.agent.experimental.temperature,
                    other_options=self._config.agent.experimental.additional_llm_options
                    | {"toolChoice": opt},
                )
                for opt in self._tool_manager.get_forced_tools()
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
            == self._config.agent.max_loop_iterations - 1
        ):
            # No tool calls in last iteration
            stream_response = await self._chat_service.complete_with_references_async(
                messages=messages,
                model_name=self._config.language_model.name,
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self._config.agent.experimental.temperature,
                other_options=self._config.agent.experimental.additional_llm_options,
            )

        else:
            stream_response = await self._chat_service.complete_with_references_async(
                messages=messages,
                model_name=self._config.language_model.name,
                tools=self._tool_manager.get_tool_definitions(),
                content_chunks=self._reference_manager.get_chunks(),
                start_text=self.start_text,
                debug_info=self._debug_info_manager.get(),
                temperature=self._config.agent.experimental.temperature,
                other_options=self._config.agent.experimental.additional_llm_options,
            )

        return stream_response


    async def _process_plan(self, loop_response: LanguageModelStreamResponse) -> bool:
        self._logger.info(
            "Processing the plan, executing the tools and checking for loop exit conditions once all is done."
        )

        if not loop_response.is_empty():
            self._logger.debug("Empty model response, exiting loop.")
            self._chat_service.modify_assistant_message(content=EMPTY_MESSAGE_WARNING)
            return True

        call_tools = len(loop_response.tool_calls or []) > 0
        if call_tools:
            self._logger.debug("Tools were called we process them and do not exit the loop")
            await self._handle_tool_calls(loop_response)
            return False
        
        self._logger.debug("No tool calls. we might exit the loop")    
    
        return await self._handle_no_tool_calls(loop_response)

    ##############################
    # Abstract methods
    ##############################

    async def _compose_message_plan_execution(self) -> LanguageModelMessages:
        
        original_user_message = self._event.payload.user_message.text
        rendered_user_message_string = await self._render_user_prompt()
        rendered_system_message_string = await self._render_system_prompt()

        o = await self._history_manager.get_history_for_model_call(
            original_user_message,
            rendered_user_message_string,
            rendered_system_message_string,
            self._postprocessor_manager.remove_from_text,
        )
        return o


    async def _render_user_prompt(self) -> str:
        user_message_template = jinja2.Template(
            self._config.agent.prompt_config.user_message_prompt_template
        )

        query = self._event.payload.user_message.text
        user_msg = user_message_template.render(
            query=query,
        )
        return user_msg


    async def _render_system_prompt(
        self,
    ) -> str:
        # TODO: Collect tool information here and adapt to system prompt
        tool_descriptions = self._tool_manager.get_tool_prompts()

        used_tools = [m.name for m in self._tool_manager.get_tools()]


        system_prompt_template = jinja2.Template(
            self._config.agent.prompt_config.system_prompt_template
        )

        date_string = datetime.now().strftime("%A %B %d, %Y")

        system_message = system_prompt_template.render(
            model_info=self._config.agent.space.language_model.model_dump(
                mode="json"
            ),
            date_string=date_string,
            tool_descriptions=tool_descriptions,
            used_tools=used_tools,
            project_name=self._config.agent.space.project_name,
            custom_instructions=self._config.agent.space.custom_instructions,
            max_tools_per_iteration=self._config.loop_configuration.max_tool_calls_per_iteration,
            max_loop_iterations=self._config.max_loop_iterations,
            current_iteration=self.current_iteration_index + 1,
            mcp_server_system_prompts=[],
        )
        return system_message


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