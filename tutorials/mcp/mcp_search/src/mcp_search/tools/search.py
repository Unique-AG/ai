"""Knowledge Base Search tool.

Separation of concerns:
- CONFIG  (admin-set, injected via the config meta key at call time)
  → service_config: KnowledgeBaseInternalSearchConfig — all retrieval params
  → post_processing: PostProcessorConfig — token budget, client-side reranking
  → no LLM involvement
- STATE   (LLM fills at call time, tool arguments)
  → search_string   required — what to search for
"""

import logging
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp_search.config import SearchToolConfig
from mcp_search.references import (
    REFERENCE_FORMAT_INFORMATION,
    chunk_to_text_content,
    citation_instruction_content,
)
from mcp_search.scope_resolver import resolve_scope_ids
from mcp_search.settings import McpSearchServerSettings
from pydantic import Field

from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    get_tool_config,
    get_unique_settings_async,
    merge_tool_meta,
)
from unique_toolkit.experimental.components.internal_search import (
    InternalSearchPostProcessor,
    KnowledgeBaseInternalSearchService,
)

_LOGGER = logging.getLogger(__name__)

_TOOL_DESCRIPTION = (
    "Search the knowledge base for the given query and return relevant chunks. "
    + REFERENCE_FORMAT_INFORMATION
)

_META = merge_tool_meta(
    {
        "unique.app/icon": "search",
        "unique.app/system-prompt": (
            "Choose this tool if you need to search in the knowledge base. "
            + REFERENCE_FORMAT_INFORMATION
        ),
        "unique.app/tool-format-information": REFERENCE_FORMAT_INFORMATION,
    },
    ContextRequirements(
        required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID],
    ),
    ConfigSchemaMeta(SearchToolConfig),
)


@tool(
    name="search",
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
async def search(
    # ── STATE: LLM fills this at call time ───────────────────────────────────
    search_string: Annotated[
        str,
        Field(description="The query to search for in the knowledge base."),
    ],
    # ── INJECTED: framework provides these, not part of the tool schema ───────
    config: SearchToolConfig = Depends(get_tool_config(SearchToolConfig)),
) -> CallToolResult:
    """Search the knowledge base.

    All search behaviour is driven by ``SearchToolConfig`` read from the config
    meta key. Pydantic fills any missing fields with model defaults.

    Identity for the Unique API call is the logged-in user (OAuth JWT /
    userinfo) or trusted ``_meta`` from Unique AI — never a fixed
    ``UNIQUE_AUTH_*`` service user when a session is present.
    """

    try:
        # In-body (not Depends) so the identity-refusal ValueError surfaces as a
        # tool error with its instructive message, not a generic dependency
        # resolution failure.
        settings = await get_unique_settings_async()
        service = KnowledgeBaseInternalSearchService.from_config(
            config.service_config
        ).bind_settings(settings)
        service.state.search_queries = [search_string]

        result = await service.run()

        post_processor = InternalSearchPostProcessor.from_settings(
            settings, config=config.post_processing
        )
        chunks = await post_processor.process(result)
    except Exception as exc:
        _LOGGER.exception("search error")
        return CallToolResult(
            isError=True, content=[TextContent(type="text", text=str(exc))]
        )

    frontend_base_url = McpSearchServerSettings().frontend_base_url_str()
    scope_by_content_id: dict[str, str] = {}
    if frontend_base_url and chunks:
        try:
            scope_by_content_id = await resolve_scope_ids(chunks, settings)
        except Exception:
            _LOGGER.exception("scope resolution failed; falling back to unique:// URLs")

    content: list[TextContent] = [
        chunk_to_text_content(
            chunk,
            sequence_number=i,
            frontend_base_url=frontend_base_url,
            scope_id=scope_by_content_id.get(chunk.id) if chunk.id else None,
        )
        for i, chunk in enumerate(chunks, start=1)
    ]
    if content:
        content.append(citation_instruction_content())

    return CallToolResult(content=content)
