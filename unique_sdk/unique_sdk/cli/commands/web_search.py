"""Web-search command: query a search engine and crawl URLs through the API.

Mirrors the assistants-core ``unique-websearch`` CLI (search + crawl) but
talks to the Unique platform via :class:`unique_sdk.WebSearch` /
:class:`unique_sdk.WebCrawl` instead of instantiating engines / crawlers
locally. Engine and crawler are resolved server-side from
``ACTIVE_SEARCH_ENGINES`` / ``ACTIVE_INHOUSE_CRAWLERS``; per-call
overrides use the same discriminated-union shapes the server expects.

When the call carries a chat id, the batch is sent once to
``POST /web-search-api/review`` before any search. A space with query
review off searches as before. A space with review on does not search
until the user approves the queries; this command does not poll.

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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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
from unique_sdk.cli.workspace import manifest_path as workspace_manifest_path

_LOGGER = logging.getLogger(__name__)

DEFAULT_PARALLEL = 10
MAX_SEARCH_QUERIES = 8
SEARCH_CONCURRENCY = MAX_SEARCH_QUERIES
_SNIPPET_PREVIEW_LIMIT = 200
_CONTENT_PREVIEW_LIMIT = 500
_WEB_REFS_LOG_RELATIVE_PATH = Path(".unique") / "web-refs.jsonl"
_WEB_REFS_LOCK_FILENAME = "web-refs.lock"

WEB_SEARCH_ERROR_PREFIX = "web-search:"
WEB_CRAWL_ERROR_PREFIX = "web-crawl:"

# The server clamps a review form's lifetime to this. One supervised
# ``elicit wait`` of this length covers every configured review window.
QUERY_REVIEW_WAIT_TIMEOUT_SECONDS = 300
USER_APPROVED_QUERIES_NOTICE = "These are the user-approved queries."
_REVIEW_TERMINAL_ERRORS = {
    "DECLINED": (
        "The user declined the web search queries. "
        "Tell the user that the web search did not run."
    ),
    "CANCELLED": (
        "The user did not approve the web search queries in time. "
        "Tell the user that the web search did not run."
    ),
    "EXPIRED": (
        "The user did not approve the web search queries in time. "
        "Tell the user that the web search did not run."
    ),
}


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


def _fetch_error_message(content: Any) -> str | None:
    """Extract the failure message when ``content`` is a crawl-error payload.

    The web-search backend reports per-URL fetch failures in-band: proxy
    crawlers return ``"URL: <url>\\n\\nError: <message>"``, Tavily/Jina a
    bare ``"Error: <message>"``. Returns the message for error payloads and
    ``None`` for real page content.

    Any leading ``URL: …`` line is skipped without matching it against the
    result's own URL — redirects or normalization can make the reported URL
    differ from the requested one.
    """
    if not isinstance(content, str):
        return None
    stripped = content.strip()
    first_line, _, rest = stripped.partition("\n")
    if first_line.startswith("URL:"):
        stripped = rest.lstrip()
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
    refs_log_path = refs_log_path or workspace_manifest_path(
        _WEB_REFS_LOG_RELATIVE_PATH
    )
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
            fetch_error = _fetch_error_message(content)
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


def _search_results_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Stable projection — drops the SDK envelope ``object`` discriminator."""
    return {
        "engine": payload.get("engine"),
        "query": payload.get("query"),
        "results": payload.get("results", []),
    }


