from unique_web_search.services.search_engine.utils.vertexai.client import (
    get_vertex_client,
)
from unique_web_search.services.search_engine.utils.vertexai.config import (
    get_vertex_grounding_config,
    get_vertex_structured_results_config,
)
from unique_web_search.services.search_engine.utils.vertexai.gemini import (
    generate_content,
)
from unique_web_search.services.search_engine.utils.vertexai.prompts import (
    VERTEX_GROUNDING_SYSTEM_INSTRUCTION,
    VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
)
from unique_web_search.services.search_engine.utils.vertexai.response_handler import (
    PostProcessFunction,
    add_citations,
    parse_to_structured_results,
)

__all__ = [
    "get_vertex_client",
    "get_vertex_grounding_config",
    "get_vertex_structured_results_config",
    "generate_content",
    "PostProcessFunction",
    "parse_to_structured_results",
    "add_citations",
    "VERTEX_GROUNDING_SYSTEM_INSTRUCTION",
    "VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION",
]
