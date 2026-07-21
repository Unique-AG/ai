"""Knowledge Base read-file tool — read a specific content's text, in full or by page range.

- CONFIG (admin): ReadFileToolConfig.max_tokens_per_call
- STATE (LLM): content_id required, start_page/end_page optional
"""

import logging
import math
from pathlib import Path
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp_search.references import file_reference_url, markdown_citation_link
from mcp_search.settings import McpSearchServerSettings
from pydantic import BaseModel, Field, RootModel, field_validator

from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    get_tool_config,
    get_unique_settings_async,
    merge_tool_meta,
)
from unique_toolkit._common.token.token_counting import DEFAULT_ENCODING, count_tokens
from unique_toolkit.content.functions import (
    download_content_to_bytes_async,
    search_contents_async,
)
from unique_toolkit.content.schemas import Content, ContentChunk
from unique_toolkit.content.utils import sort_content_chunks

_LOGGER = logging.getLogger(__name__)

_TEXT_EXTENSIONS = {".txt", ".md", ".html", ".json", ".csv"}
_CHUNKED_EXTENSIONS = {".pdf", ".docx"}


class ReadFileToolConfig(BaseModel):
    max_tokens_per_call: int = 8_000


class SupportedFileExtension(RootModel[str]):
    """Extension allow-list and chunked vs text dispatch."""

    @field_validator("root")
    @classmethod
    def _check_supported(cls, v: str) -> str:
        v = v.lower()
        if v not in _TEXT_EXTENSIONS | _CHUNKED_EXTENSIONS:
            raise ValueError(f"unsupported file extension: {v}")
        return v

    @property
    def is_chunked(self) -> bool:
        return self.root in _CHUNKED_EXTENSIONS


_TOOL_DESCRIPTION = (
    "Read a specific knowledge-base file's text content. Requires "
    "`content_id` (from a prior content_tree 'list'/'search' call). "
    "For large files, pass `start_page`/`end_page` to read a portion — for "
    "PDFs/DOCX these are real document pages; for plain-text formats "
    "(.txt/.md/.html/.json/.csv) they're fixed-size virtual pages, same "
    "semantics either way. If the file is too large and no range is given, "
    "the call returns an informative error (with the file's total token/page "
    "count) instead of silently truncating — use that to pick a range. Ranges "
    "are also token-capped; if a range is too large, narrow it (a single-page "
    "request always succeeds). Successful reads start with a markdown link "
    "that opens the file in the Unique knowledge base — paste it as-is when "
    "citing the file."
)

_META = merge_tool_meta(
    {
        "unique.app/icon": "file-text",
        "unique.app/system-prompt": (
            "Choose this tool to read the contents of a specific file once "
            "you have its content_id (e.g. from content_tree)."
        ),
    },
    ContextRequirements(
        required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID],
    ),
    ConfigSchemaMeta(ReadFileToolConfig),
)


def _error(text: str) -> CallToolResult:
    return CallToolResult(isError=True, content=[TextContent(type="text", text=text)])


def _with_reference_header(result: CallToolResult, content: Content) -> CallToolResult:
    """Prefix successful reads with a markdown link that opens the file."""
    if result.isError or not result.content:
        return result
    first = result.content[0]
    if not isinstance(first, TextContent):
        return result
    url = file_reference_url(
        content.id,
        metadata=content.metadata,
        frontend_base_url=McpSearchServerSettings().frontend_base_url_str(),
    )
    header = markdown_citation_link(content.title or content.key, url)
    first.text = f"{header}\n\n{first.text}"
    return result


