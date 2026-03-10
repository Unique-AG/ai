#!/usr/bin/env python3
"""
Claude Agent SDK — Live Platform Demo

Runs a real agent loop against the QA knowledge base. All tool calls,
tool results, and streaming chunks are visible in the console.

Requires: ANTHROPIC_API_KEY + Unique platform credentials (see Setup below).

Where to put .env.local:  ~/ai/.env.local

Usage
-----
    # Default (KB analysis of Oklo Inc. Q3 2024 earnings):
    uv run python examples/frameworks/claude_agent/demo_streaming.py

    # Named scenarios (each pre-configures query + ClaudeAgentConfig):
    uv run python examples/frameworks/claude_agent/demo_streaming.py --scenario kb
    uv run python examples/frameworks/claude_agent/demo_streaming.py --scenario code
    uv run python examples/frameworks/claude_agent/demo_streaming.py --scenario web
    uv run python examples/frameworks/claude_agent/demo_streaming.py --scenario reasoning

    # Override any scenario with a custom query:
    uv run python examples/frameworks/claude_agent/demo_streaming.py --query "What does Oklo say about AI data centers?"

    # Toggle individual capabilities:
    uv run python examples/frameworks/claude_agent/demo_streaming.py --web-search
    uv run python examples/frameworks/claude_agent/demo_streaming.py --code-exec
    uv run python examples/frameworks/claude_agent/demo_streaming.py --no-scope

    # Use a different KB scope:
    uv run python examples/frameworks/claude_agent/demo_streaming.py --scope scope_eg5zj45yfe5vccqcgw0h939e

Scenarios
---------
  kb        (default) Multi-search KB analysis of Oklo Q3 2024 earnings call
  code      KB research + write a structured investment analysis to demo_output/
  web       KB search + native WebSearch for current Oklo/nuclear news
  reasoning Complex multi-step analytical task showcasing the ReAct loop depth
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import unique_sdk

from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.prompts import (
    PromptContext,
    build_system_prompt,
)
from unique_toolkit.agentic.claude_agent.runner import ClaudeAgentRunner
from unique_toolkit.content.service import ContentService

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
DEFAULT_SCOPE = "scope_eg5zj45yfe5vccqcgw0h939e"  # Investment Research

# .env.local must sit at repo root (same directory as unique_toolkit/)
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_LOCAL = _REPO_ROOT / ".env.local"

# ─────────────────────────────────────────────────────────────────────────────
# System prompt snippets
# ─────────────────────────────────────────────────────────────────────────────

_KB_SEARCH_INSTRUCTIONS = """\
## Knowledge Base Search Instructions
You have access to a knowledge base containing company documents, research, and data.

- Search the knowledge base proactively before answering any question about documents, data, or company information.
- Run 2–3 searches with different, specific query terms to maximise recall. Do not rely on a single broad query.
- Always cite every fact drawn from a search result using the [sourceN] notation provided in the tool response (where N is the source_number field).
- After completing your research, clearly state which documents contained the relevant information.
- If the knowledge base contains no relevant information, say so explicitly rather than answering from general knowledge.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Scenario definitions
# ─────────────────────────────────────────────────────────────────────────────

