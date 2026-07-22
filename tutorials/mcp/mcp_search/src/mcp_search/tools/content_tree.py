"""Knowledge Base content-tree tool — browse, list, and fuzzy-search visible files.

- CONFIG (admin, per company): ContentTreeToolConfig
- ENV (process-wide): MCP_SEARCH_CONTENT_TREE_CACHE_TTL_SECONDS / _MAX_ENTRIES
- STATE (LLM, per call): mode required, rest optional per mode
"""

import logging
from collections.abc import Sequence
from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from mcp_search.references import file_reference_url, markdown_citation_link
from mcp_search.settings import McpSearchServerSettings
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp import (
    ConfigSchemaMeta,
    ContextRequirements,
    MetaKeys,
    get_tool_config,
    get_unique_settings_async,
    merge_tool_meta,
)
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.content.schemas import ContentInfo
from unique_toolkit.content.smart_rules import Operator, Statement, UniqueQLField
from unique_toolkit.experimental.components.content_tree import ContentTree
from unique_toolkit.experimental.resources.feature_flags._ttl_cache import (
    AsyncTTLCache,
)

_LOGGER = logging.getLogger(__name__)

MatchTarget = Literal["key", "path", "both"]

# Applied when metadata_filter is unset. Not the field's own default:
# UniqueQLField's schema declares string|null but its serializer returns
# dict|None, so any non-None default breaks admin-UI rendering. Kept as a
# Statement (`.to_dict()` per call) so no shared mutable dict is handed to
# downstream service calls.
_DEFAULT_METADATA_FILTER_STATEMENT = Statement(
    operator=Operator.NOT_CONTAINS,
    path=["folderIdPath"],
    value="user-memory",
)


class ContentTreeToolConfig(BaseModel):
    # dict[str, Any] breaks the admin schema generator (RJSF can't infer
    # `items` for a nested array under Any); UniqueQLField avoids this.
    metadata_filter: Annotated[
        UniqueQLField,
        RJSFMetaTag(
            {
                "ui:options": {"customValidation": "uniqueql"},
                "anyOf": [
                    {
                        "ui:widget": "textarea",
                        "ui:placeholder": (
                            '{"operator": "equals", "value": "...", "path": ["fieldName"]}'
                        ),
                        "ui:emptyValue": "",
                    },
                    {},
                ],
            }
        ),
    ] = Field(default=None)
    default_limit: int = 50
    default_min_score: float = 0.6
    default_match_on: MatchTarget = "both"
    default_case_sensitive: bool = False
    max_concurrent_scope_lookups: int = 25


class _ContentTreeCacheSettings(BaseSettings):
    """Process-wide, not per-company: an operational concern, not a business one."""

    model_config = SettingsConfigDict(env_prefix="MCP_SEARCH_CONTENT_TREE_CACHE_")

    ttl_seconds: int = 1800
    max_entries: int = 128


# Keeps ContentTree instances alive across calls, keyed by (company_id,
# user_id). Single-process only.
_cache_settings = _ContentTreeCacheSettings()
_tree_cache: AsyncTTLCache | None = None

# Toolkit path helpers emit this sentinel when content has no folderIdPath
# (chat uploads, loose files). Strip it from display labels only — do not
# change toolkit emission; other callers may rely on the literal value.
_NO_FOLDER_PATH_SENTINEL = "_no_folder_path"


def _normalize_path_segment(segment: str) -> str:
    """Strip ``[`` / ``]`` so display labels and folder_path filters stay aligned."""
    return segment.replace("[", "").replace("]", "")


def _display_path_segments(segments: Sequence[str]) -> list[str]:
    """Path segments for display and filtering (sentinel dropped, brackets stripped)."""
    return [
        _normalize_path_segment(s) for s in segments if s != _NO_FOLDER_PATH_SENTINEL
    ]