def _ok(text: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _render_chunked(
    chunks: list[ContentChunk],
    start_page: int | None,
    end_page: int | None,
    max_tokens_per_call: int,
) -> CallToolResult:
    if not chunks:
        return _error("this file hasn't finished processing yet")

    total_pages = max((c.end_page or c.start_page or 0) for c in chunks)
    if total_pages == 0:
        # No page metadata (some DOCX pipelines) — fall back to virtual
        # paging so the file stays readable by range.
        full_text = "\n".join(c.text for c in chunks)
        return _render_text(full_text, start_page, end_page, max_tokens_per_call)

    if start_page is None and end_page is None:
        full_text = "\n".join(c.text for c in chunks)
        total_tokens = count_tokens(full_text)
        if total_tokens <= max_tokens_per_call:
            return _ok(_render_with_page_markers(chunks))
        return _error(
            f"file has ~{total_tokens} tokens across {total_pages} pages; "
            "specify start_page/end_page to read a portion."
        )

    s = start_page if start_page is not None else 1
    e = end_page if end_page is not None else total_pages
    if s < 1 or s > e or s > total_pages:
        return _error(
            f"file has {total_pages} pages; requested range {s}-{e} is out of bounds."
        )

    selected = [
        c
        for c in chunks
        if (c.start_page or 0) <= e and (c.end_page or c.start_page or 0) >= s
    ]
    if not selected:
        return _error(
            f"no content found in pages {s}-{e}; the file's page numbering "
            "may have gaps — try a wider range."
        )

    text = _render_with_page_markers(selected)
    # Single-page requests are exempt from the cap so every page stays
    # reachable even when one dense page alone exceeds it.
    if s < e:
        selected_tokens = count_tokens(text)
        if selected_tokens > max_tokens_per_call:
            return _error(
                f"pages {s}-{e} span ~{selected_tokens} tokens, over the "
                f"{max_tokens_per_call}-token per-call limit; request a "
                "narrower range (a single page is always allowed)."
            )
    return _ok(text)


def _render_with_page_markers(chunks: list[ContentChunk]) -> str:
    parts: list[str] = []
    last_page: int | None = None
    for c in chunks:
        if c.start_page is not None and c.start_page != last_page:
            parts.append(f"--- page {c.start_page} ---")
            last_page = c.start_page
        parts.append(c.text)
    return "\n".join(parts)


def _render_text(
    full_text: str,
    start_page: int | None,
    end_page: int | None,
    max_tokens_per_call: int,
) -> CallToolResult:
    total_tokens = count_tokens(full_text)
    total_pages = max(1, math.ceil(total_tokens / max_tokens_per_call))

    if start_page is None and end_page is None:
        if total_tokens <= max_tokens_per_call:
            return _ok(full_text)
        return _error(
            f"file has ~{total_tokens} tokens (~{total_pages} pages of "
            f"{max_tokens_per_call} tokens each); specify start_page/end_page "
            "to read a portion."
        )

    s = start_page if start_page is not None else 1
    e = end_page if end_page is not None else total_pages
    if s < 1 or s > e or s > total_pages:
        return _error(
            f"file has {total_pages} pages; requested range {s}-{e} is out of bounds."
        )
    # Each virtual page is exactly max_tokens_per_call tokens, so any
    # multi-page range would exceed the per-call budget by construction.
    if s < e:
        return _error(
            f"each virtual page is {max_tokens_per_call} tokens (the per-call "
            f"limit); read one page per call. File has {total_pages} pages."
        )

    token_start, token_end = _virtual_page_token_bounds(s, e, max_tokens_per_call)
    slice_text = _slice_by_token_count(full_text, token_start, token_end)
    prefix = f"showing tokens {token_start}-{token_end} of {total_tokens} total"
    return _ok(f"{prefix}\n\n{slice_text}")


def _slice_by_token_count(text: str, token_start: int, token_end: int) -> str:
    import tiktoken

    # Same encoding as count_tokens so page math and slicing stay consistent.
    encoder = tiktoken.get_encoding(DEFAULT_ENCODING)
    token_ids = encoder.encode(text)
    return encoder.decode(token_ids[token_start:token_end])


def _virtual_page_token_bounds(
    start_page: int, end_page: int, max_tokens_per_call: int
) -> tuple[int, int]:
    token_start = (start_page - 1) * max_tokens_per_call
    token_end = end_page * max_tokens_per_call
    return token_start, token_end


@tool(
    name="read_file",
    description=_TOOL_DESCRIPTION,
    meta=_META,
    # openWorldHint=False: bounded to one company's own KB, not an open/unbounded domain like web search.
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def read_file(
    content_id: Annotated[
        str,
        Field(description="The content_id of the file to read, from content_tree."),
    ],
    start_page: Annotated[
        int | None,
        Field(
            description=(
                "First page to return (1-indexed). Real document page for "
                "PDF/DOCX, virtual token-based page for plain-text formats."
            )
        ),
    ] = None,
    end_page: Annotated[
        int | None,
        Field(description="Last page to return (1-indexed), inclusive."),
    ] = None,
    config: ReadFileToolConfig = Depends(get_tool_config(ReadFileToolConfig)),
) -> CallToolResult:
    """Read one KB file by content_id; dispatch by extension."""
    try:
        # In-body (not Depends) so the identity-refusal ValueError surfaces as a
        # tool error with its instructive message.
        settings = await get_unique_settings_async()
        company_id = settings.authcontext.get_confidential_company_id()
        user_id = settings.authcontext.get_confidential_user_id()

        contents = await search_contents_async(
            user_id=user_id,
            company_id=company_id,
            chat_id=None,
            where={"id": {"equals": content_id}},
        )
        if not contents:
            return _error(f"no content found for content_id={content_id}")
        content = contents[0]

        try:
            ext = SupportedFileExtension(Path(content.key).suffix)
        except ValueError:
            suffix = Path(content.key).suffix
            return _error(f"unsupported file type for read_file: {suffix}")

        if ext.is_chunked:
            chunks = sort_content_chunks(list(content.chunks))
            result = _render_chunked(
                chunks, start_page, end_page, config.max_tokens_per_call
            )
        else:
            raw_bytes = await download_content_to_bytes_async(
                user_id=user_id,
                company_id=company_id,
                content_id=content_id,
                chat_id=None,
            )
            # Non-UTF-8 bytes degrade to replacement chars instead of failing
            # the read.
            full_text = raw_bytes.decode("utf-8", errors="replace")
            result = _render_text(
                full_text, start_page, end_page, config.max_tokens_per_call
            )
        return _with_reference_header(result, content)
    except Exception as exc:
        _LOGGER.exception("read_file error")
        return CallToolResult(
            isError=True, content=[TextContent(type="text", text=str(exc))]
        )
