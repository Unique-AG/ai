import asyncio
import time
from datetime import datetime, timezone
from logging import Logger
from typing import Any, cast, overload

import jinja2
from typing_extensions import deprecated
from unique_skill_tool.service import SkillTool
from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    AnalyticsLanguageModel,
    DebugInfoManager,
)
from unique_toolkit.agentic.evaluation.evaluation_manager import EvaluationManager
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.history_manager.utils import (
    get_selected_uploaded_content_ids,
)
from unique_toolkit.agentic.loop_runner import (
    LoopIterationRunner,
    ResponsesLoopIterationRunner,
    SupportsInvocationStats,
)
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    PostprocessorManager,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.thinking_manager.thinking_manager import ThinkingManager
from unique_toolkit.agentic.tools.experimental.open_file_tool import (
    OpenFileToolRuntime,
    OpenFileToolRuntimeConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter import (
    DisplayCodeInterpreterFilesPostProcessor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    ArtifactsDebugInfo,
)
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    SafeTaskExecutor,
    ToolManager,
)
from unique_toolkit.app.schemas import ChatEvent, McpServer, SkillReference
from unique_toolkit.chat.cancellation import CancellationEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelAssistantMessage
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelStreamResponse,
    ResponsesLanguageModelStreamResponse,
)
from unique_toolkit.protocols.support import (
    ResponsesSupportCompleteWithReferences,
    SupportCompleteWithReferences,
)
from unique_user_memory.user_memory_postprocessor import UserMemoryPostprocessor

from unique_orchestrator._builders.inject_tool_reminders import (
    inject_tool_reminders_into_user_message,
)
from unique_orchestrator._builders.skill_setup import preload_invoked_skills
from unique_orchestrator.config import UniqueAIConfig
from unique_orchestrator.settings import env_settings
from unique_orchestrator.utils import resolve_other_options


