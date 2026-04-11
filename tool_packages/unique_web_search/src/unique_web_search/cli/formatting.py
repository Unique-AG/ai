"""Terminal output formatting for search and crawl results."""

from __future__ import annotations

import json

from unique_web_search.services.search_engine.schema import WebSearchResult


def format_search_results(results: list[WebSearchResult]) -> str:
    """Format search results for terminal display (URLs + snippets)."""
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

        lines.append("")

    return "\n".join(lines).rstrip()


def format_search_results_json(results: list[WebSearchResult]) -> str:
    """Format search results as JSON for piping to other tools."""
    entries = [
        {
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet or "",
        }
        for r in results
    ]
    return json.dumps(entries, indent=2, ensure_ascii=False)


def format_crawl_results(
    results: list[tuple[str, str, str | None]],
) -> str:
    """Format crawl results for terminal display.

    Each entry is a (url, content, error) triple.
    """
    if not results:
        return "No crawl results."

    lines: list[str] = [f"Crawled {len(results)} URL(s):\n"]

    for i, (url, content, error) in enumerate(results):
        lines.append(f"  {i + 1}. {url}")
        if error:
            lines.append(f"     ERROR: {error}")
        elif content.strip():
            lines.append(f"     [{len(content)} chars]")
            preview = content[:500].replace("\n", " ").strip()
            if len(content) > 500:
                preview += "..."
            lines.append(f"     {preview}")
        else:
            lines.append("     (empty)")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_crawl_results_json(
    results: list[tuple[str, str, str | None]],
) -> str:
    """Format crawl results as JSON."""
    entries = [
        {
            "url": url,
            "content": content,
            "error": error,
        }
        for url, content, error in results
    ]
    return json.dumps(entries, indent=2, ensure_ascii=False)