_SCENARIOS: dict[str, dict[str, object]] = {
    "kb": {
        "description": "Multi-search KB analysis — Oklo Inc. Q3 2024 earnings call",
        "query": (
            "Search the knowledge base and give me a thorough analysis of Oklo Inc.'s Q3 2024 "
            "earnings call, covering: AI data center demand, nuclear energy growth thesis, "
            "business partnerships, and key risks. Be specific with numbers and quotes."
        ),
        "code_exec": False,
        "web_search": False,
    },
    "code": {
        "description": "KB research + write structured investment analysis to demo_output/",
        "query": (
            "Search the knowledge base for Oklo Inc.'s Q3 2024 earnings call transcript. "
            "Focus on what they say about AI data center demand and nuclear energy opportunities. "
            "Then write a structured 1-page investment analysis to ./demo_output/investment_analysis.md "
            "with sections: Executive Summary, Key Themes, Investment Thesis, Risks."
        ),
        "code_exec": True,
        "web_search": False,
    },
    "web": {
        "description": "KB search + native WebSearch for current Oklo/nuclear market context",
        "query": (
            "Search the knowledge base for Oklo Inc.'s Q3 2024 earnings call. "
            "Then use WebSearch to find the latest news about Oklo and the nuclear energy market "
            "since that earnings call. Combine both sources into a concise market update."
        ),
        "code_exec": False,
        "web_search": True,
    },
    "reasoning": {
        "description": "Deep multi-step ReAct loop — compare Oklo across multiple KB documents",
        "query": (
            "I need a comprehensive view of Oklo Inc. across all available documents. "
            "Search the knowledge base multiple times using different angles: "
            "(1) financial performance and milestones, "
            "(2) technology and product differentiation (Aurora reactor), "
            "(3) competitive landscape and risks. "
            "After researching all three, synthesise a structured investment memo with "
            "Bull case / Bear case / Key uncertainties."
        ),
        "code_exec": False,
        "web_search": False,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────


class _DemoHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        print(record.getMessage(), flush=True)


runner_logger = logging.getLogger("demo.claude_agent")
runner_logger.setLevel(logging.INFO)
runner_logger.addHandler(_DemoHandler())
runner_logger.propagate = False

# Show MCP tool results (e.g. "[tool] ← result: N chunks") in the demo console
tool_logger = logging.getLogger("unique_toolkit.claude_agent")
tool_logger.setLevel(logging.INFO)
tool_logger.addHandler(_DemoHandler())
tool_logger.propagate = False


# ─────────────────────────────────────────────────────────────────────────────
# Credentials
# ─────────────────────────────────────────────────────────────────────────────


def _load_credentials() -> dict[str, str]:
    """Load credentials from .env.local at repo root. No other paths or env fallbacks."""
    if not _ENV_LOCAL.exists():
        runner_logger.warning(
            "[demo] Missing %s — create it from .env.local.example and set UNIQUE_APP_KEY, etc.",
            _ENV_LOCAL,
        )
        return {}
    out: dict[str, str] = {}
    for line in _ENV_LOCAL.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    if out:
        runner_logger.info("[demo] Loaded credentials from %s", _ENV_LOCAL)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Platform init
# ─────────────────────────────────────────────────────────────────────────────


def _init_platform(creds: dict[str, str]) -> ContentService:
    """Initialize unique_sdk and return a real ContentService for the QA platform."""
    unique_sdk.api_key = creds.get("UNIQUE_APP_KEY", "")
    unique_sdk.app_id = creds.get("UNIQUE_APP_ID", "")
    unique_sdk.api_base = creds.get("UNIQUE_API_BASE_URL", "")

    company_id = creds.get("UNIQUE_AUTH_COMPANY_ID", "")
    user_id = creds.get("UNIQUE_AUTH_USER_ID", "")

    return ContentService(
        company_id=company_id,
        user_id=user_id,
        chat_id="",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Runner factory
# ─────────────────────────────────────────────────────────────────────────────


def _build_runner(
    content_service: ContentService,
    scope_id: str | None,
    enable_code_exec: bool,
    creds: dict[str, str],
) -> tuple[ClaudeAgentRunner, list[str]]:
    """Build a ClaudeAgentRunner with demo logging and streaming capture."""
    system_prompt = build_system_prompt(
        PromptContext(
            model_name=MODEL,
            date_string=datetime.now().strftime("%A %B %d, %Y"),
            custom_instructions=_KB_SEARCH_INSTRUCTIONS,
        )
    )

    runner_logger.info(
        "[demo] System prompt: %d chars | sections: header + answer_style + reference_guidelines + kb_instructions",
        len(system_prompt),
    )
    runner_logger.info(
        "[demo] NOTE: SDK Skills (.claude/*.md via setting_sources) are Step 5 — not activated here"
    )

    config = ClaudeAgentConfig(
        system_prompt_override=system_prompt,
        model=MODEL,
        max_turns=10,
        permission_mode="bypassPermissions",
        scope_ids=[scope_id] if scope_id else [],
        search_type="COMBINED",
        enable_code_execution=enable_code_exec,
        verbose_logging=True,
    )

    # Streaming capture — mirrors the platform's PATCH /message → AMQP → frontend path
    current_length = 0
    chunks: list[str] = []

    async def _on_stream(content: str | None = None, **kwargs: object) -> None:
        nonlocal current_length
        if content is not None:
            chunks.append(content)
            if len(content) > current_length:
                delta = content[current_length:]
                print(delta, end="", flush=True)
                current_length = len(content)
        elif kwargs.get("set_completed_at"):
            print()

    chat_service = MagicMock()
    chat_service.modify_assistant_message_async = AsyncMock(side_effect=_on_stream)

    mock_event = MagicMock()
    mock_event.payload.chat_id = "demo-chat-001"
    mock_event.payload.assistant_message.id = "demo-msg-001"
    mock_event.payload.user_metadata = None
    mock_event.payload.mcp_servers = []
    mock_event.user_id = creds.get(
        "UNIQUE_AUTH_USER_ID", os.environ.get("UNIQUE_AUTH_USER_ID", "demo-user")
    )
    mock_event.company_id = creds.get(
        "UNIQUE_AUTH_COMPANY_ID",
        os.environ.get("UNIQUE_AUTH_COMPANY_ID", "demo-company"),
    )

    runner = ClaudeAgentRunner(
        event=mock_event,
        logger=runner_logger,
        config=MagicMock(),
        claude_config=config,
        chat_service=chat_service,
        content_service=content_service,
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_progress_reporter=MagicMock(),
        message_step_logger=MagicMock(),
        history_manager=MagicMock(),
        debug_info_manager=MagicMock(),
    )

    return runner, chunks


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


async def _run_demo(args: argparse.Namespace) -> None:
    creds = _load_credentials()
    # Apply to process environment so the SDK subprocess sees ANTHROPIC_API_KEY
    for k, v in creds.items():
        if v:
            os.environ[k] = v

    if not creds.get("ANTHROPIC_API_KEY"):
        print(
            f"[demo] ERROR: ANTHROPIC_API_KEY not set in {_ENV_LOCAL}\n"
            f"  Add a line: ANTHROPIC_API_KEY=sk-ant-...",
            flush=True,
        )
        sys.exit(1)

    # Resolve scenario defaults
    scenario = _SCENARIOS.get(args.scenario or "kb", _SCENARIOS["kb"])
    enable_code_exec: bool = args.code_exec or bool(scenario["code_exec"])
    enable_web_search: bool = args.web_search or bool(scenario["web_search"])
    scope_id = None if args.no_scope else (args.scope or DEFAULT_SCOPE)

    # Set up demo_output workspace if code execution is enabled
    if enable_code_exec:
        demo_output = Path("demo_output")
        demo_output.mkdir(exist_ok=True)
        runner_logger.info(
            "[demo] Code execution enabled | workspace: %s", demo_output.resolve()
        )

    # Resolve query: explicit --query flag overrides scenario default
    query_text: str = args.query or str(scenario["query"])

    content_service = _init_platform(creds)
    runner, chunks = _build_runner(
        content_service=content_service,
        scope_id=scope_id,
        enable_code_exec=enable_code_exec,
        creds=creds,
    )

    system_prompt = runner._claude_config.system_prompt_override
    options = runner._build_options(system_prompt=system_prompt, workspace_dir=None)

    # Enable web search if requested (removes WebSearch from the default disallowed list)
    if enable_web_search:
        options["disallowed_tools"] = [
            t for t in options.get("disallowed_tools", []) if t != "WebSearch"
        ]
        if "WebSearch" not in options.get("allowed_tools", []):
            options.setdefault("allowed_tools", []).append("WebSearch")
        runner_logger.info("[demo] WebSearch enabled (native Claude tool)")

    tools_summary = "search_knowledge_base"
    if enable_web_search:
        tools_summary += " + WebSearch"
    if enable_code_exec:
        tools_summary += " + code_execution (Bash/Write/Edit)"

    scenario_label = args.scenario or "kb"
    runner_logger.info(
        "[demo] ── Scenario: %s ── %s",
        scenario_label,
        scenario["description"],
    )
    runner_logger.info(
        "[demo] model=%s | tools=%s | scope=%s",
        runner._claude_config.model,
        tools_summary,
        "entire KB" if scope_id is None else scope_id,
    )
    runner_logger.info(
        '[demo] Prompt: "%s"',
        query_text[:120] + ("..." if len(query_text) > 120 else ""),
    )
    print(flush=True)

    start = time.monotonic()

    result = await runner._run_claude_loop(
        prompt=query_text,
        options=options,
    )

    elapsed = time.monotonic() - start
    print(flush=True)
    runner_logger.info(
        "[demo] ✓ Complete | response=%d chars | elapsed=%.1fs",
        len(result),
        elapsed,
    )

    # Report any files written under demo_output/
    if enable_code_exec:
        demo_dir = Path("demo_output")
        written = [p for p in demo_dir.iterdir()] if demo_dir.exists() else []
        if written:
            runner_logger.info(
                "[demo] Files in demo_output/: %s",
                ", ".join(p.name for p in written),
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Claude Agent SDK demo — real KB search agent loop with verbose logging.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scenario",
        choices=list(_SCENARIOS),
        default=None,
        help=(
            "Named scenario preset (default: kb). "
            "Each pre-configures query + ClaudeAgentConfig. "
            "Any flag below overrides the scenario default."
        ),
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Custom query to send to Claude (overrides scenario default query).",
    )
    parser.add_argument(
        "--scope",
        type=str,
        default=None,
        help=f"Knowledge base scope ID (default: {DEFAULT_SCOPE}).",
    )
    parser.add_argument(
        "--no-scope",
        action="store_true",
        dest="no_scope",
        help="Search entire knowledge base (no scope filter). Overrides --scope.",
    )
    parser.add_argument(
        "--web-search",
        action="store_true",
        dest="web_search",
        help="Enable Claude's native WebSearch tool.",
    )
    parser.add_argument(
        "--code-exec",
        action="store_true",
        dest="code_exec",
        help="Enable code execution tools (Bash, Write, Edit, etc.). Creates ./demo_output/.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(_run_demo(args))
