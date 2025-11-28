from google.genai import types
from pydantic import BaseModel

from unique_web_search.services.search_engine.utils.vertexai.prompts import (
    VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
)


def get_vertex_grounding_config(
    *,
    system_instruction: str,
    entreprise_search: bool = False,
) -> types.GenerateContentConfig:
    if entreprise_search:
        grounding_tool = types.Tool(enterprise_web_search=types.EnterpriseWebSearch())
    else:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

    return types.GenerateContentConfig(
        tools=[grounding_tool], system_instruction=system_instruction
    )


def get_vertex_structured_results_config(
    *,
    response_schema: type[BaseModel],
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=response_schema,
    )