def _format_search_results_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        _search_results_projection(payload),
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
    *,
    refs_log_path: Path | None = None,
    message_id: str | None = None,
    review_id: str | None = None,
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
            set, the space's Web Search toggle is enforced server-side
            and query review runs once before the search.
        refs_log_path: The per-turn web citation manifest. When ``None``,
            it resolves from the workspace root.
        message_id: Optional assistant message the review form is attached
            to. Sent as ``messageId`` on the review call only; the search
            endpoint does not accept it.
        review_id: Id of a review the user already answered. The query is
            searched with that id. Without a chat id this is ignored.

    Returns:
        str: The formatted search, a pending-review instruction, or a
        ``web-search:`` error. A single query keeps today's text unless
        the user approved a different query.
    """
    return _execute_web_searches(
        state,
        [query],
        single_format=True,
        fetch_size=fetch_size,
        include_content=include_content,
        engine_config_raw=engine_config_raw,
        crawler_config_raw=crawler_config_raw,
        output_json=output_json,
        config_path=config_path,
        chat_id=chat_id,
        refs_log_path=refs_log_path,
        message_id=message_id,
        review_id=review_id,
    )


def _search_request_options(
    *,
    fetch_size: int | None,
    include_content: bool,
    engine_config_raw: str | None,
    crawler_config_raw: str | None,
    config_path: str | None,
    chat_id: str | None,
) -> dict[str, Any] | str:
    """Build the request fields shared by every query, or return an error string."""
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

    options: dict[str, Any] = {}
    if fetch_size is not None:
        options["fetchSize"] = fetch_size
    if include_content:
        options["includeContent"] = True
    if engine_override is not None:
        options["searchEngineConfig"] = engine_override
    if crawler_override is not None:
        options["crawlerConfig"] = crawler_override
    if chat_id:
        options["chatId"] = chat_id
    return options


def _fetch_search_payload(
    state: ShellState,
    query: str,
    options: dict[str, Any],
) -> dict[str, Any] | str:
    """Run one search request; return the payload, or an error string."""
    try:
        resource = unique_sdk.WebSearch.search(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            query=query,
            **options,
        )
    except (ValueError, unique_sdk.UniqueError) as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"
    return _payload_from_resource(resource)


def _nonempty(value: str | None) -> str | None:
    """Return ``value`` stripped, or ``None`` when it is blank."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _query_count_error(queries: list[str]) -> str | None:
    """The batch-size error, or ``None`` when the batch may be searched."""
    if not queries:
        return f"{WEB_SEARCH_ERROR_PREFIX} no queries provided."
    if len(queries) > MAX_SEARCH_QUERIES:
        return (
            f"{WEB_SEARCH_ERROR_PREFIX} too many queries ({len(queries)}); "
            f"the limit is {MAX_SEARCH_QUERIES} per call. "
            "Split them across several calls."
        )
    return None


def _resource_dict(resource: Any) -> dict[str, Any]:
    """Read a SDK response as a dict, including the lighter test doubles."""
    to_dict = getattr(resource, "to_dict_recursive", None)
    if callable(to_dict):
        converted = to_dict()
        if isinstance(converted, dict):
            return converted
    if isinstance(resource, dict):
        return resource
    return {}


