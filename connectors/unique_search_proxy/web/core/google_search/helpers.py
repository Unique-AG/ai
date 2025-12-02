from httpx import Response
from core.schema import WebSearchResult


def map_google_search_response_to_web_search_result(
    response: Response,
) -> list[WebSearchResult]:
    """Clean the response from the search engine."""
    results = response.json()
    return [
        WebSearchResult(
            url=item["link"],
            snippet=item["snippet"],
            title=item.get("title", item.get("htmlTitle", "")),
        )
        for item in results["items"]
    ]
