"""Web-search command: query a search engine and crawl URLs through the API.

Mirrors the assistants-core ``unique-websearch`` CLI (search + crawl) but
talks to the Unique platform via :class:`unique_sdk.WebSearch` /
:class:`unique_sdk.WebCrawl` instead of instantiating engines / crawlers
locally. Engine and crawler are resolved server-side from
``ACTIVE_SEARCH_ENGINES`` / ``ACTIVE_INHOUSE_CRAWLERS``; per-call
overrides use the same discriminated-union shapes the server expects.

Override precedence (highest first):
    1. Inline ``--engine-config`` / ``--crawler-config`` / ``--fetch-size`` flags
    2. Config file (``--config``, ``$UNIQUE_WEBSEARCH_CONFIG``, or
       ``~/.unique-websearch.json``) — shape-compatible with the
       reference ``unique-websearch`` CLI
    3. Server-side defaults (``ACTIVE_SEARCH_ENGINES`` etc.)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

import unique_sdk
from unique_sdk.cli.commands._citation_manifest import (
    UnsafeRefsLogPathError,
    _append_turn_refs_manifest_entry,
    _locked_turn_refs_manifest,
    _read_turn_refs_manifest,
)
from unique_sdk.cli.commands.web_search_config import (
    ConfigOverrides,
    WebSearchCLIConfigError,
    load_overrides,
)
from unique_sdk.cli.state import ShellState

_LOGGER = logging.getLogger(__name__)

DEFAULT_PARALLEL = 10
_SNIPPET_PREVIEW_LIMIT = 200
_CONTENT_PREVIEW_LIMIT = 500
_WEB_REFS_LOG_RELATIVE_PATH = Path(".unique") / "web-refs.jsonl"
_WEB_REFS_LOCK_FILENAME = "web-refs.lock"

WEB_SEARCH_ERROR_PREFIX = "web-search:"
WEB_CRAWL_ERROR_PREFIX = "web-crawl:"


def _source_numbers_by_url(entries: list[dict[str, Any]]) -> dict[str, int]:
    by_url: dict[str, int] = {}
    for entry in entries:
        url = entry.get("url")
        source_number = entry.get("sourceNumber")
        if isinstance(url, str) and isinstance(source_number, int):
            by_url.setdefault(url.strip(), source_number)
    return by_url


def _next_source_number(entries: list[dict[str, Any]]) -> int:
    source_numbers = [
        entry["sourceNumber"]
        for entry in entries
        if isinstance(entry.get("sourceNumber"), int)
    ]
    return max(source_numbers, default=0) + 1


def _fetch_error_message(content: Any, url: str) -> str | None:
    """Extract the failure message when ``content`` is a crawl-error payload.

    The web-search backend reports per-URL fetch failures in-band: proxy
    crawlers return ``"URL: <url>\\n\\nError: <message>"``, Tavily/Jina a
    bare ``"Error: <message>"``. Returns the message for error payloads and
    ``None`` for real page content.
    """
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    url_prefix = f"URL: {url}"
    if stripped.startswith(url_prefix):
        stripped = stripped[len(url_prefix) :].lstrip()
    if stripped.startswith("Error:"):
        return stripped[len("Error:") :].strip() or "unknown crawl error"
    return None


def _annotate_web_results_for_citations(
    payload: dict[str, Any],
    *,
    refs_log_path: Path | None = None,
) -> dict[str, Any]:
    """Add per-turn web citation numbers and append the refs manifest.

    Web results are deduped by URL: the same URL keeps the same
    ``sourceNumber`` across consecutive ``search`` / ``crawl`` calls in
    the same turn, so the crawled-content row carries the same citation
    marker the search-snippet row already advertised.

    Crawl-error payloads (``_fetch_error_message``) are kept out of the
    manifest's ``content`` field and recorded under ``error`` instead: the
    platform grounds the hallucination judge on manifest ``content``, so an
    in-band fetch error stored as content turns a correctly cited,
    snippet-verifiable source into a false "high hallucination" verdict
    (UN-23356). The on-screen result still shows the error text so the
    agent can react to the failed fetch.
    """
    refs_log_path = refs_log_path or (Path.cwd() / _WEB_REFS_LOG_RELATIVE_PATH)
    with _locked_turn_refs_manifest(
        refs_log_path, lock_filename=_WEB_REFS_LOCK_FILENAME
    ):
        entries = _read_turn_refs_manifest(refs_log_path)
        source_numbers_by_url = _source_numbers_by_url(entries)
        annotated = dict(payload)
        annotated_results: list[dict[str, Any]] = []

        for raw_result in payload.get("results") or []:
            if not isinstance(raw_result, dict):
                _LOGGER.warning(
                    "skipping non-dict web result while annotating citations: %r",
                    raw_result,
                )
                continue
            result = dict(raw_result)
            url = str(result.get("url") or "").strip()
            if not url:
                annotated_results.append(result)
                continue

            source_number = source_numbers_by_url.get(url)
            if source_number is None:
                source_number = _next_source_number(entries)
                source_numbers_by_url[url] = source_number
                entries.append({"sourceNumber": source_number, "url": url})

            result["sourceNumber"] = source_number
            result["citation"] = f"websource{source_number}"
            content = result.get("content")
            error = result.get("error")
            fetch_error = _fetch_error_message(content, url)
            if fetch_error is not None:
                content = None
                error = error or fetch_error
            manifest_entry = {
                "sourceNumber": source_number,
                "url": url,
                "title": result.get("title"),
                "snippet": result.get("snippet"),
                "content": content,
                "error": error,
            }
            _append_turn_refs_manifest_entry(refs_log_path, manifest_entry)
            annotated_results.append(result)

        annotated["results"] = annotated_results
        return annotated


def _row_label_for_result(result: dict[str, Any], fallback_index: int) -> int:
    """Return the human row label for a single result.

    In the happy path ``_annotate_web_results_for_citations`` runs before
    the formatter and stamps every dict result with an ``int``
    ``sourceNumber`` that matches the ``[websourceN]`` marker the LLM is
    told to emit; the formatter then surfaces that same number as the row
    label so the on-screen list and the citation namespace agree.

    The ``fallback_index`` branch only fires when ``sourceNumber`` is
    missing or non-int — i.e. a contract violation from the annotator
    (or annotation was skipped). We never want the formatter to crash,
    but the fallback row label deliberately *will not* match a
    ``[websourceN]`` marker, so the agent would cite a number that is
    not in the manifest. Warn loudly so the bug is observable instead of
    silently degrading citations.
    """
    source_number = result.get("sourceNumber")
    if isinstance(source_number, int):
        return source_number
    _LOGGER.warning(
        "web result is missing a numeric `sourceNumber` after citation "
        "annotation; falling back to row index %d. URL=%r — this row will "
        "not be citable as [websourceN].",
        fallback_index,
        result.get("url"),
    )
    return fallback_index


def _format_search_results(payload: dict[str, Any]) -> str:
    """Render a /web-search-api/search response for terminal display."""
    results: list[dict[str, Any]] = payload.get("results", [])
    engine = payload.get("engine", "unknown")
    query = payload.get("query", "")

    if not results:
        return f"No results found (engine={engine}, query={query!r})."

    lines: list[str] = [f"engine: {engine}    query: {query!r}"]
    lines.append(f"Found {len(results)} result(s):\n")

    for i, result in enumerate(results, start=1):
        title = result.get("title", "")
        url = result.get("url", "")
        snippet = (result.get("snippet") or "").replace("\n", " ").strip()
        content = result.get("content") or ""

        citation = result.get("citation")
        citation_suffix = f" [{citation}]" if citation else ""
        row_label = _row_label_for_result(result, i)
        lines.append(f"  {row_label}. {title}{citation_suffix}")
        lines.append(f"     {url}")

        if snippet:
            if len(snippet) > _SNIPPET_PREVIEW_LIMIT:
                snippet = snippet[: _SNIPPET_PREVIEW_LIMIT - 3] + "..."
            lines.append(f"     {snippet}")

        if content:
            lines.append(f"     [{len(content)} chars of content]")

        lines.append("")

    return "\n".join(lines).rstrip()


def _format_search_results_json(payload: dict[str, Any]) -> str:
    """Stable JSON projection — drops the SDK envelope ``object`` discriminator."""
    return json.dumps(
        {
            "engine": payload.get("engine"),
            "query": payload.get("query"),
            "results": payload.get("results", []),
        },
        indent=2,
        ensure_ascii=False,
    )


def _format_crawl_results(payload: dict[str, Any]) -> str:
    """Render a /web-search-api/crawl response for terminal display."""
    results: list[dict[str, Any]] = payload.get("results", [])
    crawler = payload.get("crawler", "unknown")

    if not results:
        return f"No crawl results (crawler={crawler})."

    lines: list[str] = [f"crawler: {crawler}"]
    lines.append(f"Crawled {len(results)} URL(s):\n")

    for i, entry in enumerate(results, start=1):
        url = entry.get("url", "")
        content = entry.get("content") or ""
        error = entry.get("error")

        citation = entry.get("citation")
        citation_suffix = f" [{citation}]" if citation else ""
        row_label = _row_label_for_result(entry, i)
        lines.append(f"  {row_label}. {url}{citation_suffix}")
        if error:
            lines.append(f"     ERROR: {error}")
        elif content.strip():
            lines.append(f"     [{len(content)} chars]")
            preview = content[:_CONTENT_PREVIEW_LIMIT].replace("\n", " ").strip()
            if len(content) > _CONTENT_PREVIEW_LIMIT:
                preview += "..."
            lines.append(f"     {preview}")
        else:
            lines.append("     (empty)")

        lines.append("")

    return "\n".join(lines).rstrip()


def _format_crawl_results_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "crawler": payload.get("crawler"),
            "results": payload.get("results", []),
        },
        indent=2,
        ensure_ascii=False,
    )


def _payload_from_resource(resource: Any) -> dict[str, Any]:
    """Extract a plain dict envelope from a UniqueObject-style SDK response.

    The SDK base class exposes ``.to_dict_recursive()``; falling back to
    raw attribute access keeps this resilient to lighter mock responses
    in tests.
    """
    to_dict = getattr(resource, "to_dict_recursive", None)
    if callable(to_dict):
        return cast(dict[str, Any], to_dict())
    if isinstance(resource, dict):
        return cast(dict[str, Any], resource)
    # Last-resort: rebuild from the few fields we care about.
    return {
        key: getattr(resource, key)
        for key in ("engine", "query", "crawler", "results")
        if hasattr(resource, key)
    }


def _parse_engine_config(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--engine-config is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--engine-config must be a JSON object")
    return parsed


def _parse_crawler_config(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--crawler-config is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--crawler-config must be a JSON object")
    return parsed


def _load_file_overrides(config_path: str | None) -> ConfigOverrides | str:
    """Load config-file overrides, returning a string error on failure.

    Returns either a populated :class:`ConfigOverrides` (possibly empty
    when no file is discovered) or a ``"web-search: ..."`` error string
    that callers can return verbatim.
    """
    try:
        return load_overrides(config_path)
    except WebSearchCLIConfigError as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"


def cmd_web_search(
    state: ShellState,
    query: str,
    fetch_size: int | None = None,
    include_content: bool = False,
    engine_config_raw: str | None = None,
    crawler_config_raw: str | None = None,
    output_json: bool = False,
    config_path: str | None = None,
    chat_id: str | None = None,
) -> str:
    """Run a web search via the public API.

    Args:
        state: Shell state carrying user/company credentials.
        query: Search query string.
        fetch_size: Override the engine's default ``fetchSize``. Wins
            over any value loaded from a config file.
        include_content: When ``True``, populate ``result.content`` via
            the configured crawler when the engine requires scraping.
        engine_config_raw: Optional JSON string overriding the
            ``searchEngineConfig`` discriminated union (e.g.
            ``{"searchEngineName": "Google", "fetchSize": 5}``). Wins
            over the config file's full-platform engine block.
        crawler_config_raw: Optional JSON string overriding the
            ``crawlerConfig`` discriminated union. Wins over the config
            file's full-platform crawler block.
        config_path: Optional path to a JSON config file shape-compatible
            with the reference ``unique-websearch`` CLI (full
            ``WebSearchConfig`` payload or simple-overrides). When
            ``None``, falls back to ``$UNIQUE_WEBSEARCH_CONFIG`` and
            then ``~/.unique-websearch.json``.
        output_json: When ``True``, return a JSON envelope instead of a
            human-friendly table.
        chat_id: Optional chat id this call is made on behalf of. When
            set, the space's Web Search toggle is enforced server-side.
    """
    file_overrides = _load_file_overrides(config_path)
    if isinstance(file_overrides, str):
        return file_overrides

    try:
        engine_override = _parse_engine_config(engine_config_raw)
        crawler_override = _parse_crawler_config(crawler_config_raw)
    except ValueError as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"

    if engine_override is None:
        engine_override = file_overrides.engine_config
    if crawler_override is None:
        crawler_override = file_overrides.crawler_config
    if fetch_size is None:
        fetch_size = file_overrides.fetch_size

    params: dict[str, Any] = {"query": query}
    if fetch_size is not None:
        params["fetchSize"] = fetch_size
    if include_content:
        params["includeContent"] = True
    if engine_override is not None:
        params["searchEngineConfig"] = engine_override
    if crawler_override is not None:
        params["crawlerConfig"] = crawler_override
    if chat_id:
        params["chatId"] = chat_id

    try:
        resource = unique_sdk.WebSearch.search(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
    except (ValueError, unique_sdk.APIError) as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"

    try:
        payload = _annotate_web_results_for_citations(_payload_from_resource(resource))
    except UnsafeRefsLogPathError as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"
    if output_json:
        return _format_search_results_json(payload)
    return _format_search_results(payload)


def cmd_web_crawl(
    state: ShellState,
    urls: list[str],
    parallel: int = DEFAULT_PARALLEL,
    crawler_config_raw: str | None = None,
    output_json: bool = False,
    config_path: str | None = None,
    chat_id: str | None = None,
) -> str:
    """Crawl a list of URLs via the public API.

    Args:
        state: Shell state carrying user/company credentials.
        urls: List of URLs to crawl.
        parallel: Number of URLs the server should crawl concurrently per
            batch (must be ``>= 1``).
        crawler_config_raw: Optional JSON string overriding the
            ``crawlerConfig`` discriminated union. Wins over the config
            file's full-platform crawler block.
        config_path: Optional path to a JSON config file shape-compatible
            with the reference ``unique-websearch`` CLI. See
            :func:`cmd_web_search` for resolution rules.
        output_json: When ``True``, return a JSON envelope instead of a
            human-friendly table.
        chat_id: Optional chat id this call is made on behalf of. When
            set, the space's Web Search toggle is enforced server-side.
    """
    if not urls:
        return f"{WEB_CRAWL_ERROR_PREFIX} no URLs provided. Pass URLs as arguments or use --stdin."
    if parallel < 1:
        return f"{WEB_CRAWL_ERROR_PREFIX} --parallel must be >= 1 (got {parallel})."

    try:
        file_overrides = load_overrides(config_path)
    except WebSearchCLIConfigError as exc:
        return f"{WEB_CRAWL_ERROR_PREFIX} {exc}"

    try:
        crawler_override = _parse_crawler_config(crawler_config_raw)
    except ValueError as exc:
        return f"{WEB_CRAWL_ERROR_PREFIX} {exc}"

    if crawler_override is None:
        crawler_override = file_overrides.crawler_config

    params: dict[str, Any] = {"urls": list(urls), "parallel": parallel}
    if crawler_override is not None:
        params["crawlerConfig"] = crawler_override
    if chat_id:
        params["chatId"] = chat_id

    try:
        resource = unique_sdk.WebCrawl.crawl(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
    except (ValueError, unique_sdk.APIError) as exc:
        return f"{WEB_CRAWL_ERROR_PREFIX} {exc}"

    try:
        payload = _annotate_web_results_for_citations(_payload_from_resource(resource))
    except UnsafeRefsLogPathError as exc:
        return f"{WEB_CRAWL_ERROR_PREFIX} {exc}"
    if output_json:
        return _format_crawl_results_json(payload)
    return _format_crawl_results(payload)


def is_error_output(output: str) -> bool:
    """Return ``True`` when ``output`` is a CLI error message.

    Used by the Click layer to translate a returned error string into a
    non-zero exit code without changing the existing string-returning
    contract of the ``cmd_*`` functions.
    """
    return output.startswith(WEB_SEARCH_ERROR_PREFIX) or output.startswith(
        WEB_CRAWL_ERROR_PREFIX
    )
