"""Document referencing for knowledge-base search results.

Every search result is tagged with a stable, client-agnostic reference so that
any MCP client (Unique AI, Claude Desktop, MCP Inspector, ...) can cite the
document it came from and — when a frontend base URL is configured — open it
in the Unique knowledge base UI.

Referencing style
-----------------
1. **URL scheme**:
   - External (web) chunks keep their ``https://`` URL.
   - Internal docs use
     ``{UNIQUE_FRONTEND_BASE_URL}/knowledge-upload/{scopeId}?file={contentId}``
     when the frontend base URL and scope id are known.
   - Otherwise fall back to ``unique://content/{contentId}`` (resolved by the
     Unique platform frontend).
2. **Text layer** (for the LLM): each result is prefixed with a ready-to-use
   markdown citation link

       [Quarterly Report 2025.pdf](https://next.qa.unique.app/knowledge-upload/…?file=…)
       (pages 12-14)

   so models can paste the link inline instead of inventing ``[sourceN]`` tags.
3. **Structured layer** (for Unique MCP clients): each content item carries a
   ``unique.app/reference`` entry in its ``_meta``, always using the
   ``unique://content/{id}`` scheme so Unique AI chips keep working.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from mcp.types import TextContent

from unique_toolkit.content.schemas import ContentChunk

_LOGGER = logging.getLogger(__name__)

REFERENCE_META_KEY = "unique.app/reference"

# Instruction surfaced to the orchestrating LLM via the
# "unique.app/tool-format-information" tool meta, the tool description, and a
# trailing result block so every MCP client knows how to cite search results.
REFERENCE_FORMAT_INFORMATION = (
    "Each search result starts with a markdown citation link of the form "
    "'[<document name>](<document URL>)' (optional page range on the next line). "
    "When you use information from a result, cite it inline by pasting that "
    "exact markdown link immediately after the claim — for example "
    "'raised a $30M Series A ([andreas-hauri.md](https://…)).' "
    "Do NOT invent placeholders like [source1], [sourceN], or [1]. "
    "Always end your answer with a Sources section listing each cited document "
    "once as the same markdown link. Prefer https://…/knowledge-upload/…?file=… "
    "links when present — they open the document in the Unique knowledge base. "
    "Never alter unique:// or https:// URLs from the result headers."
)

CITATION_RESULT_INSTRUCTION = (
    "How to cite: paste the exact [<document name>](<url>) markdown links from "
    "the result headers inline after each claim. Do not write [sourceN] or other "
    "bracket placeholders. End with a Sources list using those same markdown links."
)

SERVER_CITATION_INSTRUCTIONS = (
    "This server searches the Unique knowledge base. When answering from search "
    "results, cite sources inline by pasting the exact markdown links "
    "[document name](url) provided in each result header. Never use [sourceN] "
    "placeholders. End with a Sources section listing the cited documents as "
    "those same markdown links."
)


def scope_id_from_folder_id_path(folder_id_path: str) -> str | None:
    """Return the leaf scope id from a ``uniquepathid://…`` path."""
    if not folder_id_path or not isinstance(folder_id_path, str):
        return None
    segments = [
        sid
        for sid in folder_id_path.replace("uniquepathid://", "").split("/")
        if sid
    ]
    return segments[-1] if segments else None