def _string_list(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def _pending_query_review_output(review_id: str) -> str:
    """Tell the agent how to wait, without searching or blocking.

    Args:
        review_id (str): Review id, which is also the elicitation id.

    Returns:
        str: Non-error instructions. The text does not include the queries.
    """
    return (
        "The user must approve the web search queries before they are sent.\n"
        f"Review id: {review_id}\n"
        "Wait for the answer, then search the approved queries:\n"
        f"unique-cli elicit wait {review_id} "
        f"--timeout {QUERY_REVIEW_WAIT_TIMEOUT_SECONDS}\n"
        f"unique-cli web-search search --review-id {review_id}"
    )


def _review_terminal_error(status: str) -> str:
    detail = _REVIEW_TERMINAL_ERRORS.get(
        status,
        (
            "The user did not approve the web search queries. "
            "Tell the user that the web search did not run."
        ),
    )
    return f"{WEB_SEARCH_ERROR_PREFIX} {detail}"


def _load_approved_queries(state: ShellState, review_id: str) -> list[str] | str:
    """Read ``responseContent.queries`` from the review elicitation.

    Uses the same ``Elicitation.get_elicitation`` call as
    ``cli/commands/elicitation.py``. A review the user has not answered
    yet returns the pending instructions instead of searching.

    Args:
        state (ShellState): Credentials for the get call.
        review_id (str): Elicitation id returned by the review endpoint.

    Returns:
        list[str] | str: The approved queries, or text to return as the
        command output.
    """
    try:
        elicitation = unique_sdk.Elicitation.get_elicitation(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            elicitation_id=review_id,
        )
    except (ValueError, unique_sdk.UniqueError) as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"

    payload = _resource_dict(elicitation)
    content = payload.get("responseContent")
    queries = _string_list(
        content.get("queries") if isinstance(content, dict) else None
    )
    if queries:
        return queries

    status = str(payload.get("status") or "").upper()
    if status in _REVIEW_TERMINAL_ERRORS:
        return _review_terminal_error(status)
    if status in {"", "PENDING", "CREATED"}:
        return _pending_query_review_output(review_id)
    return (
        f"{WEB_SEARCH_ERROR_PREFIX} review {review_id} has no approved queries. "
        "The search did not run."
    )


@dataclass(frozen=True)
class _SearchPlan:
    """Queries to search and the request fields shared by every query."""

    queries: list[str]
    options: dict[str, Any]
    notice: str | None


def _request_query_review(
    state: ShellState,
    *,
    chat_id: str,
    message_id: str | None,
    queries: list[str],
    options: dict[str, Any],
) -> _SearchPlan | str:
    """Ask once for the batch. Return a plan, or text to show instead.

    Args:
        state (ShellState): Credentials for the review call.
        chat_id (str): Chat whose space decides whether review is on.
        message_id (str | None): Assistant message the form is attached to.
        queries (list[str]): Proposed queries. Not logged.
        options (dict[str, Any]): Search fields already built for the batch.

    Returns:
        _SearchPlan | str: A plan whose queries are safe to search, or
        command output that means the search did not run.
    """
    try:
        if message_id:
            resource = unique_sdk.WebSearchReview.review(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                chatId=chat_id,
                messageId=message_id,
                queries=queries,
            )
        else:
            resource = unique_sdk.WebSearchReview.review(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                chatId=chat_id,
                queries=queries,
            )
    except (ValueError, unique_sdk.UniqueError) as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"

    payload = _resource_dict(resource)
    status = payload.get("status")
    if status == "NOT_REQUIRED":
        return _SearchPlan(queries=queries, options=options, notice=None)
    if status == "PENDING":
        review_id = payload.get("reviewId")
        if not isinstance(review_id, str) or not review_id:
            return (
                f"{WEB_SEARCH_ERROR_PREFIX} the query review is pending but "
                "no review id was returned. The search did not run."
            )
        return _pending_query_review_output(review_id)
    if status == "ACCEPTED":
        approved = _string_list(payload.get("queries"))
        if not approved:
            return (
                f"{WEB_SEARCH_ERROR_PREFIX} The user did not approve any "
                "web search queries. Tell the user that the web search did not run."
            )
        count_error = _query_count_error(approved)
        if count_error:
            return count_error
        review_id = payload.get("reviewId")
        if not isinstance(review_id, str) or not review_id:
            return (
                f"{WEB_SEARCH_ERROR_PREFIX} the accepted query review did not "
                "include a review id. The search did not run."
            )
        return _SearchPlan(
            queries=approved,
            options={**options, "reviewId": review_id},
            notice=USER_APPROVED_QUERIES_NOTICE,
        )
    if isinstance(status, str) and status in _REVIEW_TERMINAL_ERRORS:
        return _review_terminal_error(status)
    return (
        f"{WEB_SEARCH_ERROR_PREFIX} unexpected web search query review "
        f"status {status!r}. The search did not run."
    )


def _plan_web_search(
    state: ShellState,
    queries: list[str],
    *,
    fetch_size: int | None,
    include_content: bool,
    engine_config_raw: str | None,
    crawler_config_raw: str | None,
    config_path: str | None,
    chat_id: str | None,
    message_id: str | None,
    review_id: str | None,
) -> _SearchPlan | str:
    """Resolve review, then return the queries and options to search.

    Without ``chat_id`` the plan is today's search: no review call and no
    ``reviewId``. With ``review_id`` the review endpoint is not called again.
    """
    review_id = _nonempty(review_id)
    if chat_id and review_id and not queries:
        loaded = _load_approved_queries(state, review_id)
        if isinstance(loaded, str):
            return loaded
        queries = loaded

    count_error = _query_count_error(queries)
    if count_error:
        return count_error

    options = _search_request_options(
        fetch_size=fetch_size,
        include_content=include_content,
        engine_config_raw=engine_config_raw,
        crawler_config_raw=crawler_config_raw,
        config_path=config_path,
        chat_id=chat_id,
    )
    if isinstance(options, str):
        return options
    if not chat_id:
        return _SearchPlan(queries=queries, options=options, notice=None)
    if review_id:
        return _SearchPlan(
            queries=queries,
            options={**options, "reviewId": review_id},
            notice=None,
        )
    return _request_query_review(
        state,
        chat_id=chat_id,
        message_id=message_id,
        queries=queries,
        options=options,
    )


def _render_one_search(
    state: ShellState,
    query: str,
    options: dict[str, Any],
    *,
    output_json: bool,
    refs_log_path: Path | None,
) -> str:
    payload = _fetch_search_payload(state, query, options)
    if isinstance(payload, str):
        return payload
    try:
        payload = _annotate_web_results_for_citations(
            payload, refs_log_path=refs_log_path
        )
    except UnsafeRefsLogPathError as exc:
        return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"
    if output_json:
        return _format_search_results_json(payload)
    return _format_search_results(payload)


def _render_many_searches(
    state: ShellState,
    queries: list[str],
    options: dict[str, Any],
    *,
    output_json: bool,
    refs_log_path: Path | None,
) -> str:
    with ThreadPoolExecutor(
        max_workers=min(SEARCH_CONCURRENCY, len(queries))
    ) as executor:
        fetched = list(
            executor.map(
                lambda query: _fetch_search_payload(state, query, options), queries
            )
        )

    outcomes: list[dict[str, Any] | str] = []
    for item in fetched:
        if isinstance(item, str):
            outcomes.append(item)
            continue
        try:
            outcomes.append(
                _annotate_web_results_for_citations(item, refs_log_path=refs_log_path)
            )
        except UnsafeRefsLogPathError as exc:
            return f"{WEB_SEARCH_ERROR_PREFIX} {exc}"

    failures = [
        f"{query!r}: {outcome}"
        for query, outcome in zip(queries, outcomes, strict=True)
        if isinstance(outcome, str)
    ]
    if len(failures) == len(queries):
        return (
            f"{WEB_SEARCH_ERROR_PREFIX} all {len(queries)} queries failed.\n"
            + "\n".join(failures)
        )
    if output_json:
        return _format_many_search_results_json(queries, outcomes)
    return _format_many_search_results(queries, outcomes)


def _with_user_approved_notice(output: str, *, output_json: bool) -> str:
    """Mark a successful search as the queries the user approved.

    Text gains a leading sentence. JSON gains a ``notice`` field so the
    document stays parseable.
    """
    if not output_json:
        return f"{USER_APPROVED_QUERIES_NOTICE}\n\n{output}"
    parsed = json.loads(output)
    if isinstance(parsed, dict):
        noted: Any = {"notice": USER_APPROVED_QUERIES_NOTICE, **parsed}
    elif isinstance(parsed, list):
        noted = [
            {"notice": USER_APPROVED_QUERIES_NOTICE, **entry}
            if isinstance(entry, dict)
            else entry
            for entry in parsed
        ]
    else:
        return output
    return json.dumps(noted, indent=2, ensure_ascii=False)


def _execute_web_searches(
    state: ShellState,
    queries: list[str],
    *,
    single_format: bool,
    fetch_size: int | None,
    include_content: bool,
    engine_config_raw: str | None,
    crawler_config_raw: str | None,
    output_json: bool,
    config_path: str | None,
    chat_id: str | None,
    refs_log_path: Path | None,
    message_id: str | None,
    review_id: str | None,
) -> str:
    """Review the batch once, then search. One query keeps today's format."""
    plan = _plan_web_search(
        state,
        queries,
        fetch_size=fetch_size,
        include_content=include_content,
        engine_config_raw=engine_config_raw,
        crawler_config_raw=crawler_config_raw,
        config_path=config_path,
        chat_id=chat_id,
        message_id=message_id,
        review_id=review_id,
    )
    if isinstance(plan, str):
        return plan
    if single_format and len(plan.queries) == 1:
        output = _render_one_search(
            state,
            plan.queries[0],
            plan.options,
            output_json=output_json,
            refs_log_path=refs_log_path,
        )
    else:
        output = _render_many_searches(
            state,
            plan.queries,
            plan.options,
            output_json=output_json,
            refs_log_path=refs_log_path,
        )
    if plan.notice and not output.startswith(WEB_SEARCH_ERROR_PREFIX):
        return _with_user_approved_notice(output, output_json=output_json)
    return output


def cmd_web_search_many(
    state: ShellState,
    queries: list[str],
    fetch_size: int | None = None,
    include_content: bool = False,
    engine_config_raw: str | None = None,
    crawler_config_raw: str | None = None,
    output_json: bool = False,
    config_path: str | None = None,
    chat_id: str | None = None,
    *,
    refs_log_path: Path | None = None,
    message_id: str | None = None,
    review_id: str | None = None,
) -> str:
    """Run several web searches in one call and return one block per query.

    Requests run concurrently, at most ``SEARCH_CONCURRENCY`` at a time.
    Citation numbers are assigned afterwards, one query at a time in the
    order given, so ``[websourceN]`` is the same on every run. A URL found
    by several queries keeps one number; the manifest gets one row per search.

    A failed query shows its own error and does not drop the others. The
    output is a ``web-search:`` error only when every query failed.
    ``output_json`` returns a list with one entry per query: the usual
    ``{engine, query, results}`` object, or ``{query, error}`` on failure.
    ``refs_log_path`` is the per-turn web citation manifest; ``None``
    resolves it from the workspace root. ``message_id`` is sent as
    ``messageId`` on the review call only.

    Query review, when ``chat_id`` is set, runs once for the whole batch.
    ``review_id`` searches queries the user already approved. With no
    queries it reads ``responseContent.queries`` from that elicitation.

    Args:
        state (ShellState): Shell state carrying user/company credentials.
        queries (list[str]): Queries to search. Empty only with ``review_id``.
        review_id (str | None): Accepted review to search under.
        message_id (str | None): Assistant message the review is attached to.
        chat_id (str | None): Chat the searches are made for. Without it,
            review is skipped and the output matches a call that never
            heard of query review.

    Returns:
        str: One block per query, a pending-review instruction, or a
        ``web-search:`` error.
    """
    return _execute_web_searches(
        state,
        list(queries),
        single_format=False,
        fetch_size=fetch_size,
        include_content=include_content,
        engine_config_raw=engine_config_raw,
        crawler_config_raw=crawler_config_raw,
        output_json=output_json,
        config_path=config_path,
        chat_id=chat_id,
        refs_log_path=refs_log_path,
        message_id=message_id,
        review_id=review_id,
    )


def _format_many_search_results(
    queries: list[str],
    outcomes: list[dict[str, Any] | str],
) -> str:
    blocks: list[str] = []
    failed = 0
    for position, (query, outcome) in enumerate(
        zip(queries, outcomes, strict=True), start=1
    ):
        header = f"=== query {position}/{len(queries)} ==="
        if isinstance(outcome, str):
            failed += 1
            blocks.append(f"{header}\nquery: {query!r}\nERROR: {outcome}")
            continue
        blocks.append(f"{header}\n{_format_search_results(outcome)}")
    if failed:
        blocks.append(f"{failed} of {len(queries)} queries failed.")
    return "\n\n".join(blocks)


def _format_many_search_results_json(
    queries: list[str],
    outcomes: list[dict[str, Any] | str],
) -> str:
    entries = [
        {"query": query, "error": outcome}
        if isinstance(outcome, str)
        else _search_results_projection(outcome)
        for query, outcome in zip(queries, outcomes, strict=True)
    ]
    return json.dumps(entries, indent=2, ensure_ascii=False)


def cmd_web_crawl(
    state: ShellState,
    urls: list[str],
    parallel: int = DEFAULT_PARALLEL,
    crawler_config_raw: str | None = None,
    output_json: bool = False,
    config_path: str | None = None,
    chat_id: str | None = None,
    *,
    refs_log_path: Path | None = None,
    message_id: str | None = None,
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
        refs_log_path: The per-turn web citation manifest. When ``None``,
            it resolves from the workspace root.
        message_id: Optional assistant message this call serves; sent as
            ``messageId`` only when set.
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
    if message_id:
        params["messageId"] = message_id

    try:
        resource = unique_sdk.WebCrawl.crawl(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
    except (ValueError, unique_sdk.UniqueError) as exc:
        return f"{WEB_CRAWL_ERROR_PREFIX} {exc}"

    try:
        payload = _annotate_web_results_for_citations(
            _payload_from_resource(resource), refs_log_path=refs_log_path
        )
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
