from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class ClaudeAgentConfig(BaseToolConfig):
    """Configuration for Claude Agent SDK integration.

    Maps to ClaudeAgentOptions in the claude-agent-sdk Python package.
    See CLAUDE_AGENT_SDK_GUIDE.md §3 for the full parameter reference.
    """

    # ─── Model & Reasoning ───
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model identifier. Short names ('opus', 'sonnet', 'haiku') or full IDs.",
    )
    fallback_model: str | None = Field(
        default=None,
        description="Fallback model if primary is unavailable.",
    )
    max_thinking_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Budget for extended/adaptive thinking. None = SDK default.",
    )

    # ─── Agent Loop Limits ───
    max_turns: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum autonomous reasoning turns.",
    )
    max_budget_usd: float = Field(
        default=2.0,
        ge=0.1,
        le=10.0,
        description="Hard cost cap per invocation in USD.",
    )

    # ─── Permissions ───
    permission_mode: Literal["default", "acceptEdits", "bypassPermissions"] = Field(
        default="bypassPermissions",
        description="Tool permission trust level. 'bypassPermissions' for production/sandboxed use.",
    )

    # ─── Knowledge Base & Search ───
    search_type: str = Field(
        default="COMBINED",
        description="Knowledge base search type: VECTOR | COMBINED | FULL_TEXT | POSTGRES_FULL_TEXT",
    )
    scope_ids: list[str] = Field(
        default_factory=list,
        description="Scope IDs to restrict KB search. Empty = search all scopes.",
    )

    # ─── History ───
    history_included: bool = Field(
        default=True,
        description="Include conversation history in system prompt.",
    )
    max_history_interactions: int = Field(
        default=4,
        ge=0,
        description="Max past interactions to include in history context.",
    )

    # ─── Code Execution ───
    enable_code_execution: bool = Field(
        default=False,
        description="Allow Claude to use Bash, Write, Edit, Read, Glob, Grep tools.",
    )

    # ─── Skills & Settings ───
    setting_sources: list[str] | None = Field(
        default=None,
        description=(
            "Controls loading of .claude/ skills, CLAUDE.md, and rules. "
            "None = full isolation (default). ['project'] = load from cwd/.claude/. "
            "Required for skills to work."
        ),
    )
    add_dirs: list[str] = Field(
        default_factory=list,
        description="Additional directories to make visible to the agent (e.g. data mounts, templates).",
    )

    # ─── Workspace Persistence ───
    enable_workspace_persistence: bool = Field(
        default=True,
        description="Persist workspace across turns via zip upload/download.",
    )

    # ─── System Prompt ───
    system_prompt_override: str = Field(
        default="",
        description="Override the default system prompt entirely. Empty = use platform default.",
    )
    custom_instructions: str | None = Field(
        default=None,
        description="Additional instructions appended to system prompt (project context).",
    )
    user_instructions: str | None = Field(
        default=None,
        description="User-specific instructions appended to system prompt.",
    )

    # ─── Subagents (future) ───
    agents: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Subagent definitions. Dict mapping agent name to AgentDefinition-compatible dict. "
            "Not used in MVP but field exists for forward compatibility."
        ),
    )

    # ─── Hooks (future) ───
    enable_hooks: bool = Field(
        default=False,
        description="Enable the PreToolUse/PostToolUse/Stop hook system. Hook definitions are code-side.",
    )

    # ─── Session Management (future) ───
    session_id: str | None = Field(
        default=None,
        description="Resume a specific session. None = new session each turn.",
    )
    continue_conversation: bool = Field(
        default=False,
        description="Continue from previous session (requires session_id).",
    )

    # ─── Advanced / Deployment ───
    cli_path: str | None = Field(
        default=None,
        description="Override bundled CLI binary path. None = use bundled binary.",
    )
    stderr_logging: bool = Field(
        default=True,
        description="Capture full CLI stderr for debug logging.",
    )
    enable_file_checkpointing: bool = Field(
        default=False,
        description="Enable file state snapshots for recovery.",
    )
    extra_env: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables passed to the CLI process.",
    )


# ─── Tool Policy ───

BASE_ALLOWED_TOOLS = [
    "mcp__unique_platform__search_knowledge_base",
    "mcp__unique_platform__web_search",
    "mcp__unique_platform__list_chat_files",
    "mcp__unique_platform__read_chat_file",
]

BASE_DISALLOWED_TOOLS = ["WebFetch", "WebSearch"]

CODE_EXECUTION_TOOLS = ["Bash", "Write", "Edit", "Read", "Glob", "Grep"]

SKILL_TOOLS = ["Skill"]

TODO_TOOLS = ["TodoRead", "TodoWrite"]


def build_tool_policy(config: ClaudeAgentConfig) -> tuple[list[str], list[str]]:
    """Build allowed/disallowed tool lists from config.

    Returns (allowed_tools, disallowed_tools) for ClaudeAgentOptions.
    """
    allowed = list(BASE_ALLOWED_TOOLS)
    disallowed = list(BASE_DISALLOWED_TOOLS)

    if config.enable_code_execution:
        allowed.extend(CODE_EXECUTION_TOOLS)
    else:
        disallowed.extend(["Bash", "Write", "Edit", "MultiEdit"])

    if config.setting_sources is not None:
        allowed.extend(SKILL_TOOLS)

    # TodoRead/TodoWrite are always available for progress tracking
    allowed.extend(TODO_TOOLS)

    return allowed, disallowed
