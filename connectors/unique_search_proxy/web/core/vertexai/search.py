from core.vertexai.client import (
    get_vertex_client,
)
from core.vertexai.config import (
    get_vertex_grounding_config,
    get_vertex_structured_results_config,
)
from core.vertexai.gemini import (
    generate_content,
)
from core.vertexai.response_handler import (
    PostProcessFunction,
    add_citations,
    parse_to_structured_results,
)
from core.schema import WebSearchResult, WebSearchResults, camelized_model_config
from core.vertexai.helpers import resolve_all
from pydantic import BaseModel


class VertexAiParams(BaseModel):
    model_config = camelized_model_config

    model_name: str = "gemini-2.5-flash"
    entreprise_search: bool = False
    system_instruction: str | None = None
    resolve_urls: bool = True


class VertexAISearchEngine:
    def __init__(
        self,
        params: VertexAiParams,
    ):
        self.model_name = params.model_name
        self.entreprise_search = params.entreprise_search
        self.system_instruction = params.system_instruction
        self.resolve_urls = params.resolve_urls

    async def search(self, query: str) -> list[WebSearchResult]:
        client = get_vertex_client()
        answer_with_citations = await generate_content(
            client=client,
            model_name=self.model_name,
            config=get_vertex_grounding_config(
                system_instruction=self.system_instruction,
                entreprise_search=self.entreprise_search,
            ),
            contents=query,
            post_process_function=PostProcessFunction[str](add_citations),
        )

        # Generate the structured results
        structured_results = await generate_content(
            client=client,
            model_name=self.model_name,
            config=get_vertex_structured_results_config(
                system_instruction=None,
                response_schema=WebSearchResults,
            ),
            contents=answer_with_citations,
            post_process_function=PostProcessFunction[WebSearchResults](
                parse_to_structured_results,
                response_schema=WebSearchResults,
            ),
        )
        if self.resolve_urls:
            structured_results = await resolve_all(structured_results)

        return structured_results.results
