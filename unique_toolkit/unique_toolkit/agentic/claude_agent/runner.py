"""
Claude Agent runner — main entry point for executing a Claude Agent SDK call.

This module will contain:
- ClaudeAgentRunner: the top-level runner class returned by _build_claude_agent()
  in unique_ai_builder.py. Its run() method drives the entire agent turn:
  workspace setup → claude-agent-sdk query loop → streaming → post-processing.
- _build_options(): constructs ClaudeAgentOptions from ClaudeAgentConfig and
  the injected MCP tool list.
- _inject_common_components(): wires EvaluationManager, PostprocessorManager,
  and ReferenceManager into the runner so they are called after Claude exits.

Design constraint: cwd and env are always passed as parameters; no hardcoded
local paths except the workspace base dir constant. This keeps the runner
sandbox-agnostic for WI-4 / A3 future work.
"""


class ClaudeAgentRunner:
    """Entry-point runner for Claude Agent SDK integration.

    Returned by _build_claude_agent() in unique_ai_builder.py when
    experimental.claude_agent_config is set on the incoming UniqueAIConfig.

    TODO: Implement run() — see decision A1 / Option C in
    .local-dev/claude_sdk_integration/proposals/001-streaming-contract-v2.md
    """

    async def run(self) -> None:  # noqa: B027
        raise NotImplementedError
