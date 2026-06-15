from __future__ import annotations

import json

from pydantic import BaseModel


def build_json_output_format_rule(output_schema: type[BaseModel]) -> str:
    """Instruction block that pins agent output to a JSON schema (Bing path)."""
    schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
    return (
        "## Output Format\n"
        "Respond with a JSON object matching the schema below. "
        "Do NOT include any text outside the JSON.\n\n"
        f"JSON Schema:\n```json\n{schema_json}\n```"
    )


def build_agent_instructions(
    *,
    generation_instructions: str,
    output_schema: type[BaseModel],
) -> str:
    """Merge generation instructions with structured-output formatting rules."""
    return (
        f"{generation_instructions.rstrip()}\n\n"
        f"{build_json_output_format_rule(output_schema)}"
    )


__all__ = ["build_agent_instructions", "build_json_output_format_rule"]
