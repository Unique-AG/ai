from __future__ import annotations

from typing import Annotated, override

from fastmcp import FastMCP
from fastmcp.dependencies import Depends
from mcp.types import CallToolResult, TextContent
from pydantic import Field
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.components.internal_search import (
    ChatInternalSearchService,
    InternalSearchResult,
    KnowledgeBaseInternalSearchService,
)
from unique_toolkit.components.internal_search.knowledge_base.schemas import (
    KnowledgeBaseInternalSearchState,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

from unique_mcp.internal_search.config import (
    BaseInternalSearchMcpConfig,
    ChatInternalSearchMcpConfig,
    KnowledgeBaseInternalSearchMcpConfig,
)
from unique_mcp.internal_search.meta import InternalSearchRequestMeta
from unique_mcp.provider.base import BaseProvider
from unique_mcp.provider.context_provider import UniqueContextProvider


def _populate_common_state(
    *,
    service: ChatInternalSearchService | KnowledgeBaseInternalSearchService,
    search_string: str | list[str],
    request_meta: InternalSearchRequestMeta,
) -> None:
    service.state.search_queries = (
        [search_string] if isinstance(search_string, str) else search_string
    )

    language_model_info = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120
    )
    service.state.language_model_info = language_model_info
    service.state.language_model_max_input_tokens = (
        request_meta.language_model_max_input_tokens
        or language_model_info.token_limits.token_limit_input
    )


def _format_tool_result(
    *,
    config: BaseInternalSearchMcpConfig,
    result: InternalSearchResult,
) -> CallToolResult:
    if not result.chunks:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=config.no_results_message,
                    _meta={"debug_info": result.debug_info},
                )
            ]
        )

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=chunk.text,
                _meta={
                    "chunk": chunk.model_dump(mode="json"),
                    "debug_info": result.debug_info,
                },
            )
            for chunk in result.chunks
        ]
    )


class ChatInternalSearchToolProvider(BaseProvider):
    _config: ChatInternalSearchMcpConfig
    _context_provider: UniqueContextProvider

    def __init__(
        self,
        *,
        config: ChatInternalSearchMcpConfig,
        context_provider: UniqueContextProvider,
    ) -> None:
        self._config = config
        self._context_provider = context_provider

    def _build_service(
        self,
        *,
        settings: UniqueSettings,
        request_meta: InternalSearchRequestMeta,
    ) -> ChatInternalSearchService:
        chat_settings = UniqueSettings(
            auth=settings.authcontext,
            app=settings.app,
            api=settings.api,
            chat_event_filter_options=settings.chat_event_filter_options,
            chat=request_meta.to_chat_context(),
        )
        return ChatInternalSearchService.from_config(
            self._config.execution_config
        ).bind_settings(chat_settings)

    @override
    def register(self, *, mcp: FastMCP) -> None:
        @mcp.tool(
            name=self._config.name,
            description=self._config.description,
            meta=self._config.tool_meta or None,
        )
        async def _search(
            search_string: Annotated[
                str | list[str],
                Field(description=self._config.param_description_search_string),
            ],
            settings: UniqueSettings = Depends(self._context_provider.get_settings),
        ) -> CallToolResult:
            request_meta = InternalSearchRequestMeta.from_request_meta(
                self._context_provider.get_request_meta()
            )
            service = self._build_service(
                settings=settings,
                request_meta=request_meta,
            )
            _populate_common_state(
                service=service,
                search_string=search_string,
                request_meta=request_meta,
            )
            service.state.content_ids = request_meta.chat_content_ids
            result = await service.run()
            return _format_tool_result(config=self._config, result=result)


class KnowledgeBaseInternalSearchToolProvider(BaseProvider):
    _config: KnowledgeBaseInternalSearchMcpConfig
    _context_provider: UniqueContextProvider

    def __init__(
        self,
        *,
        config: KnowledgeBaseInternalSearchMcpConfig,
        context_provider: UniqueContextProvider,
    ) -> None:
        self._config = config
        self._context_provider = context_provider

    def _build_service(
        self, *, settings: UniqueSettings
    ) -> KnowledgeBaseInternalSearchService:
        return KnowledgeBaseInternalSearchService.from_config(
            self._config.execution_config
        ).bind_settings(settings)

    @override
    def register(self, *, mcp: FastMCP) -> None:
        @mcp.tool(
            name=self._config.name,
            description=self._config.description,
            meta=self._config.tool_meta or None,
        )
        async def _search(
            search_string: Annotated[
                str | list[str],
                Field(description=self._config.param_description_search_string),
            ],
            settings: UniqueSettings = Depends(self._context_provider.get_settings),
        ) -> CallToolResult:
            request_meta = InternalSearchRequestMeta.from_request_meta(
                self._context_provider.get_request_meta()
            )
            service = self._build_service(settings=settings)
            _populate_common_state(
                service=service,
                search_string=search_string,
                request_meta=request_meta,
            )
            service.state.content_ids = request_meta.knowledge_base_content_ids
            if request_meta.metadata_filter is not None:
                kb_state = service.state
                assert isinstance(kb_state, KnowledgeBaseInternalSearchState)
                kb_state.metadata_filter_override = request_meta.metadata_filter
            result = await service.run()
            return _format_tool_result(config=self._config, result=result)


__all__ = [
    "ChatInternalSearchToolProvider",
    "KnowledgeBaseInternalSearchToolProvider",
]