def _display_path(segments: Sequence[str]) -> str:
    """Join path segments for display labels.

    Drops the orphan-folder sentinel and strips ``[`` / ``]`` so folder names
    like ``[SM]`` cannot break the outer ``[label](url)`` markdown wrapper.
    """
    return "/".join(_display_path_segments(segments))


def _file_link(
    content_info: ContentInfo,
    segments: Sequence[str],
    frontend_base_url: str | None,
) -> str:
    """Render a file row as a markdown citation (sentinel/brackets stripped)."""
    display = _display_path(segments)
    url = file_reference_url(
        content_info.id,
        metadata=content_info.metadata,
        owner_id=content_info.owner_id,
        frontend_base_url=frontend_base_url,
    )
    return markdown_citation_link(display, url)


def _get_tree_cache() -> AsyncTTLCache:
    global _tree_cache
    if _tree_cache is None:
        _tree_cache = AsyncTTLCache(
            maxsize=_cache_settings.max_entries,
            ttl_ms=_cache_settings.ttl_seconds * 1000,
        )
    return _tree_cache


_TOOL_DESCRIPTION = (
    "Browse the knowledge base's visible file/folder structure. Pick a "
    "`mode`; only that mode's args below apply, rest ignored. '*' = required.\n"
    "- mode='tree': max_depth — first orientation view of folders/files.\n"
    "- mode='list': folder_path, limit — flat listing; each result's "
    "content_id is needed for a later read_file call.\n"
    "- mode='search': query*, limit, min_score, match_on, case_sensitive — "
    "fuzzy filename/path lookup when you know roughly what it's called but "
    "not where.\n"
    "'list' and 'search' rows start with a markdown link that opens the file "
    "in the Unique knowledge base — paste it as-is when referring the user to "
    "a file; use the content_id for read_file calls.\n"
    "Listings are cached per user (~30 min); repeat calls are fast. When the "
    "user says they added, deleted, or changed files and needs a fresh tree, "
    "call with refresh=true (expect a slower ~20s refetch)."
)

_META = merge_tool_meta(
    {
        "unique.app/icon": "folder-tree",
        "unique.app/system-prompt": (
            "Choose this tool to browse or locate files/folders in the "
            "knowledge base before reading one with the read_file tool."
        ),
    },
    ContextRequirements(
        required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID],
    ),
    ConfigSchemaMeta(ContentTreeToolConfig),
)