def _metadata_as_dict(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    model_dump = getattr(metadata, "model_dump", None)
    if callable(model_dump):
        # include extras (folderIdPath) that ContentMetadata allows
        return model_dump(mode="python", by_alias=True)
    return {}


def scope_id_from_metadata(metadata: Any) -> str | None:
    """Extract the leaf folder/scope id from content or chunk metadata."""
    data = _metadata_as_dict(metadata)
    path = data.get("folderIdPath") or data.get("folder_id_path")
    if isinstance(path, str):
        return scope_id_from_folder_id_path(path)
    owner = data.get("ownerId") or data.get("owner_id")
    if isinstance(owner, str) and owner.startswith("scope_"):
        return owner
    return None


def scope_id_from_chunk(chunk: ContentChunk) -> str | None:
    """Best-effort scope id from fields already present on a search chunk."""
    return scope_id_from_metadata(chunk.metadata)


def frontend_document_url(
    frontend_base_url: str, scope_id: str, content_id: str
) -> str:
    """Build a Unique knowledge-upload deep link for a document."""
    base = frontend_base_url.rstrip("/")
    return f"{base}/knowledge-upload/{quote(scope_id, safe='')}?file={quote(content_id, safe='')}"


def platform_reference_url(chunk: ContentChunk) -> str:
    """URL used in Unique-platform ``_meta`` (always ``unique://`` for KB docs)."""
    if chunk.url and not chunk.internally_stored_at:
        return chunk.url
    return f"unique://content/{chunk.id}"


def reference_url(
    chunk: ContentChunk,
    *,
    frontend_base_url: str | None = None,
    scope_id: str | None = None,
) -> str:
    """Return the canonical URL for a chunk (for the LLM-facing text layer).

    Priority:
    1. External web chunk → original https URL
    2. Frontend base + scope → knowledge-upload deep link
    3. Fallback → ``unique://content/{id}``
    """
    if chunk.url and not chunk.internally_stored_at:
        return chunk.url

    resolved_scope = scope_id or scope_id_from_chunk(chunk)
    if frontend_base_url and resolved_scope and chunk.id:
        return frontend_document_url(frontend_base_url, resolved_scope, chunk.id)

    return f"unique://content/{chunk.id}"


def _pages_suffix(chunk: ContentChunk) -> str:
    if chunk.start_page is None or chunk.start_page < 0:
        return ""
    if chunk.end_page is not None and chunk.end_page != chunk.start_page:
        return f" (pages {chunk.start_page}-{chunk.end_page})"
    return f" (page {chunk.start_page})"


def _escape_markdown_link_label(name: str) -> str:
    """Escape brackets in document names so markdown links stay valid."""
    return name.replace("[", "\\[").replace("]", "\\]")


def markdown_citation_link(name: str, url: str) -> str:
    """Return a ready-to-paste ``[name](url)`` citation."""
    return f"[{_escape_markdown_link_label(name)}]({url})"


def chunk_to_text_content(
    chunk: ContentChunk,
    sequence_number: int,
    *,
    frontend_base_url: str | None = None,
    scope_id: str | None = None,
) -> TextContent:
    """Render one search result as MCP ``TextContent`` with reference info.

    Args:
        chunk: The retrieved knowledge-base chunk.
        sequence_number: 1-based position of the result in the response
            (stored in Unique ``_meta`` reference chips).
        frontend_base_url: Optional Unique frontend origin for deep links.
        scope_id: Optional folder/scope id (overrides metadata on the chunk).
    """
    name = chunk.title or chunk.key or chunk.id
    text_url = reference_url(
        chunk, frontend_base_url=frontend_base_url, scope_id=scope_id
    )
    cite = markdown_citation_link(name, text_url)
    pages = _pages_suffix(chunk)
    header = f"{cite}{pages}" if pages else cite

    # Unique AI chips keep the platform scheme so existing clients stay stable.
    reference = chunk.to_reference(sequence_number=sequence_number)
    reference_payload = reference.model_dump(mode="json", by_alias=True)
    reference_payload["url"] = platform_reference_url(chunk)

    return TextContent(
        type="text",
        text=f"{header}\n\n{chunk.text}",
        _meta={
            **chunk.model_dump(mode="json"),
            REFERENCE_META_KEY: reference_payload,
        },
    )


def citation_instruction_content() -> TextContent:
    """Trailing block that steers the LLM to cite the results above."""
    return TextContent(type="text", text=CITATION_RESULT_INSTRUCTION)
