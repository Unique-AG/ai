"""Terminal output formatting for web search results."""

from __future__ import annotations

from unique_web_search.services.search_engine.schema import WebSearchResult


def format_websearch_results(
    results: list[WebSearchResult],
    crawled_contents: list[str] | None = None,
    content_preview_length: int = 200,
) -> str:
    """Format web search results for terminal display.

    Args:
        results: Search results from the engine.
        crawled_contents: Optional crawled page contents (parallel to results).
        content_preview_length: Max chars of crawled content to show per result.
    """
    if not results:
        return "No results found."

    lines: list[str] = [f"Found {len(results)} result(s):\n"]

    for i, result in enumerate(results):
        lines.append(f"  {i + 1}. {result.title}")
        lines.append(f"     {result.url}")

        if result.snippet:
            snippet = result.snippet.replace("\n", " ").strip()
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."
            lines.append(f"     {snippet}")

        if crawled_contents and i < len(crawled_contents):
            content = crawled_contents[i].strip()
            if content:
                preview = content[:content_preview_length].replace("\n", " ").strip()
                if len(content) > content_preview_length:
                    preview += "..."
                lines.append("     --- crawled content ---")
                lines.append(f"     {preview}")

        lines.append("")

    return "\n".join(lines).rstrip()
