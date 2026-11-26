"""Citable records in an MCP tool result.

Shared by ``unique-cli mcp`` (Conduct) and the Unique AI MCP tool wrapper, so a
tool result is split into the same records, titles and links on both paths.
"""

from __future__ import annotations

import json
import re
from typing import Any

_MCP_SNIPPET_CHAR_LIMIT = 300

# Keys an MCP tool's JSON result commonly uses for a record's human title.
_TITLE_KEYS = (
    "title",
    "name",
    "displayName",
    "display_name",
    "subject",
    "summary",
    "key",
)

# Preferred keys for a record's own http(s) link, tried before other fields.
# One present but empty means the record has no link.
_URL_KEYS = (
    "url",
    "uri",
    "href",
    "webUrl",
    "web_url",
    "webLink",
    "web_link",
    "outlookWebLink",
    "link",
)

# Internal reference: a Unique knowledge-base document, opened in the preview.
_INTERNAL_URL = re.compile(r"unique://content/\S+")

# How deep untitled wrapper objects are searched for lists of titled records.
_MAX_WRAPPER_DEPTH = 4

# Markdown list item: a bullet or numbered title, then an indented http(s) URL.
# A list marker is required so a prose line above an indented link is not a hit.
_MARKDOWN_TITLE_URL = re.compile(
    r"(?m)^(?:[-*]\s+|\d+\.\s+)(.+?)\n[ \t]+(https?://\S+)\s*$"
)

# Keys an MCP tool's JSON result commonly uses for the optional "details" line
# (UN-22310) — e.g. a date and an author such as "10/10/2026 - Jamie Dimon".
# Best-effort: only top-level record keys are inspected for these (nested
# provenance is too tool-specific to generalize). The values themselves may be
# nested one level — a date is read as a top-level string, while an author may
# be a plain string or an object whose name is pulled via `_AUTHOR_NAME_KEYS`
# (e.g. Atlassian's `{"displayName": "..."}`). The line is omitted when neither
# a date nor an author is found.
_DETAILS_DATE_KEYS = (
    "date",
    "updated",
    "updatedAt",
    "updatedDate",
    "lastModified",
    "modified",
    "created",
    "createdAt",
    "createdDate",
    "timestamp",
)
_DETAILS_AUTHOR_KEYS = (
    "author",
    "creator",
    "owner",
    "createdBy",
    "updatedBy",
    "by",
    "sender",
    "from",
)
# Keys to read a human name out of an author value that is itself an object
# (e.g. Atlassian's ``{"displayName": "Jamie Dimon"}``).
_AUTHOR_NAME_KEYS = ("displayName", "name", "fullName", "emailAddress", "email")
_MCP_DETAILS_CHAR_LIMIT = 200