@tool(
    name="content_tree",
    description=_TOOL_DESCRIPTION,
    meta=_META,
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def content_tree(
    mode: Annotated[
        Literal["tree", "list", "search"],
        Field(
            description=(
                "Which view to return. 'tree' for an overview, 'list' for a "
                "flat file listing (optionally scoped to folder_path), "
                "'search' for fuzzy filename lookup (requires `query`)."
            )
        ),
    ],
    max_depth: Annotated[
        int | None,
        Field(description="Maximum folder depth to render (1 = top-level only)."),
    ] = None,
    folder_path: Annotated[
        str | None,
        Field(
            description=(
                "Restrict the listing to files under this path, e.g. 'Contracts/2024'."
            )
        ),
    ] = None,
    query: Annotated[
        str | None,
        Field(description="Fuzzy text to match against file names and/or paths."),
    ] = None,
    limit: Annotated[
        int | None,
        Field(description="Maximum number of files/matches to return."),
    ] = None,
    min_score: Annotated[
        float | None,
        Field(
            description=(
                "Minimum fuzzy-match score in [0.0, 1.0]; higher is stricter. "
                "Leave unset unless you have a specific reason to change it."
            )
        ),
    ] = None,
    match_on: Annotated[
        MatchTarget | None,
        Field(
            description=(
                "Score against the file name ('key'), the full folder path "
                "('path'), or both ('both')."
            )
        ),
    ] = None,
    case_sensitive: Annotated[
        bool | None,
        Field(description="Whether fuzzy matching is case-sensitive."),
    ] = None,
    refresh: Annotated[
        bool,
        Field(
            description=(
                "If true, drop this caller's cached tree and refetch from the "
                "backend (~20s). Use when the user reports added/deleted/"
                "changed files and needs a fresh listing."
            )
        ),
    ] = False,
    config: ContentTreeToolConfig = Depends(get_tool_config(ContentTreeToolConfig)),
) -> CallToolResult:
    """Dispatch to ContentTree by mode; validate mode='search' needs query."""
    try:
        if mode == "search" and not query:
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text="query is required when mode='search'",
                    )
                ],
            )

        # In-body (not Depends) so identity-refusal ValueError surfaces as a tool error.
        settings = await get_unique_settings_async()
        company_id = settings.authcontext.get_confidential_company_id()
        user_id = settings.authcontext.get_confidential_user_id()

        cache = _get_tree_cache()

        async def _construct() -> ContentTree:
            return ContentTree(company_id=company_id, user_id=user_id)

        # SecretStr fields so cache/exception reprs stay masked.
        cache_key = (settings.authcontext.company_id, settings.authcontext.user_id)
        tree_svc, _ = await cache.get_or_fetch(cache_key, _construct)

        if refresh:
            tree_svc.invalidate_cache()

        metadata_filter = (
            config.metadata_filter.to_dict()
            if config.metadata_filter is not None
            else _DEFAULT_METADATA_FILTER_STATEMENT.to_dict()
        )

        if mode == "tree":
            text = await tree_svc.render_visible_tree_async(
                max_depth=max_depth,
                metadata_filter=metadata_filter,
                max_concurrent_scope_lookups=config.max_concurrent_scope_lookups,
            )
            return CallToolResult(content=[TextContent(type="text", text=text)])

        if mode == "list":
            rows = await tree_svc.resolve_visible_file_paths_async(
                metadata_filter=metadata_filter,
                max_concurrent_scope_lookups=config.max_concurrent_scope_lookups,
            )
            if folder_path:
                # Match against display paths (brackets stripped, sentinel dropped)
                # so filters like "SM/AlpenSys" work when segments are ["[SM]", ...].
                prefix = tuple(
                    _normalize_path_segment(p)
                    for p in folder_path.strip("/").split("/")
                )
                rows = [
                    (content_info, segments)
                    for content_info, segments in rows
                    if tuple(_display_path_segments(segments)[: len(prefix)]) == prefix
                ]
            effective_limit = limit if limit is not None else config.default_limit
            rows = rows[:effective_limit]
            frontend_base_url = McpSearchServerSettings().frontend_base_url_str()
            lines = [
                f"{_file_link(content_info, segments, frontend_base_url)} "
                f"(content_id={content_info.id})"
                for content_info, segments in rows
            ]
            text = "\n".join(lines) if lines else "No visible files match."
            return CallToolResult(content=[TextContent(type="text", text=text)])

        assert query is not None and mode == "search"
        matches = await tree_svc.search_visible_files_fuzzy_async(
            query,
            limit=limit if limit is not None else config.default_limit,
            min_score=min_score if min_score is not None else config.default_min_score,
            match_on=match_on if match_on is not None else config.default_match_on,
            case_sensitive=(
                case_sensitive
                if case_sensitive is not None
                else config.default_case_sensitive
            ),
            metadata_filter=metadata_filter,
            max_concurrent_scope_lookups=config.max_concurrent_scope_lookups,
        )
        frontend_base_url = McpSearchServerSettings().frontend_base_url_str()
        lines = [
            f"{_file_link(m.content_info, m.path_segments, frontend_base_url)} "
            f"(score={m.score:.2f}, content_id={m.content_info.id})"
            for m in matches
        ]
        text = "\n".join(lines) if lines else "No matching files found."
        return CallToolResult(content=[TextContent(type="text", text=text)])
    except Exception as exc:
        _LOGGER.exception("content_tree error")
        return CallToolResult(
            isError=True, content=[TextContent(type="text", text=str(exc))]
        )
