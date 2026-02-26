"""
Claude Agent runner — orchestrates a single Claude Agent SDK turn.

This module is the core deliverable of Step 2a. It provides:

- ClaudeAgentRunner: returned by _build_claude_agent() in unique_ai_builder.py.
  Its run() method drives the full turn lifecycle:
    workspace setup → system prompt → history → options → Claude SDK loop →
    post-processing → message completion → workspace persist → cleanup.

Design constraints (enforce throughout):
- cwd and env are always passed as parameters, never hardcoded. This keeps the
  runner sandbox-agnostic for WI-4 / A3 future work.
- No import of claude_agent_sdk in this step. The SDK dependency will be added
  in Step 3 when _run_claude_loop() is implemented.
- The runner lives in unique_toolkit and must NOT import orchestrator internals
  (e.g. _CommonComponents). Services are injected individually.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Any

from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
)
from unique_toolkit.agentic.evaluation.evaluation_manager import EvaluationManager
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    PostprocessorManager,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.thinking_manager.thinking_manager import ThinkingManager
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.service import ContentService

from .config import ClaudeAgentConfig, build_tool_policy
from .history import format_history_as_text
from .prompts import PromptContext, build_system_prompt

if TYPE_CHECKING:
    from unique_orchestrator.config import UniqueAIConfig

    from unique_toolkit.app.schemas import ChatEvent


class ClaudeAgentRunner:
    """Entry-point runner for Claude Agent SDK integration.

    Returned by _build_claude_agent() in unique_ai_builder.py when
    experimental.claude_agent_config is explicitly set on UniqueAIConfig.

    Bypasses UniqueAI.run() entirely (Decision A1 / Option C). Drives its own
    turn: workspace → system prompt → history → SDK loop → post-processing.
    Eval, postprocessing, and references always run after Claude exits — this is
    the key advantage over Abi's Node implementation which omits all three.

    See: .local-dev/claude_sdk_integration/proposals/001-streaming-contract-v2.md §A1
    """

    def __init__(
        self,
        event: "ChatEvent",
        logger: Logger,
        config: "UniqueAIConfig",
        claude_config: ClaudeAgentConfig,
        chat_service: ChatService,
        content_service: ContentService,
        evaluation_manager: EvaluationManager,
        postprocessor_manager: PostprocessorManager,
        reference_manager: ReferenceManager,
        thinking_manager: ThinkingManager,
        tool_progress_reporter: ToolProgressReporter,
        message_step_logger: MessageStepLogger,
        history_manager: HistoryManager,
        debug_info_manager: DebugInfoManager,
    ) -> None:
        self._event = event
        self._logger = logger
        self._config = config
        self._claude_config = claude_config
        self._chat_service = chat_service
        self._content_service = content_service
        self._evaluation_manager = evaluation_manager
        self._postprocessor_manager = postprocessor_manager
        self._reference_manager = reference_manager
        self._thinking_manager = thinking_manager
        self._tool_progress_reporter = tool_progress_reporter
        self._message_step_logger = message_step_logger
        self._history_manager = history_manager
        self._debug_info_manager = debug_info_manager

        # Workspace dir is set during run() and used for persist/cleanup in the
        # finally block. None until _setup_workspace() runs.
        self._workspace_dir: Path | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Execute a single Claude Agent SDK turn.

        Flow: workspace setup → prompt → history → options → Claude loop →
        post-processing → message completion → workspace persist → cleanup.

        Each phase is isolated in a private method so that Step 3 (streaming loop)
        and Step 2b (prompts/history) can be filled in independently.
        """
        self._logger.info("Starting Claude Agent runner...")

        workspace_dir = await self._setup_workspace()

        try:
            system_prompt = await self._build_system_prompt()
            history = self._build_history()  # noqa: F841 — passed to SDK in Step 2b/3
            options = self._build_options(
                system_prompt=system_prompt,
                workspace_dir=workspace_dir,
            )

            claude_result = await self._run_claude_loop(
                prompt=self._event.payload.user_message.text,
                options=options,
            )

            await self._run_post_processing(claude_result)

            await self._chat_service.modify_assistant_message_async(
                set_completed_at=True,
            )
        finally:
            if workspace_dir is not None:
                await self._persist_workspace(workspace_dir)
                self._cleanup_workspace(workspace_dir)

    # ─────────────────────────────────────────────────────────────────────────
    # Phase methods
    # ─────────────────────────────────────────────────────────────────────────

    async def _setup_workspace(self) -> Path | None:
        """Fetch and extract workspace zip if persistence is enabled.

        Returns the workspace directory path, or None if persistence is disabled.
        Implementation deferred to workspace.py integration (Step 7).
        """
        if not self._claude_config.enable_workspace_persistence:
            return None
        # TODO (Step 7): delegate to workspace.fetch_workspace(
        #     content_service=self._content_service,
        #     chat_id=self._event.payload.chat_id,
        # )
        return None

    async def _build_system_prompt(self) -> str:
        """Compose the system prompt from platform context.

        Returns system_prompt_override verbatim when set. Otherwise builds
        a structured prompt via build_system_prompt() matching Abi's
        buildClaudeAgentSystemPrompt() output.
        """
        if self._claude_config.system_prompt_override:
            return self._claude_config.system_prompt_override

        context = PromptContext(
            model_name=self._claude_config.model,
            date_string=datetime.now().strftime("%A %B %d, %Y"),
            user_metadata=self._get_user_metadata(),
            custom_instructions=self._claude_config.custom_instructions or None,
            user_instructions=self._claude_config.user_instructions,
            project_name=(
                getattr(self._config, "space", None)
                and getattr(self._config.space, "project_name", "Unique AI")
                or "Unique AI"
            ),
            history_text=self._format_history(),
        )
        return build_system_prompt(context)

    def _build_history(self) -> list[dict[str, Any]]:
        """Return placeholder for future structured Anthropic-format history.

        For MVP, history is injected as a text section inside the system prompt
        via _format_history() / _build_system_prompt(). Structured Anthropic
        messages ([{role, content}]) will be returned here in a later step once
        the SDK streaming loop (Step 3) is in place.
        """
        return []

    def _format_history(self) -> str:
        """Get formatted history text for system prompt injection."""
        if not self._claude_config.history_included:
            return ""

        messages = (
            self._history_manager._loop_history
        )  # TODO: use public API when available
        return format_history_as_text(
            messages=messages,
            max_interactions=self._claude_config.max_history_interactions,
        )

    def _get_user_metadata(self) -> dict[str, str]:
        """Extract user metadata from the event payload.

        TODO: filter to only the keys listed in config.agent.prompt_config.user_metadata
        (see unique_ai.py::_get_filtered_user_metadata). For MVP, returns all
        available metadata as str values.
        """
        raw = getattr(self._event.payload, "user_metadata", None)
        if not raw:
            return {}
        return {k: str(v) for k, v in raw.items()}

    def _build_options(
        self,
        system_prompt: str,
        workspace_dir: Path | None,
    ) -> dict[str, Any]:
        """Construct options dict matching ClaudeAgentOptions shape.

        Does not import claude_agent_sdk — the dict is unpacked into
        ClaudeAgentOptions(**options) inside _run_claude_loop() once the SDK
        dependency is wired in Step 3.

        MCP server objects (search_kb, list_chat_files, etc.) are NOT included
        here — they will be created in mcp_tools.py (Step 4) and merged into the
        returned dict before it is passed to ClaudeAgentOptions.
        """
        import os

        allowed_tools, disallowed_tools = build_tool_policy(self._claude_config)

        options: dict[str, Any] = {
            "system_prompt": system_prompt,
            "model": self._claude_config.model,
            "max_turns": self._claude_config.max_turns,
            "max_budget_usd": self._claude_config.max_budget_usd,
            "permission_mode": self._claude_config.permission_mode,
            "allowed_tools": allowed_tools,
            "disallowed_tools": disallowed_tools,
            "env": {
                "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
                **self._claude_config.extra_env,
            },
            # include_partial_messages exposes content_block_delta events mid-turn.
            # Required for streaming text chunks to the frontend in real time.
            "include_partial_messages": True,
        }

        if workspace_dir is not None:
            options["cwd"] = str(workspace_dir)

        if self._claude_config.max_thinking_tokens is not None:
            options["max_thinking_tokens"] = self._claude_config.max_thinking_tokens

        if self._claude_config.fallback_model is not None:
            options["fallback_model"] = self._claude_config.fallback_model

        if self._claude_config.setting_sources is not None:
            options["setting_sources"] = self._claude_config.setting_sources

        if self._claude_config.add_dirs:
            options["add_dirs"] = self._claude_config.add_dirs

        if self._claude_config.cli_path is not None:
            options["cli_path"] = self._claude_config.cli_path

        return options

    async def _run_claude_loop(
        self,
        prompt: str,
        options: dict[str, Any],
    ) -> Any:
        """Run the Claude Agent SDK query loop and stream results to the frontend.

        Step 3 implementation pattern (do not implement now, but preserve this docstring):

            from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
            accumulated_text = ""
            async for message in query(prompt=prompt, options=ClaudeAgentOptions(**options)):
                if message.type == "content_block_delta":
                    delta = message.delta
                    if delta.type == "text_delta":
                        accumulated_text += delta.text
                        await self._chat_service.modify_assistant_message_async(
                            content=accumulated_text
                        )
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if block.type == "tool_use":
                            # log tool call via self._message_step_logger
                            pass
            return accumulated_text  # used by post-processing

        query() is a native async generator — no extra streaming mode to configure.
        Each content_block_delta / text_delta maps to one modify_assistant_message_async()
        call → PATCH /message/{id} → platform AMQP → frontend stream chunk.
        Call frequency matches OpenAI token streaming (confirmed by Abhi 2026-02-23).

        See also: claude-agent-streaming.service.ts in Abi's PR for the Node equivalent.
        """
        raise NotImplementedError(
            "Claude SDK loop not yet implemented — see Step 3 (streaming loop)"
        )

    async def _run_post_processing(self, claude_result: Any) -> None:
        """Run evaluations and postprocessors after Claude's loop exits.

        Intended pattern (mirrors UniqueAI._handle_no_tool_calls() — see unique_ai.py:380):

            from unique_toolkit.agentic.tools.tool_manager import SafeTaskExecutor
            task_executor = SafeTaskExecutor(logger=self._logger)
            evaluation_results = task_executor.execute_async(
                self._evaluation_manager.run_evaluations,
                selected_evaluation_names,
                claude_result,          # needs LanguageModelStreamResponse adapter
                self._event.payload.assistant_message.id,
            )
            postprocessor_result = task_executor.execute_async(
                self._postprocessor_manager.run_postprocessors,
                claude_result,          # needs LanguageModelStreamResponse adapter
            )
            _, evaluation_results = await asyncio.gather(
                postprocessor_result,
                evaluation_results,
            )

        TODO (Step 3): Once the shape of claude_result is defined (accumulated text
        string or a richer object), create a LanguageModelStreamResponse-compatible
        adapter so evaluation_manager.run_evaluations() and
        postprocessor_manager.run_postprocessors() can consume it unchanged.
        Eval and postprocessors must run concurrently via asyncio.gather().

        The asyncio import is kept at module level for this future use.
        """
        _ = asyncio  # used in Step 3 when SafeTaskExecutor pattern is implemented
        self._logger.info("Running post-processing pipeline...")
        # TODO (Step 3): implement SafeTaskExecutor pattern described above.
        self._logger.info("Post-processing complete.")

    async def _persist_workspace(self, workspace_dir: Path) -> None:
        """Zip and upload workspace for next turn.

        Implementation deferred to workspace.py integration (Step 7).
        Pattern: zip workspace_dir → ContentService.upload_content_from_bytes(
            chat_id=self._event.payload.chat_id, skip_ingestion=True
        )
        """
        pass

    def _cleanup_workspace(self, workspace_dir: Path) -> None:
        """Remove local workspace directory after persist completes.

        Implementation deferred to Step 7. Pattern: shutil.rmtree(workspace_dir).
        """
        pass
