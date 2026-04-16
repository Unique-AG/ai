from google.genai import types
from pydantic import BaseModel

from unique_web_search.services.search_engine.utils.shared_models import (
    RESPONSE_RULE,
)
from unique_web_search.services.search_engine.utils.vertexai.prompts import (
    VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
)


def _get_grounding_tool(
    use_entreprise_search: bool = False,
) -> types.Tool:
    if use_entreprise_search:
        return types.Tool(enterprise_web_search=types.EnterpriseWebSearch())
    return types.Tool(google_search=types.GoogleSearch())


def get_vertex_grounding_config(
    *,
    system_instruction: str,
    entreprise_search: bool = False,
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[_get_grounding_tool(entreprise_search)],
        system_instruction=system_instruction,
    )


def get_vertex_grounding_with_structured_output_config(
    *,
    generation_instructions: str,
    entreprise_search: bool = False,
) -> types.GenerateContentConfig:
    system_instruction = generation_instructions + "\n\n" + RESPONSE_RULE
    return types.GenerateContentConfig(
        tools=[_get_grounding_tool(entreprise_search)],
        system_instruction=system_instruction,
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