def _load_invocation_stats_from_debug_info(
    debug_info: dict[str, Any],
    logger: Logger,
) -> list[LanguageModelInvocationStats]:
    """Deserialize previously persisted invocation stats, ignoring malformed entries."""
    raw_invocations = debug_info.get("llm_invocations")
    if not isinstance(raw_invocations, list):
        return []

    invocations: list[LanguageModelInvocationStats] = []
    for raw_invocation in raw_invocations:
        try:
            invocations.append(
                LanguageModelInvocationStats.model_validate(raw_invocation)
            )
        except Exception:
            logger.warning(
                "Ignoring malformed persisted LLM invocation stats",
                exc_info=True,
            )
    return invocations


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
        agent_file_registry: list[str] | None = None,
        uploaded_documents: list[Content] | None = None,
        user_memory_text: str = "",
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
        agent_file_registry: list[str] | None = None,
        uploaded_documents: list[Content] | None = None,
        user_memory_text: str = "",
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
        uploaded_documents: list[Content] | None = None,
        user_memory_text: str = "",
    ) -> None:
        self._logger = logger
        self._event = event
        self._config = config
        self._chat_service = chat_service
        self._content_service = content_service
        self._uploaded_documents = uploaded_documents or []
        self._user_memory_text = user_memory_text
        self._skill_choices: list[SkillReference] = getattr(
            event.payload, "skill_choices", []
        )

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
        if self._config.agent.experimental.open_file_tool_config.enabled:
            self._agent_file_registry: list[str] = (
                agent_file_registry if agent_file_registry is not None else []
            )
            file_cfg = self._config.agent.experimental.open_file_tool_config
            selected_ids = get_selected_uploaded_content_ids(event)
            self._open_file_runtime = OpenFileToolRuntime(
                logger=logger,
                config=OpenFileToolRuntimeConfig(
                    enabled=file_cfg.enabled,
                    send_files_in_payload=file_cfg.send_files_in_payload,
                    send_uploaded_files_in_payload=file_cfg.send_uploaded_files_in_payload,
                    use_responses_api=(
                        self._config.agent.experimental.responses_api_config.use_responses_api
                        or self._config.agent.experimental.use_responses_api
                    ),
                    selected_content_ids=(
                        frozenset(selected_ids) if selected_ids is not None else None
                    ),
                ),
                content_service=content_service,
                tool_manager=tool_manager,
                message_step_logger=message_step_logger,
                agent_file_registry=self._agent_file_registry,
            )
        self._file_fallback_occurred = False
        # Helper variable to support control loop
        self._tool_took_control = False
        self._loop_iteration_runner = loop_iteration_runner
        self._last_assistant_text: str | None = None

        self._execution_times: list[dict[str, Any]] = []
        self._current_loop_timing: dict[str, Any] = {}
        self._loop_debug_params: list[dict[str, Any]] = []
        self._generated_files_info: ArtifactsDebugInfo | None = None
        # None when the user-memory postprocessor is not activated for this turn;
        # True/False when it ran and did/didn't update the stored memory profile.
        self._context_memory_updated: bool | None = None
        self._invocation_stats: list[LanguageModelInvocationStats] = []
        self._invocation_stats_finalized = False

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
            await self._chat_service.modify_assistant_message_async(
                content="Starting agentic loop..."  # TODO: this must be more informative
            )

        self._execution_times = []
        self._loop_debug_params = []
        # Reset per-run artifact analytics too: a later run that exits without
        # reaching _handle_no_tool_calls (tool takes control / empty response /
        # cancellation) must not report the previous run's artifacts.
        self._generated_files_info = None
        self._context_memory_updated = None
        # Pending pre-run usage (e.g. the user-memory load-time condense call)
        # must be captured unconditionally, before it's known whether this
        # turn will even reach postprocessors -- otherwise a turn that exits
        # early (cancellation, empty response, control-taking tool) drops it.
        self._invocation_stats = (
            self._postprocessor_manager.take_pending_invocation_stats()
        )
        self._invocation_stats_finalized = False
        self._debug_info_manager.add("llm_invocations_complete", False)
        invocations_persisted = False
        persisted_invocations_merged = False
        run_start = time.perf_counter()

        await preload_invoked_skills(
            tool_manager=self._tool_manager,
            history_manager=self._history_manager,
            logger=self._logger,
            skill_choices=self._skill_choices,
        )

        sub = self._chat_service.cancellation.on_cancellation.subscribe(
            self._on_cancellation
        )
        try:
            max_iterations = self._config.effective_max_loop_iterations
            for i in range(max_iterations):
                if await self._chat_service.cancellation.check_cancellation_async():
                    break

                self.current_iteration_index = i
                self._logger.info(f"Starting iteration {i + 1}...")

                loop_start = time.perf_counter()
                self._current_loop_timing = {
                    "iteration": i + 1,
                    "tool_execution": {},
                    "post_processing": {},
                    "evaluation": {},
                }

                planning_start = time.perf_counter()
                loop_response = await self._plan_or_execute()
                self._current_loop_timing["planning_or_streaming"] = round(
                    time.perf_counter() - planning_start, 3
                )
                self._logger.info("Done with _plan_or_execute")
                if loop_response.usage is not None:
                    self._invocation_stats.append(
                        LanguageModelInvocationStats.from_usage(
                            self._config.space.language_model.name,
                            loop_response.usage,
                            source=f"main_loop[{i + 1}]",
                        )
                    )
                # TODO(UN-20907): if _plan_or_execute() above raises an exception that
                # propagates out of this loop uncaught, execution never reaches this
                # drain call -- any planning-step usage recorded on the runner this
                # iteration is lost. In practice this is not planning-specific: an
                # uncaught abort here also skips the debug_info["llm_invocations"]
                # write entirely (see the `finally` at the end of run()), so every
                # usage source (main_loop, evaluations, postprocessors) is equally
                # absent from that turn, not just planning. Revisit only if partial
                # debug_info persistence on an aborted run becomes a requirement.
                if isinstance(self._loop_iteration_runner, SupportsInvocationStats):
                    self._invocation_stats.extend(
                        self._loop_iteration_runner.get_invocation_stats()
                    )

                if await self._chat_service.cancellation.check_cancellation_async():
                    self._finalize_loop_timing(loop_start)
                    break

                references = loop_response.message.references or []
                self._reference_manager.add_references(references)
                self._last_assistant_text = (
                    loop_response.message.original_text or loop_response.message.text
                )
                self._logger.info("Done with adding references")

                self._thinking_manager.update_tool_progress_reporter(loop_response)

                if (
                    self._config.agent.experimental.open_file_tool_config.enabled
                    and self._file_fallback_occurred
                ):
                    await self._open_file_runtime.report_file_fallback_step()
                    self._file_fallback_occurred = False

                self._debug_info_manager.extract_builtin_tool_debug_info(
                    loop_response,
                    tool_manager=cast(ToolManager, self._tool_manager),
                    loop_iteration_index=self.current_iteration_index,
                )

                exit_loop = await self._process_plan(loop_response)
                self._logger.info("Done with _process_plan")

                self._finalize_loop_timing(loop_start)

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

            self._debug_info_manager.add(
                "execution_time",
                {
                    "loop_iterations": self._execution_times,
                    "total_time": round(time.perf_counter() - run_start, 3),
                },
            )
            self._debug_info_manager.add("loop_params", self._loop_debug_params)
            skills_debug_info = self._get_activated_skills_debug_info()
            self._debug_info_manager.add("skills", skills_debug_info)
            tool_names = {
                tool["name"] for tool in self._debug_info_manager.get()["tools"]
            }
            existing_debug_info: dict[str, Any] = {}
            if "DeepResearch" in tool_names:
                existing_debug_info = await self._chat_service.get_debug_info_async()
                self._invocation_stats = [
                    *_load_invocation_stats_from_debug_info(
                        existing_debug_info,
                        self._logger,
                    ),
                    *self._invocation_stats,
                ]
                persisted_invocations_merged = True
            self._debug_info_manager.add(
                "llm_invocations",
                [
                    invocation.model_dump(by_alias=True)
                    for invocation in self._invocation_stats
                ],
            )
            reference_sources = {
                ("url", reference.url)
                if reference.url is not None
                else ("source", reference.source, reference.source_id)
                for references in self._reference_manager.get_references()
                for reference in references
            }
            language_model = self._config.space.language_model
            tool_display_names = {
                str(tool.name): tool.display_name() or str(tool.name)
                for tool in self._tool_manager.available_tools
            }

            total_time_to_answer_ms: int | None = None
            if not self._chat_service.cancellation.is_cancelled:
                if self._config.agent.input_token_distribution.enable_tool_call_persistence:
                    await self._persist_tool_calls()
                completed_message = (
                    await self._chat_service.modify_assistant_message_async(
                        set_completed_at=not self._tool_took_control,
                    )
                )
                total_time_to_answer_ms = self._calculate_total_time_to_answer_ms(
                    user_message_created_at=self._event.payload.user_message.created_at,
                    assistant_completed_at=getattr(
                        completed_message, "completed_at", None
                    ),
                )

            self._debug_info_manager.add_analytics(
                skills_debug_info,
                language_model=AnalyticsLanguageModel(
                    name=str(language_model.name),
                    family=str(language_model.family),
                    provider=str(language_model.provider),
                ),
                tool_display_names=tool_display_names,
                references=len(reference_sources),
                user_prompt_length=len(self._event.payload.user_message.text),
                answer_length=len(self._last_assistant_text or ""),
                loop_iteration_count=len(self._execution_times),
                total_time_to_answer_ms=total_time_to_answer_ms,
                artifacts=self._generated_files_info,
                context_memory_updated=self._context_memory_updated,
                invocations=self._invocation_stats,
            )

            # DeepResearch always takes control (see `takes_control()`), so a run
            # that invokes it exits before `_handle_no_tool_calls` and never sets
            # `_invocation_stats_finalized` -- gating on that flag would make this
            # branch unreachable. Its completion signal is instead the message
            # execution callback that runs the actual research (`message_execution_id`
            # set), which is when its merged invocation stats are truly final.
            llm_invocations_complete = (
                self._event.payload.message_execution_id is not None
                if "DeepResearch" in tool_names
                else self._invocation_stats_finalized
            )
            self._debug_info_manager.add(
                "llm_invocations_complete",
                llm_invocations_complete,
            )
            run_debug_info = self._debug_info_manager.get()
            if "DeepResearch" in tool_names:
                debug_info = {
                    **existing_debug_info,
                    "llm_invocations": run_debug_info["llm_invocations"],
                    "llm_invocations_complete": llm_invocations_complete,
                    "analytics": run_debug_info["analytics"],
                }
            else:
                existing_debug_info = await self._chat_service.get_debug_info_async()
                debug_info = {**existing_debug_info, **run_debug_info}
            await self._chat_service.update_debug_info_async(debug_info=debug_info)
            invocations_persisted = True
        finally:
            if not invocations_persisted:
                if isinstance(self._loop_iteration_runner, SupportsInvocationStats):
                    self._invocation_stats.extend(
                        self._loop_iteration_runner.get_invocation_stats()
                    )
                self._debug_info_manager.add(
                    "llm_invocations",
                    [
                        invocation.model_dump(by_alias=True)
                        for invocation in self._invocation_stats
                    ],
                )
                self._debug_info_manager.add("llm_invocations_complete", False)
                try:
                    existing_debug_info = (
                        await self._chat_service.get_debug_info_async()
                    )
                    partial_debug_info = self._debug_info_manager.get()
                    is_deep_research = any(
                        tool.get("name") == "DeepResearch"
                        for tool in partial_debug_info.get("tools", [])
                    )
                    if is_deep_research:
                        if persisted_invocations_merged:
                            merged_invocations = partial_debug_info["llm_invocations"]
                        else:
                            previous_invocations = (
                                _load_invocation_stats_from_debug_info(
                                    existing_debug_info,
                                    self._logger,
                                )
                            )
                            merged_invocations = [
                                *[
                                    invocation.model_dump(by_alias=True)
                                    for invocation in previous_invocations
                                ],
                                *partial_debug_info["llm_invocations"],
                            ]
                        debug_info = {
                            **existing_debug_info,
                            "llm_invocations": merged_invocations,
                            "llm_invocations_complete": False,
                        }
                    else:
                        debug_info = {**existing_debug_info, **partial_debug_info}
                    await self._chat_service.update_debug_info_async(
                        debug_info=debug_info
                    )
                except Exception:
                    self._logger.warning(
                        "Failed to persist partial LLM invocation usage",
                        exc_info=True,
                    )
            sub.cancel()

    @staticmethod
    def _calculate_total_time_to_answer_ms(
        user_message_created_at: str,
        assistant_completed_at: datetime | None,
    ) -> int | None:
        if assistant_completed_at is None:
            return None

        try:
            user_created_at = datetime.fromisoformat(user_message_created_at)
        except (ValueError, TypeError):
            # ValueError: malformed timestamp; TypeError: created_at not a str.
            return None

        if user_created_at.tzinfo is None:
            user_created_at = user_created_at.replace(tzinfo=timezone.utc)
        if assistant_completed_at.tzinfo is None:
            assistant_completed_at = assistant_completed_at.replace(tzinfo=timezone.utc)

        return round((assistant_completed_at - user_created_at).total_seconds() * 1000)

    def _record_loop_debug_params(self, other_options: dict) -> None:
        reasoning_effort = self._resolve_effective_reasoning_effort(other_options)
        thinking_level: str = reasoning_effort or "None"
        self._loop_debug_params.append(
            {
                "loop_number": self.current_iteration_index,
                "thinking_level": thinking_level,
            }
        )
        model_info = self._config.space.language_model
        resolved_temperature, _ = model_info.resolve_temp_and_reasoning(
            self._config.agent.experimental.temperature,
            reasoning_effort=reasoning_effort,
        )
        self._debug_info_manager.add("temperature", resolved_temperature)

    def _resolve_effective_reasoning_effort(self, other_options: dict) -> str | None:
        """Read the reasoning effort from the same source the active LLM API uses.

        Mirrors ``resolve_other_options``: the completions API reads the flat
        ``reasoning_effort`` key, while the responses API prefers the nested
        ``reasoning.effort`` and falls back to the flat key. Keeping this in sync
        ensures the debug temperature matches what is actually sent to the model.
        """
        use_responses_api = (
            self._config.agent.experimental.responses_api_config.use_responses_api
            or self._config.agent.experimental.use_responses_api
        )
        if use_responses_api:
            reasoning = other_options.get("reasoning")
            if isinstance(reasoning, dict) and reasoning.get("effort") is not None:
                return reasoning.get("effort")
        return other_options.get("reasoning_effort")

    def _get_activated_skills_debug_info(self) -> list[dict[str, str | bool]]:
        skill_tool = self._tool_manager.get_tool_by_name(SkillTool.name)
        if not isinstance(skill_tool, SkillTool):
            return []

        forced_content_ids = {
            choice.content_id for choice in self._skill_choices if choice.content_id
        }
        forced_names = {choice.name for choice in self._skill_choices if choice.name}

        skills_debug_info: dict[str, dict[str, str | bool]] = {}
        for skill in skill_tool.activated_skills:
            skills_debug_info.setdefault(
                skill.name,
                {
                    "name": skill.name,
                    "content_id": skill.content_id,
                    "is_forced": (
                        skill.content_id in forced_content_ids
                        if skill.content_id
                        else skill.name in forced_names
                    ),
                },
            )

        return list(skills_debug_info.values())

    # @track()
    async def _plan_or_execute(self) -> LanguageModelStreamResponse:
        self._logger.info("Planning or executing the loop.")
        messages = await self._compose_message_plan_execution()

        self._logger.info("Done composing message plan execution.")

        other_options = resolve_other_options(
            self._config, self._tool_manager, self._logger
        )
        self._record_loop_debug_params(other_options)

        kwargs: dict = dict(
            messages=messages,
            iteration_index=self.current_iteration_index,
            streaming_handler=self._streaming_handler,  # type: ignore (constructor accepts only compatible arguments)
            model=self._config.space.language_model,
            tools=self._tool_manager.get_tool_definitions(),  # type: ignore (as above)
            content_chunks=self._history_manager.get_content_chunks_for_backend(),
            start_text=self.start_text,
            debug_info=self._debug_info_manager.get(),
            temperature=self._config.agent.experimental.temperature,
            tool_choices=self._tool_manager.get_forced_tools(),  # type: ignore (as above)
            other_options=other_options,
        )

        # Experimental Feature UN-17905
        if self._config.agent.experimental.open_file_tool_config.enabled:
            try:
                return await self._loop_iteration_runner(**kwargs)
            except Exception as exc:
                if not self._open_file_runtime.should_retry_without_files(exc):
                    raise
                self._logger.warning(
                    "LLM call failed (likely payload too large). "
                    "Retrying without attached files."
                )
                self._file_fallback_occurred = True
                kwargs["messages"] = self._open_file_runtime.prepare_retry_messages(
                    messages=messages
                )
                kwargs["tools"] = self._tool_manager.get_tool_definitions()  # type: ignore (as above)
                kwargs["tool_choices"] = self._tool_manager.get_forced_tools()  # type: ignore (as above)
                return await self._loop_iteration_runner(**kwargs)

        return await self._loop_iteration_runner(**kwargs)

    async def _process_plan(self, loop_response: LanguageModelStreamResponse) -> bool:
        self._logger.info(
            "Processing the plan, executing the tools and checking for loop exit conditions once all is done."
        )

        if loop_response.is_empty():
            self._logger.debug("Empty model response, exiting loop.")
            await self._chat_service.modify_assistant_message_async(
                content=env_settings.empty_message_warning
            )
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

        if self._config.agent.experimental.open_file_tool_config.enabled:
            if self._open_file_runtime.should_attach_content_files():
                messages = (
                    self._open_file_runtime.inject_content_files_into_user_message(
                        messages
                    )
                )

        tool_reminders: list[str] = []
        for prompts in self._tool_manager.get_tool_prompts():
            if prompts.tool_system_reminder_for_user_prompt:
                tool_reminders.append(prompts.tool_system_reminder_for_user_prompt)
        messages = inject_tool_reminders_into_user_message(messages, tool_reminders)
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

        uploaded_documents_expired = [
            doc for doc in self._uploaded_documents if doc.is_expired()
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
            max_loop_iterations=self._config.effective_max_loop_iterations,
            current_iteration=self.current_iteration_index + 1,
            mcp_server_system_prompts=mcp_server_system_prompts,
            use_sub_agent_references=use_sub_agent_references,
            sub_agent_referencing_instructions=sub_agent_referencing_instructions,
            user_metadata=user_metadata,
            uploaded_documents_expired=uploaded_documents_expired,
            user_memory=self._user_memory_text,
        )
        return system_message

    def _finalize_loop_timing(self, loop_start: float) -> None:
        self._current_loop_timing["total_loop_time"] = round(
            time.perf_counter() - loop_start, 3
        )
        self._execution_times.append(dict(self._current_loop_timing))

    async def _handle_no_tool_calls(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        """Handle the case where no tool calls are returned."""
        task_executor = SafeTaskExecutor(
            logger=self._logger,
        )

        if self._config.agent.experimental.open_file_tool_config.enabled:
            selected_evaluation_names = self._open_file_runtime.filter_evaluation_names(
                self._tool_manager.get_evaluation_check_list()
            )
        else:
            selected_evaluation_names = self._tool_manager.get_evaluation_check_list()

        if (
            isinstance(loop_response, ResponsesLanguageModelStreamResponse)
            and loop_response.code_interpreter_calls
        ):
            selected_evaluation_names = [
                name
                for name in selected_evaluation_names
                if name != EvaluationMetricName.HALLUCINATION
            ]
            self._logger.info(
                "Code interpreter was used - skipping hallucination check "
                "(answer is grounded in code execution output, not search chunks)."
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

        postprocessor_result, evaluation_results = await asyncio.gather(
            postprocessor_result,
            evaluation_results,
        )
        postprocessor_outputs = postprocessor_result.unpack() or {}
        # run_postprocessors erases each postprocessor's return type to
        # `object | None` (generic channel), so re-narrow the one we own.
        self._generated_files_info = cast(
            "ArtifactsDebugInfo | None",
            postprocessor_outputs.get(
                DisplayCodeInterpreterFilesPostProcessor.__name__
            ),
        )
        # Absent key => postprocessor not activated this turn (stays None);
        # present => bool telling whether the memory profile was updated.
        self._context_memory_updated = cast(
            "bool | None",
            postprocessor_outputs.get(UserMemoryPostprocessor.__name__),
        )
        self._current_loop_timing["post_processing"].update(
            self._postprocessor_manager.get_execution_times()
        )
        self._invocation_stats.extend(
            self._postprocessor_manager.get_invocation_stats()
        )

        evaluation_times = self._evaluation_manager.get_execution_times()
        for name in selected_evaluation_names:
            name_str = str(name)
            self._current_loop_timing["evaluation"][name_str] = evaluation_times.get(
                name_str, 0
            )
        self._invocation_stats.extend(self._evaluation_manager.get_invocation_stats())
        self._invocation_stats_finalized = True

        if evaluation_results.success and not all(
            result.is_positive for result in evaluation_results.unpack()
        ):
            self._logger.warning(
                "we should add here the retry counter add an instruction and retry the loop for now we just exit the loop."
            )  # TODO: add retry counter and instruction

        return True

    async def _persist_tool_calls(self) -> None:
        """Persist tool calls and responses from the loop to the database.

        Before persisting, uncited sources are stripped from tool response
        content so that only sources referenced in the final assistant message
        are kept (compaction).
        """
        records = self._history_manager.extract_message_tools()
        if not records:
            return
        records = HistoryManager.compact_message_tools(
            records=records,
            assistant_text=self._last_assistant_text,
        )
        try:
            await self._chat_service.create_message_tools_async(
                tool_calls=records,
            )
            self._logger.info(f"Persisted {len(records)} tool call records")
        except Exception:
            self._logger.error("Failed to persist tool calls", exc_info=True)

    def _log_tool_calls(self, tool_calls: list) -> None:
        # Create dictionary mapping tool names to display names for efficient lookup
        all_tools_dict: dict[str, str] = {
            tool.name: tool.display_name()
            for tool in self._tool_manager.available_tools
        }

        # Tool names that should not be logged in the "Triggered Tool Calls"
        # step. The Skill tool emits its own message log entry per invocation
        # (see ``unique_skill_tool.SkillTool._log_skill_loaded``), so it is
        # redundant and noisy to also list it here.

        tool_names_not_to_log: set[str] = {
            "DeepResearch",
            "Skill",
            "AskUser",
            "ActivatePython",
        }

        used_tools: dict[str, int] = {}
        for tool_call in tool_calls:
            self._history_manager.add_tool_call(tool_call)
            if tool_call.name in all_tools_dict:
                used_tools[tool_call.name] = used_tools.get(tool_call.name, 0) + 1

        suppress_step_entry = any(
            getattr(getattr(tool, "config", None), "show_triggered_tool_calls", True)
            is False
            for tool in self._tool_manager.available_tools
        )
        if suppress_step_entry:
            return

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

        execution_start = time.perf_counter()
        tool_call_responses = await self._tool_manager.execute_selected_tools(
            tool_calls
        )
        execution_total = round(time.perf_counter() - execution_start, 3)

        for response in tool_call_responses:
            self._invocation_stats.extend(response.invocation_stats)

        tool_times: dict[str, float] = {}
        for response in tool_call_responses:
            if response.debug_info and "execution_time_s" in response.debug_info:
                name = response.name
                if name == "total" or name in tool_times:
                    counter = 2
                    base = name
                    while f"{base}_{counter}" in tool_times:
                        counter += 1
                    name = f"{base}_{counter}"
                tool_times[name] = response.debug_info["execution_time_s"]

        self._current_loop_timing["tool_execution"] = {
            "total": execution_total,
            **tool_times,
        }

        # Inject reminders before persisting tool results into history.
        if self._config.agent.experimental.open_file_tool_config.enabled:
            self._open_file_runtime.inject_open_file_reminder(tool_call_responses)

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


@deprecated("Use UniqueAI directly instead")
class UniqueAIResponsesApi(UniqueAI):
    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: UniqueAIConfig,
        chat_service: ChatService,
        content_service: ContentService,
        uploaded_documents: list[Content],
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
            uploaded_documents=uploaded_documents,
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
