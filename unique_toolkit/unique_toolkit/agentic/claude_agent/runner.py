"""
Claude Agent runner — orchestrates a single Claude Agent SDK turn.

This module is the core deliverable of Step 2a (structure) and Step 3 (SDK loop).
It provides:

- ClaudeAgentRunner: returned by _build_claude_agent() in unique_ai_builder.py.
  Its run() method drives the full turn lifecycle:
    workspace setup → system prompt → history → options → Claude SDK loop →
    post-processing → message completion → workspace persist → cleanup.

Design constraints (enforce throughout):
- cwd and env are always passed as parameters, never hardcoded. This keeps the
  runner sandbox-agnostic for WI-4 / A3 future work.
- The runner lives in unique_toolkit and must NOT import orchestrator internals
  (e.g. _CommonComponents). Services are injected individually.

Step 3 adds the claude-agent-sdk dependency and implements _run_claude_loop()
and _run_post_processing().
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKError,
    query,
)
from claude_agent_sdk.types import (
    McpSdkServerConfig,
    ResultMessage,
    StreamEvent,
    ToolUseBlock,
)

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
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
)

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

        messages = self._history_manager.get_loop_history()
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

    def _build_mcp_server(self) -> McpSdkServerConfig:
        """Build the unified MCP server with KB search + platform proxy tools."""
        from .mcp_tools import build_unique_mcp_server

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
        """Run the Claude Agent SDK query loop and stream results to the frontend.

        Iterates over the async event stream from claude_agent_sdk.query():
        - content_block_delta / text_delta → accumulate text + stream via
          modify_assistant_message_async() (PATCH /message → AMQP → frontend)
        - assistant messages → log tool_use blocks; detect TodoWrite state
        - result → capture final text if no deltas were streamed
        - SDK errors → log, set user-facing error message, do NOT re-raise

        Returns accumulated_text string consumed by _run_post_processing().
        """
        accumulated_text = ""
        tool_call_count = 0

        sdk_options_kwargs = dict(options)
        if self._claude_config.stderr_logging:

            def _stderr_handler(data: str) -> None:
                self._logger.debug("Claude Agent SDK stderr: %s", data.strip())

            sdk_options_kwargs["stderr"] = _stderr_handler

        sdk_options = ClaudeAgentOptions(**sdk_options_kwargs)

        try:
            # Pass prompt as an async iterable so the SDK uses stream_input(),
            # which keeps stdin open until the first result arrives before closing.
            # The string-prompt path closes stdin immediately via end_input(), which
            # breaks MCP control-request responses (CLIConnectionError: ProcessTransport
            # is not ready for writing). stream_input() is aware of sdk_mcp_servers and
            # waits for the first result before closing the channel.
            async def _prompt_iter() -> AsyncIterator[dict[str, Any]]:
                yield {
                    "type": "user",
                    "session_id": "",
                    "message": {"role": "user", "content": prompt},
                    "parent_tool_use_id": None,
                }

            async for message in query(prompt=_prompt_iter(), options=sdk_options):
                if isinstance(message, StreamEvent):
                    event = message.event
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                accumulated_text += text
                                await self._chat_service.modify_assistant_message_async(
                                    content=accumulated_text
                                )

                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            tool_call_count += 1
                            input_preview = str(block.input)[:200]
                            self._logger.debug(
                                "Claude agent tool call #%d: %s | input: %s",
                                tool_call_count,
                                block.name,
                                input_preview,
                            )
                            if block.name == "TodoWrite":
                                todos = (block.input or {}).get("todos", [])
                                for todo in todos:
                                    status = todo.get("status", "?")
                                    content = todo.get("activeForm") or todo.get(
                                        "content", ""
                                    )
                                    self._logger.debug(
                                        "todo [%s]: %s", status, content[:100]
                                    )

                elif isinstance(message, ResultMessage):
                    if message.result and not accumulated_text:
                        accumulated_text = message.result

        except ClaudeSDKError as e:
            self._logger.error("Claude Agent SDK error: %s", e, exc_info=True)
            if not accumulated_text:
                accumulated_text = (
                    f"An error occurred while processing your request: {e}"
                )

        except Exception as e:
            self._logger.error(
                "Unexpected error in Claude Agent loop: %s", e, exc_info=True
            )
            if not accumulated_text:
                accumulated_text = (
                    f"An error occurred while processing your request: {e}"
                )

        return accumulated_text

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
                role="assistant",
                text=claude_result,
                original_text=claude_result,
            ),
            tool_calls=None,
        )

        task_executor = SafeTaskExecutor(logger=self._logger)
        # TODO (Step 4+): Replace [] with self._tool_manager.get_evaluation_check_list()
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
