"""
Claude Agent runner — orchestrates a single Claude Agent SDK turn.

- ClaudeAgentRunner: returned by _build_claude_agent() in unique_ai_builder.py.
  Its run() method drives the full turn lifecycle:
    workspace setup → system prompt → history → options → Claude SDK loop →
    post-processing → message completion → workspace persist → cleanup.

Design constraints (enforce throughout):
- cwd and env are always passed as parameters, never hardcoded.
- The runner lives in unique_toolkit and must NOT import orchestrator internals
  (e.g. _CommonComponents). Services are injected individually.

"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk.types import McpSdkServerConfig

from unique_toolkit._common.execution import SafeTaskExecutor
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
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
)

from . import workspace as workspace_module
from .config import ClaudeAgentConfig, build_tool_policy
from .generated_files import inject_file_references_into_text
from .mcp_tools import build_unique_mcp_server
from .prompts import PromptContext, build_system_prompt

if TYPE_CHECKING:
    from unique_orchestrator.config import UniqueAIConfig

    from unique_toolkit.app.schemas import ChatEvent


class ClaudeAgentRunner:
    """Entry-point runner for Claude Agent SDK integration.

    Returned by _build_claude_agent() in unique_ai_builder.py when
    experimental.claude_agent_config is explicitly set on UniqueAIConfig.

    Bypasses UniqueAI.run() entirely. Drives its own turn: workspace → system
    prompt → history → SDK loop → post-processing. Eval, postprocessing, and
    references always run after Claude exits.

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
        output file upload → text enrichment → post-processing →
        message completion → checkpoint save → cleanup.

        Output files are uploaded BEFORE post-processing so that inline
        image/file references flow through the postprocessor pipeline and
        appear in the final chat message. The workspace checkpoint is saved
        afterwards (in finally) to capture the full turn state.

        Each phase is isolated in a private method for clear separation of concerns.
        """
        self._logger.info("Starting Claude Agent runner...")

        workspace_dir = await self._setup_workspace()

        try:
            system_prompt = await self._build_system_prompt()
            self._build_history()  # history is injected as text in the system prompt for MVP
            options = self._build_options(
                system_prompt=system_prompt,
                workspace_dir=workspace_dir,
            )

            claude_result = await self._run_claude_loop(
                prompt=self._event.payload.user_message.text,
                options=options,
            )

            # Upload output files and enrich accumulated text with inline references.
            # If references were injected, push the enriched text to the chat service
            # so the UI sees unique://content/ URLs rather than ./output/ paths.
            uploaded_files = await self._upload_output_files(workspace_dir)
            enriched_result = inject_file_references_into_text(
                claude_result, uploaded_files
            )
            if enriched_result != claude_result:
                await self._chat_service.modify_assistant_message_async(
                    content=enriched_result,
                )

            await self._run_post_processing(enriched_result)

            await self._chat_service.modify_assistant_message_async(
                set_completed_at=True,
            )
        finally:
            if workspace_dir is not None:
                await self._save_workspace_checkpoint(workspace_dir)
                self._cleanup_workspace(workspace_dir)

    # ─────────────────────────────────────────────────────────────────────────
    # Phase methods
    # ─────────────────────────────────────────────────────────────────────────

    async def _setup_workspace(self) -> Path | None:
        """Fetch and extract workspace zip if persistence is enabled.

        Returns the workspace directory path, or None if persistence is disabled.
        """
        if not self._claude_config.enable_workspace_persistence:
            return None
        try:
            return await workspace_module.setup_workspace(
                content_service=self._content_service,
                chat_id=self._event.payload.chat_id,
                logger=self._logger,
                skills_scope_id=self._claude_config.skills_scope_id,
            )
        except Exception as e:
            self._logger.error(
                "workspace: setup failed — running without workspace: %s",
                e,
                exc_info=True,
            )
            return None

    async def _build_system_prompt(self) -> str:
        """Compose the system prompt from platform context.

        Returns system_prompt_override verbatim when set. Otherwise builds
        a structured prompt via build_system_prompt().
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
            enable_code_execution=self._claude_config.enable_code_execution,
        )
        return build_system_prompt(context)

    def _build_history(self) -> list[dict[str, Any]]:
        """Return placeholder for future structured conversation history.

        For MVP, history is injected as a text block inside the system prompt via
        _format_history() / _build_system_prompt(). This differs from the OpenAI
        completions path where a messages list is passed directly to the model.

        The Claude Agent SDK does not expose an OpenAI-style messages parameter.
        History must flow through the prompt itself — either as text (current
        approach) or as a structured prompt iterable in a future implementation.

        Two paths are planned post-MVP:
        - Platform-controlled: persist full turn (assistant + tool messages) to DB
          after each loop; replay as structured Anthropic-format messages via the
          _prompt_iter() async generator on the next turn. Preserves audit trail
          and gives us full control.
        - SDK-native: use session_id / continue_conversation in ClaudeAgentConfig
          to let the SDK manage conversation state itself. Simpler, but bypasses
          our DB persistence and audit logging.
        """
        return []

    def _format_history(self) -> str:
        """Get formatted history text for system prompt injection."""
        if not self._claude_config.history_included:
            return ""
        # TODO: wire HistoryManager or DB-backed history in follow-up; for MVP no history injected
        return ""

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

    def _build_mcp_server(self) -> McpSdkServerConfig:
        """Build the unified MCP server with KB search + platform proxy tools."""
        return build_unique_mcp_server(
            content_service=self._content_service,
            claude_config=self._claude_config,
            event=self._event,
        )

    def _build_options(
        self,
        system_prompt: str,
        workspace_dir: Path | None,
    ) -> dict[str, Any]:
        """Construct options dict matching ClaudeAgentOptions shape."""
        allowed_tools, disallowed_tools = build_tool_policy(self._claude_config)

        options: dict[str, Any] = {
            "system_prompt": system_prompt,
            "model": self._claude_config.model,
            "max_turns": self._claude_config.max_turns,
            "max_budget_usd": self._claude_config.max_budget_usd,
            "permission_mode": self._claude_config.permission_mode,
            "allowed_tools": allowed_tools,
            "disallowed_tools": disallowed_tools,
            # ANTHROPIC_API_KEY is forwarded to the SDK subprocess via env rather
            # than passed as a constructor argument. The subprocess inherits this
            # dict, not the parent process environment, so it must be explicit.
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

        if workspace_dir is not None and (workspace_dir / ".claude").exists():
            options["env"]["HOME"] = str(workspace_dir)
            options["continue_conversation"] = True

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

        mcp_server = self._build_mcp_server()
        options["mcp_servers"] = {"unique_platform": mcp_server}

        # Add dynamically discovered platform tool names to allowed_tools
        mcp_servers = getattr(self._event.payload, "mcp_servers", []) or []
        for server in mcp_servers:
            for mcp_tool in server.tools:
                tool_fqn = f"mcp__unique_platform__{mcp_tool.name}"
                if tool_fqn not in options["allowed_tools"]:
                    options["allowed_tools"].append(tool_fqn)

        return options

    async def _run_claude_loop(
        self,
        prompt: str,
        options: dict[str, Any],
    ) -> str:
        """Run the Claude Agent SDK query loop and return accumulated_text.

        Delegates to streaming.run_claude_loop() which owns the event loop,
        streaming logic, and all per-event handlers.
        """
        from .streaming import run_claude_loop

        return await run_claude_loop(
            prompt=prompt,
            options=options,
            chat_service=self._chat_service,
            tool_progress_reporter=self._tool_progress_reporter,
            claude_config=self._claude_config,
            logger=self._logger,
        )

    async def _run_post_processing(self, claude_result: str) -> None:
        """Run evaluations and postprocessors after Claude's loop exits.

        Wraps accumulated_text in a LanguageModelStreamResponse so that
        evaluation_manager and postprocessor_manager can consume it unchanged.
        Both run concurrently via asyncio.gather() using SafeTaskExecutor.

        Mirrors the pattern from UniqueAI._handle_no_tool_calls() (unique_ai.py ~407).
        """
        if not claude_result:
            self._logger.warning(
                "Claude Agent returned empty result — skipping post-processing."
            )
            return

        self._logger.info("Running post-processing pipeline...")

        response_adapter = LanguageModelStreamResponse(
            message=LanguageModelStreamResponseMessage(
                id=self._event.payload.assistant_message.id,
                previous_message_id=None,
                role=LanguageModelMessageRole.ASSISTANT,
                text=claude_result,
                original_text=claude_result,
            ),
            tool_calls=None,
        )

        task_executor = SafeTaskExecutor(logger=self._logger)
        # TODO: Replace [] with self._tool_manager.get_evaluation_check_list()
        #   when MCP tools are configured.
        evaluation_task = task_executor.execute_async(
            self._evaluation_manager.run_evaluations,
            [],
            response_adapter,
            self._event.payload.assistant_message.id,
        )
        postprocessor_task = task_executor.execute_async(
            self._postprocessor_manager.run_postprocessors,
            response_adapter.model_copy(deep=True),
        )
        _, evaluation_results = await asyncio.gather(
            postprocessor_task, evaluation_task
        )

        self._logger.info("Post-processing complete.")

    async def _upload_output_files(self, workspace_dir: Path | None) -> dict[str, str]:
        """Upload files from ./output/ and return filename → content_id map.

        Returns empty dict if workspace is disabled or upload fails.
        Called before post-processing so file references can be injected into
        the response text before the postprocessor pipeline runs.
        """
        if workspace_dir is None:
            return {}
        try:
            return await workspace_module.upload_output_files(
                workspace_dir=workspace_dir,
                content_service=self._content_service,
                chat_id=self._event.payload.chat_id,
                logger=self._logger,
            )
        except Exception as e:
            self._logger.warning(
                "workspace: output file upload failed — files will not appear inline: %s",
                e,
            )
            return {}

    async def _save_workspace_checkpoint(self, workspace_dir: Path) -> None:
        """Zip and upload full workspace as a checkpoint for the next turn."""
        try:
            await workspace_module._save_checkpoint(
                workspace_dir=workspace_dir,
                content_service=self._content_service,
                chat_id=self._event.payload.chat_id,
                logger=self._logger,
            )
        except Exception as e:
            self._logger.error(
                "workspace: checkpoint save failed — workspace may be lost: %s",
                e,
                exc_info=True,
            )

    def _cleanup_workspace(self, workspace_dir: Path) -> None:
        """Remove local workspace directory after persist completes."""
        workspace_module.cleanup_workspace(
            workspace_dir=workspace_dir,
            logger=self._logger,
        )
