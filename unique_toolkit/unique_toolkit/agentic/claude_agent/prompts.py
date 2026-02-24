"""
System prompt construction for Claude Agent SDK integration.

This module will contain helpers for rendering Jinja2 system prompt templates
for Claude. No new prompt templates are needed: Abi's claude-agent-prompts.ts
(PR #20429) is an explicit port of the existing Python Jinja2 templates:

- unique_orchestrator/prompts/system_prompt.jinja2
- unique_orchestrator/prompts/generic_reference_prompt.jinja2

The Python implementation renders these templates directly. The reference
citation format ([source0], [source1]) and answer-style sections are already
in the templates and work for Claude without modification.

When system_prompt_override is set in ClaudeAgentConfig, the rendered template
is replaced entirely. custom_instructions and user_instructions are appended
as additional sections.
"""