def _snippet(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None
    collapsed = " ".join(text.split())
    return collapsed[:_MCP_SNIPPET_CHAR_LIMIT] or None


def _title_from_json(obj: dict[str, Any]) -> str | None:
    for key in _TITLE_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_str_by_keys(obj: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _author_display(obj: dict[str, Any]) -> str | None:
    """Read an author name from a record, whether the author value is a plain
    string or a nested object (e.g. ``{"displayName": "..."}``)."""
    for key in _DETAILS_AUTHOR_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            name = _first_str_by_keys(value, _AUTHOR_NAME_KEYS)
            if name:
                return name
    return None


def _details_from_json(obj: dict[str, Any]) -> str | None:
    """Best-effort optional "details" line (UN-22310): a date and/or author
    composed as "<date> - <author>". Returns ``None`` when neither is found."""
    date = _first_str_by_keys(obj, _DETAILS_DATE_KEYS)
    author = _author_display(obj)
    parts = [part for part in (date, author) if part]
    if not parts:
        return None
    return " - ".join(parts)[:_MCP_DETAILS_CHAR_LIMIT]


# Keys under which a JSON object commonly wraps the actual list of retrieved
# records, e.g. Jira's ``{"issues": [...]}`` or a generic ``{"results": [...]}``.
# When a result wraps its records this way, we iterate the list so each record
# becomes its own reference instead of collapsing to one title-less chip.
_CONTAINER_KEYS = (
    "issues",
    "results",
    "items",
    "values",
    "data",
    "hits",
    "records",
    "entries",
    "elements",
    "content",
)

# Subset of ``_CONTAINER_KEYS`` that are also plausible fields of a *single*
# titled record — e.g. a page/document payload ``{"title": ..., "content": [...]}``
# whose ``content`` is the body, not a list of separate results. When one of
# these matches on an object that carries its own top-level title, we keep the
# object as one record rather than splitting it into title-less inner rows.
_AMBIGUOUS_CONTAINER_KEYS = ("data", "content")


def loads_embedded_json(text: str) -> Any:
    """Parse a JSON value from a tool-result string, tolerating a non-JSON
    preamble.

    Some MCP servers (e.g. Atlassian) prefix the JSON body with a human-readable
    notice like ``[IMPORTANT: ...]\\n{...}``, so a direct ``json.loads`` of the
    whole string fails. Try a direct parse first, then fall back to decoding the
    first JSON object/array that appears. Returns ``None`` when no JSON is found.
    """
    found = find_embedded_json(text)
    return found[0] if found else None


def find_embedded_json(text: str) -> tuple[Any, int, int] | None:
    """Like :func:`loads_embedded_json`, but also returns the ``start`` and
    ``end`` offsets of the decoded JSON so text around it can be kept."""
    try:
        return json.loads(text), 0, len(text)
    except (ValueError, TypeError):
        pass
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char in "{[":
            try:
                value, end = decoder.raw_decode(text, index)
            except ValueError:
                continue
            return value, index, end
    return None


def _records_from_parsed(parsed: Any) -> tuple[list[dict[str, Any]], bool]:
    """Records of a known container key's list, else of every titled list in a wrapper.
    The flag marks wrapper records, which are cited only with a link."""
    if isinstance(parsed, list):
        return [entry for entry in parsed if isinstance(entry, dict)], False
    if isinstance(parsed, dict):
        for key in _CONTAINER_KEYS:
            value = parsed.get(key)
            if isinstance(value, list):
                records = [entry for entry in value if isinstance(entry, dict)]
                if records:
                    # A single titled record must not be split apart by an
                    # incidental ambiguous key (a page body under ``content`` /
                    # ``data``) — keep the object as one record so its title
                    # survives instead of collapsing to a title-less chip.
                    if key in _AMBIGUOUS_CONTAINER_KEYS and _title_from_json(parsed):
                        return [parsed], False
                    return records, False
        if not _is_record(parsed):
            titled = _titled_lists(parsed, depth=0)
            if titled:
                return titled, True
        return [parsed], False
    return [], False


def _is_record(obj: dict[str, Any]) -> bool:
    """A titled object, or one with its own link key, is one record rather than
    a wrapper: a chat message with no subject is not split into its attachments."""
    return bool(_title_from_json(obj)) or any(key in obj for key in _URL_KEYS)


def _titled_lists(wrapper: dict[str, Any], *, depth: int) -> list[dict[str, Any]]:
    """Records of every list holding a titled record, searching wrapper objects
    but not inside a record."""
    records: list[dict[str, Any]] = []
    for value in wrapper.values():
        value = _connection_nodes(value) or value
        if isinstance(value, list):
            entries = [entry for entry in value if isinstance(entry, dict)]
            if any(_title_from_json(entry) for entry in entries):
                records.extend(entries)
        elif (
            isinstance(value, dict)
            and depth < _MAX_WRAPPER_DEPTH
            and not _is_record(value)
        ):
            records.extend(_titled_lists(value, depth=depth + 1))
    return records


def _connection_nodes(value: object) -> list[Any] | None:
    """The ``nodes`` list of a GraphQL-style connection, such as Atlassian's
    ``{"issues": {"nodes": [...], "webUrl": ...}}``, whose own link is the search page."""
    if isinstance(value, dict):
        nodes = value.get("nodes")
        if isinstance(nodes, list):
            return nodes
    return None


def _is_http_url(value: object) -> str | None:
    """Return ``value`` when it is an http(s) URL, else None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if stripped.startswith("https://") or stripped.startswith("http://"):
        return stripped
    return None


def _is_citable_url(value: object) -> str | None:
    """Return ``value`` when it is an http(s) or ``unique://content/<id>`` URL."""
    if isinstance(value, str) and _INTERNAL_URL.fullmatch(value.strip()):
        return value.strip()
    return _is_http_url(value)


def _url_from_item(obj: dict[str, Any]) -> str | None:
    """First citable URL on a record. Preferred keys, then any string field,
    unless a preferred key is present but empty: the record then has no link."""
    for key in _URL_KEYS:
        url = _is_citable_url(obj.get(key))
        if url:
            return url
    if any(key in obj and obj[key] in ("", None) for key in _URL_KEYS):
        return None
    for value in obj.values():
        url = _is_citable_url(value)
        if url:
            return url
    return None


def _with_url(item: dict[str, Any], url: str | None) -> dict[str, Any]:
    if url:
        item["url"] = url
    return item


def _titles_from_json(text: str) -> list[dict[str, Any]]:
    """Best-effort: pull a human title out of a JSON result, e.g. an Atlassian
    page/issue returned as JSON-in-text. Tolerates a non-JSON preamble before
    the JSON body and unwraps a container key (``{"issues": [...]}``) so each
    retrieved record yields its own item. A record from a wrapper's list, or
    titled only by ``display_name``, needs a link. Returns [] when the text
    carries no JSON or no record qualifies.
    """
    parsed = loads_embedded_json(text)
    if parsed is None:
        return []
    records, needs_link = _records_from_parsed(parsed)
    items: list[dict[str, Any]] = []
    for entry in records:
        title = _title_from_json(entry)
        if not title:
            continue
        url = _url_from_item(entry)
        if not url and (needs_link or _titled_by_display_name_only(entry)):
            continue
        items.append(
            _with_url(
                {
                    "title": title,
                    "snippet": None,
                    "details": _details_from_json(entry),
                    "text": _record_text(entry),
                },
                url,
            )
        )
    return items


def _titled_by_display_name_only(entry: dict[str, Any]) -> bool:
    return _title_from_json({**entry, "display_name": None}) is None


def _titles_from_markdown_list(text: str) -> list[dict[str, Any]]:
    """One item per markdown list entry that pairs a title with an http(s) URL.

    Returns [] when no pair is found.
    """
    if not text.strip():
        return []
    items: list[dict[str, Any]] = []
    for match in _MARKDOWN_TITLE_URL.finditer(text):
        title = match.group(1).strip().lstrip("-* ").strip()
        url = _is_http_url(match.group(2))
        if not title or not url:
            continue
        items.append(
            {
                "title": title,
                "snippet": None,
                "details": None,
                "text": match.group(0).strip(),
                "url": url,
            }
        )
    return items


def _get_by_dotted_path(obj: Any, path: str) -> Any:
    """Walk a dotted path over dicts and lists (numeric segments index lists),
    e.g. ``"issues"``, ``"fields.summary"``, ``"result.items.0.key"``. Returns
    ``None`` when any segment is missing."""
    current = obj
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list) and segment.lstrip("-").isdigit():
            index = int(segment)
            try:
                current = current[index]
            except IndexError:
                return None
        else:
            return None
        if current is None:
            return None
    return current


_TEMPLATE_TOKEN = re.compile(r"\{([^{}]+)\}")


def _render_title_template(template: str, record: dict[str, Any]) -> str | None:
    """Substitute ``{dotted.path}`` tokens from ``record`` into ``template``.
    Missing tokens render empty; returns ``None`` if the result is blank."""

    def _sub(match: re.Match[str]) -> str:
        value = _get_by_dotted_path(record, match.group(1).strip())
        return str(value).strip() if value is not None else ""

    rendered = _TEMPLATE_TOKEN.sub(_sub, template).strip()
    # Collapse artifacts left by empty tokens (e.g. a dangling " — ").
    rendered = rendered.strip(" -—–|:").strip()
    return rendered or None


def _response_field(response: Any, name: str) -> Any:
    if isinstance(response, dict):
        return response.get(name)
    return getattr(response, name, None)


def _as_content_dict(block: Any) -> dict[str, Any] | None:
    """Normalize an MCP content block to a dict.

    Client libraries often hand back typed objects (``mcp.types.TextContent``)
    with the same fields as the wire dict. Only known attribute names are
    copied so a hostile object cannot inject unexpected keys. A typed ``uri``
    (``AnyUrl`` in ``mcp.types.ResourceLink``) becomes its wire string.
    """
    if isinstance(block, dict):
        return block
    block_type = getattr(block, "type", None)
    if not isinstance(block_type, str) or not block_type.strip():
        return None
    out: dict[str, Any] = {"type": block_type}
    for key in ("text", "name", "description"):
        value = getattr(block, key, None)
        if value is not None:
            out[key] = value
    uri = getattr(block, "uri", None)
    if uri is not None:
        out["uri"] = uri if isinstance(uri, str) else str(uri)
    return out


def _mapped_records(response: Any, list_path: str | None) -> list[Any]:
    """Locate the records a reference mapping applies to, preferring the
    MCP-native ``structuredContent`` then any JSON-in-text block (preamble
    tolerant). ``list_path`` (dotted) points at the array; when unset the parsed
    value itself is used. List entries may be objects (field/template titles) or
    plain strings (text titles), so both are kept; a single object is wrapped.
    An empty object/list is ignored (not treated as a record) so the caller can
    still fall back to ``titleFromText`` / the generic heuristic — e.g. an empty
    ``structuredContent`` alongside a Markdown doc."""
    sources: list[Any] = []
    structured = _response_field(response, "structuredContent") or _response_field(
        response, "structured_content"
    )
    if structured is not None:
        sources.append(structured)
    for block in _response_field(response, "content") or []:
        normalized = _as_content_dict(block)
        if normalized is not None and normalized.get("type") == "text":
            parsed = loads_embedded_json(normalized.get("text") or "")
            if parsed is not None:
                sources.append(parsed)

    for parsed in sources:
        target = _get_by_dotted_path(parsed, list_path) if list_path else parsed
        target = _connection_nodes(target) or target
        if isinstance(target, list):
            records = [entry for entry in target if isinstance(entry, (dict, str))]
            if records:
                return records
        elif isinstance(target, dict) and target:
            return [target]
    return []


_MCP_TEXT_TITLE_DEFAULT_CHARS = 120


def _leading_title_line(text: str | None, max_chars: int) -> str | None:
    """First non-empty line of ``text`` with leading Markdown heading/list
    markers (``# * - >``) stripped, capped at ``max_chars``. Used to title a
    plain-text document (or a plain-text list item) by its heading. ``None``
    when ``text`` is not a non-empty string."""
    if not isinstance(text, str):
        return None
    for line in text.splitlines():
        stripped = line.strip().lstrip("#*->").strip()
        if stripped:
            return stripped[:max_chars]
    return None


def _first_text_title(response: Any, max_chars: int) -> str | None:
    """Title from the first non-empty line of the first text block — for a
    non-JSON result such as a fetched Markdown document (e.g. ``read_doc``)."""
    for block in _response_field(response, "content") or []:
        normalized = _as_content_dict(block)
        if normalized is not None and normalized.get("type") == "text":
            title = _leading_title_line(normalized.get("text"), max_chars)
            if title:
                return title
    return None


def _all_text_blocks(response: Any) -> str | None:
    """Concatenation of every text block — the underlying text of a single-item
    result (e.g. a fetched document) recorded as that item's ground truth."""
    texts: list[str] = []
    for block in _response_field(response, "content") or []:
        normalized = _as_content_dict(block)
        if normalized is None or normalized.get("type") != "text":
            continue
        text = normalized.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return "\n\n".join(texts) or None


def _record_text(record: Any) -> str | None:
    """A record's underlying text for citation grounding: the record itself
    when it is a plain string, else the serialized record — which carries the
    titled field plus all metadata the agent may cite."""
    if isinstance(record, str):
        return record or None
    try:
        return json.dumps(record, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return None


def _extract_with_reference_mapping(
    response: Any, mapping: dict[str, Any]
) -> list[dict[str, Any]]:
    """Destructure a result into ``{title, snippet, details}`` items using an
    admin-configured reference mapping. For a list result, one item per record;
    for a non-JSON text result with ``titleFromText`` set, a single item titled
    from the leading text. Returns [] when the mapping locates nothing, so the
    caller can fall back to the generic heuristic."""
    list_path = mapping.get("listPath") or mapping.get("list_path")
    title_path = mapping.get("titlePath") or mapping.get("title_path")
    title_template = mapping.get("titleTemplate") or mapping.get("title_template")
    details_path = mapping.get("detailsPath") or mapping.get("details_path")
    title_from_text = mapping.get("titleFromText") or mapping.get("title_from_text")
    # When titling from text and the list items are objects, this dotted path
    # points at the text field within each item (e.g. ``content``); leave unset
    # when each item is itself a plain string.
    title_text_path = mapping.get("titleTextPath") or mapping.get("title_text_path")
    url_path = mapping.get("urlPath") or mapping.get("url_path")
    try:
        title_max_chars = int(
            mapping.get("titleMaxChars")
            or mapping.get("title_max_chars")
            or _MCP_TEXT_TITLE_DEFAULT_CHARS
        )
    except (TypeError, ValueError):
        title_max_chars = _MCP_TEXT_TITLE_DEFAULT_CHARS

    records = _mapped_records(response, list_path)
    items: list[dict[str, Any]] = []
    for record in records:
        is_dict = isinstance(record, dict)
        if title_from_text:
            # Title from the item's text: the item itself when it's a plain
            # string, else its ``title_text_path`` field.
            if isinstance(record, str):
                text = record
            elif is_dict and title_text_path:
                text = _get_by_dotted_path(record, title_text_path)
            else:
                text = None
            title = _leading_title_line(text, title_max_chars)
        elif title_template and is_dict:
            title = _render_title_template(title_template, record)
        elif title_path and is_dict:
            value = _get_by_dotted_path(record, title_path)
            title = str(value).strip() if isinstance(value, (str, int, float)) else None
        else:
            title = None
        if not title:
            continue
        details = (
            _get_by_dotted_path(record, details_path)
            if details_path and is_dict
            else None
        )
        url = None
        if is_dict:
            if url_path:
                url = _is_citable_url(_get_by_dotted_path(record, url_path))
            if not url:
                url = _url_from_item(record)
        items.append(
            _with_url(
                {
                    "title": title,
                    "snippet": None,
                    "details": str(details).strip() if details else None,
                    "text": _record_text(record),
                },
                url,
            )
        )
    if items:
        return items
    # Non-list / non-JSON result (e.g. a fetched Markdown doc): title the single
    # chip from the leading text when the tool opts in via ``titleFromText``.
    # Only when *no* records were located — if list records were found but
    # yielded no usable title, defer to the generic heuristic (e.g. per-issue
    # references) instead of a bogus text-derived chip.
    if not records and title_from_text:
        title = _first_text_title(response, title_max_chars)
        if title:
            return [
                {
                    "title": title,
                    "snippet": None,
                    "details": None,
                    "text": _all_text_blocks(response),
                }
            ]
    return items


def extract_mcp_citation_items(
    response: Any,
    *,
    reference_mapping: dict[str, Any] | None = None,
    fallback_text: str | None = None,
) -> list[dict[str, Any]]:
    """Context for what the tool retrieved: ``{title, snippet, text}`` per item,
    plus ``url`` and ``details`` when the record has them.

    ``response`` is an MCP ``CallToolResult``, as a wire dict or an object.

    An optional admin ``reference_mapping`` is applied first (deterministic
    destructuring of a list result); when it yields nothing we fall back to the
    generic heuristic: MCP ``resource_link`` names (spec-native) or a best-effort
    JSON-title heuristic over text blocks (for tools like Atlassian that return
    JSON-in-text), or a markdown list that pairs a title with an indented
    http(s) URL. Typed content blocks from an MCP client library are
    normalized to dicts first so a list result is not collapsed to one
    title-less chip. An http(s) or ``unique://content/<id>`` link on a record is
    stored on the row and is not copied into the Sources block. Falls back to a
    single title-less item (the runner names it after the tool) when the result
    carries no recognizable title.

    ``text`` is the item's underlying retrieved text (the serialized record, a
    fetched document body, or — for the title-less fallback — ``fallback_text``,
    the whole formatted output). The runner grounds the hallucination check for
    each cited ``[mcpsourceN]`` on it. A ``resource_link`` carries no body, so
    its ``text`` is the link description only.
    """
    if reference_mapping:
        mapped = _extract_with_reference_mapping(response, reference_mapping)
        if mapped:
            return mapped

    content = _response_field(response, "content") or []
    items: list[dict[str, Any]] = []

    for block in content:
        normalized = _as_content_dict(block)
        if normalized is None:
            continue
        if normalized.get("type") == "resource_link":
            name = (normalized.get("name") or "").strip()
            if name:
                items.append(
                    _with_url(
                        {
                            "title": name,
                            "snippet": _snippet(normalized.get("description")),
                            "text": normalized.get("description") or None,
                        },
                        _is_citable_url(normalized.get("uri")),
                    )
                )

    if not items:
        for block in content:
            normalized = _as_content_dict(block)
            if normalized is not None and normalized.get("type") == "text":
                items.extend(_titles_from_json(normalized.get("text") or ""))

    if not items:
        for block in content:
            normalized = _as_content_dict(block)
            if normalized is not None and normalized.get("type") == "text":
                items.extend(_titles_from_markdown_list(normalized.get("text") or ""))

    if not items and fallback_text:
        items.extend(_titles_from_json(fallback_text))
        if not items:
            items.extend(_titles_from_markdown_list(fallback_text))

    if not items:
        # No recognizable title — one chip named after the tool itself.
        items.append({"title": None, "snippet": None, "text": fallback_text})

    return items
