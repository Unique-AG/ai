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
from mcp.types import CallToolResult, TextContent
from mcp_search.auth import resolve_search_settings
from mcp_search.config import SearchToolConfig
from mcp_search.references import (
    REFERENCE_FORMAT_INFORMATION,
    chunk_to_text_content,
)
from pydantic import Field

from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    get_tool_config,
    merge_tool_meta,
)
from unique_mcp.unique_injectors import get_unique_settings
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.experimental.components.internal_search import (
    InternalSearchPostProcessor,
    KnowledgeBaseInternalSearchService,
)

_LOGGER = logging.getLogger(__name__)

_META = merge_tool_meta(
    {
        "unique.app/icon": "search",
        "unique.app/system-prompt": (
            "Choose this tool if you need to search in the knowledge base"
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
    description="Search the knowledge base for the given query and return relevant chunks.",
    meta=_META,
)
async def search(
    # ── STATE: LLM fills this at call time ───────────────────────────────────
    search_string: Annotated[
        str,
        Field(description="The query to search for in the knowledge base."),
    ],
    # ── INJECTED: framework provides these, not part of the tool schema ───────
    config: SearchToolConfig = Depends(get_tool_config(SearchToolConfig)),
    settings: UniqueSettings = Depends(get_unique_settings),
) -> CallToolResult:
    """Search the knowledge base.

    All search behaviour is driven by ``SearchToolConfig`` read from the config
    meta key. Pydantic fills any missing fields with model defaults.

    Identity for the Unique API call is the logged-in user (OAuth JWT /
    userinfo) or trusted ``_meta`` from Unique AI — never a fixed
    ``UNIQUE_AUTH_*`` service user when a session is present.
    """

    try:
        settings = await resolve_search_settings(settings)
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

    return CallToolResult(
        content=[
            chunk_to_text_content(chunk, sequence_number=i)
            for i, chunk in enumerate(chunks, start=1)
        ],
    )
