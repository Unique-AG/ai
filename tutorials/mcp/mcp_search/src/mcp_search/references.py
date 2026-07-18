"""Document referencing for knowledge-base search results.

Every search result is tagged with a stable, client-agnostic reference so that
any MCP client (Unique AI, Claude Desktop, MCP Inspector, ...) can cite the
document it came from and — inside the Unique platform — open it directly in
the knowledge base.

Referencing style
-----------------
1. **URL scheme**: internally stored documents are referenced as
   ``unique://content/{contentId}``. The Unique frontend resolves this scheme
   and opens the document in the knowledge base. Chunks that originate from
   the web keep their external ``https://`` URL.
2. **Text layer** (for the LLM): each result is prefixed with a source header

       [source3] Quarterly Report 2025.pdf (pages 12-14)
       unique://content/cont_abcdefgehijklmnopqrstuvwx

   so models can cite results with ``[sourceN]`` markers or markdown links.
3. **Structured layer** (for MCP clients): each content item carries a
   ``unique.app/reference`` entry in its ``_meta``, shaped like the Unique
   ``ContentReference`` (name, url, sourceId, source, sequenceNumber), ready
   to be turned into a clickable reference chip without parsing text.
"""

from mcp.types import TextContent

from unique_toolkit.content.schemas import ContentChunk

REFERENCE_META_KEY = "unique.app/reference"

# Instruction surfaced to the orchestrating LLM via the
# "unique.app/tool-format-information" tool meta so every MCP client knows how
# to cite search results consistently.
REFERENCE_FORMAT_INFORMATION = (
    "Each search result starts with a source header of the form "
    "'[sourceN] <document name> (pages ...)' followed by the document URL. "
    "When you use information from a result, cite it inline with its "
    "[sourceN] marker. When asked for the source document, provide it as a "
    "markdown link: [<document name>](<document URL>). URLs of the form "
    "unique://content/<contentId> are resolved by the Unique platform and "
    "open the document directly in the knowledge base; never alter them."
)


def reference_url(chunk: ContentChunk) -> str:
    """Return the canonical URL for a chunk.

    External (web) chunks keep their original URL; everything stored in the
    knowledge base is addressed via the ``unique://content/{id}`` scheme that
    the Unique frontend resolves to the document view.
    """
    if chunk.url and not chunk.internally_stored_at:
        return chunk.url
    return f"unique://content/{chunk.id}"


def _pages_suffix(chunk: ContentChunk) -> str:
    if chunk.start_page is None or chunk.start_page < 0:
        return ""
    if chunk.end_page is not None and chunk.end_page != chunk.start_page:
        return f" (pages {chunk.start_page}-{chunk.end_page})"
    return f" (page {chunk.start_page})"


def chunk_to_text_content(chunk: ContentChunk, sequence_number: int) -> TextContent:
    """Render one search result as MCP ``TextContent`` with reference info.

    Args:
        chunk: The retrieved knowledge-base chunk.
        sequence_number: 1-based position of the result in the response,
            used as the ``[sourceN]`` citation marker.
    """
    name = chunk.title or chunk.key or chunk.id
    url = reference_url(chunk)
    header = f"[source{sequence_number}] {name}{_pages_suffix(chunk)}\n{url}"

    reference = chunk.to_reference(sequence_number=sequence_number)

    return TextContent(
        type="text",
        text=f"{header}\n\n{chunk.text}",
        _meta={
            **chunk.model_dump(mode="json"),
            REFERENCE_META_KEY: reference.model_dump(mode="json", by_alias=True),
        },
    )
