"""Normalize raw ``ToolBuildConfig`` dict input before Pydantic field validation.

This module sits between :class:`~unique_toolkit.agentic.tools.config.ToolBuildConfig`
and :class:`~unique_toolkit.agentic.tools.factory.ToolFactory` so the envelope model
does not import the factory. The factory (registry) depends on schemas only at import
time; this adapter depends on the factory to resolve ``name`` → concrete config class
when ``configuration`` is still a plain dict.

:class:`ExtendedSubAgentToolConfig` is imported **inside** the sub-agent branch only:
``a2a.config`` pulls in postprocessing → jinja → ``Tool``, which would cycle if imported
at module load when ``config`` is still initializing.

Imports of ``ToolFactory`` and ``MCPToolConfig`` are **inside** this function: loading
``mcp.models`` runs ``mcp/__init__.py``, which imports ``Tool`` before ``tool.py`` has
finished if done at module import time.
"""

from __future__ import annotations

from typing import Any


def normalize_tool_build_payload(value: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``value`` with ``configuration`` coerced where needed.

    Handles ``tool_type`` defaulting from ``name``, MCP passthrough, sub-agent
    configs, and registered tools (dict or pre-built instance) via
    :meth:`ToolFactory.resolve_tool_configuration`.
    """
    from unique_toolkit.agentic.tools.factory import ToolFactory
    from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig

    if (
        not any(k in value for k in ("tool_type", "toolType"))
        and value.get("name") is not None
    ):
        value = {**value, "tool_type": value["name"]}

    is_mcp_tool = value.get("mcp_source_id", "") != ""
    mcp_configuration = value.get("configuration", {})

    if isinstance(mcp_configuration, MCPToolConfig) and mcp_configuration.mcp_source_id:
        return value
    if is_mcp_tool:
        return value

    is_sub_agent_tool = value.get("is_sub_agent") or value.get("isSubAgent") or False

    configuration = value.get("configuration", {})

    if is_sub_agent_tool:
        from unique_toolkit.agentic.tools.a2a.config import ExtendedSubAgentToolConfig

        config = ExtendedSubAgentToolConfig.model_validate(configuration)
    else:
        config = ToolFactory.resolve_tool_configuration(
            value["name"],
            configuration,
        )
    return {**value, "configuration": config}
