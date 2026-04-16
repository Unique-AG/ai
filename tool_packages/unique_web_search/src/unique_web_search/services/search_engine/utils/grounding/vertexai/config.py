from google.genai import types

from unique_web_search.services.search_engine.utils.grounding import (
    RESPONSE_RULE,
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
