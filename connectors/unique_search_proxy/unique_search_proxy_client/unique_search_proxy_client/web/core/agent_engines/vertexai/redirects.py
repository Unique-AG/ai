from __future__ import annotations

from httpx import AsyncClient
from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput
from unique_search_proxy_core.url_safety import UrlSafetyService


async def resolve_vertex_result_urls(
    answer: str,
    *,
    http_client: AsyncClient,
) -> str:
    """Resolve structured Vertex result URLs through Search Proxy URL safety."""
    try:
        output = AgentSearchOutput.model_validate_json(answer)
    except ValueError:
        return answer

    outcomes = await UrlSafetyService.validate_urls_individually(
        [result.source_url for result in output.results],
        redirect_http_client=http_client,
    )
    for result, outcome in zip(output.results, outcomes, strict=True):
        if outcome.resolved is not None:
            result.source_url = outcome.resolved.normalized_url

    return output.model_dump_json()


__all__ = ["resolve_vertex_result_urls"]
