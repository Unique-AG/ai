from google.genai import types
from pydantic import BaseModel

from core.vertexai.prompts import (
    VERTEX_GROUNDING_SYSTEM_INSTRUCTION,
    VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
)


def get_vertex_grounding_config(
    *,
    system_instruction: str | None,
    entreprise_search: bool = False,
) -> types.GenerateContentConfig:
    system_instruction = system_instruction or VERTEX_GROUNDING_SYSTEM_INSTRUCTION

    if entreprise_search:
        grounding_tool = types.Tool(enterprise_web_search=types.EnterpriseWebSearch())
    else:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

    return types.GenerateContentConfig(
        tools=[grounding_tool], system_instruction=system_instruction
    )


def get_vertex_structured_results_config(
    *,
    system_instruction: str | None,
    response_schema: type[BaseModel],
) -> types.GenerateContentConfig:
    system_instruction = (
        system_instruction or VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION
    )
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=response_schema,
    )
