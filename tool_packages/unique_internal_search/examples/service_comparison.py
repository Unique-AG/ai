"""
v1 vs v2 InternalSearchService — what actually changed and why.
Run with: uv run python examples/service_comparison.py
"""

# ---------------------------------------------------------------------------
# v1 — Tool IS-A Service via diamond inheritance
# ---------------------------------------------------------------------------
#
# class InternalSearchTool(Tool[InternalSearchConfig], InternalSearchService):
#
#     def __init__(self, configuration, event, ...):
#         Tool.__init__(self, configuration, event, ...)
#
#         # deps wired manually by caller, every time
#         content_service = ContentService.from_event(self.event)
#         chunk_relevancy_sorter = ChunkRelevancySorter.from_event(self.event)
#
#         # chat_id resolved here in __init__ (correlation logic inline)
#         if isinstance(self.event, (ChatEvent, Event)):
#             chat_id = self.event.payload.correlation.parent_chat_id \
#                       if self.event.payload.correlation \
#                       else self.event.payload.chat_id
#         else:
#             chat_id = None
#
#         # 8-param init mixing service + tool concerns
#         InternalSearchService.__init__(
#             self,
#             config=configuration,
#             content_service=content_service,
#             chunk_relevancy_sorter=chunk_relevancy_sorter,
#             chat_id=chat_id,
#             company_id=self.event.company_id,
#             logger=self.logger,
#             message_step_logger=self._message_step_logger,
#             display_name=self._display_name,
#         )
#
#     async def run(self, tool_call):
#         # query normalisation happens here AND again inside service.search()
#         search_strings = [clean_search_string(s) for s in tool_call.arguments["search_string"]]
#         search_strings = list(dict.fromkeys(search_strings))[:self.config.max_search_strings]
#
#         # UI/feature flag logic baked into the run path
#         await self._message_step_logger.display_search_in_message_log(...)
#         if not feature_flags.enable_new_answers_ui_un_14411.is_enabled(self.company_id):
#             await self.post_progress_message(...)
#
#         # service.search() internally:
#         #   - backs up content_service._metadata_filter
#         #   - sets it to None if chat_only          ← mutating a private attr of another object
#         #   - runs searches in parallel
#         #   - restores content_service._metadata_filter  ← easy to forget, not thread-safe
#         #   - stores result in self.debug_info       ← side effect, leaks between calls
#         selected_chunks = await self.search(**tool_call.arguments, tool_call=tool_call)
#
#         selected_chunks = append_metadata_in_chunks(selected_chunks, ...)
#         return ToolCallResponse(content_chunks=selected_chunks, debug_info=self.debug_info)


# ---------------------------------------------------------------------------
# v2 — Tool HAS-A Service via composition
# ---------------------------------------------------------------------------

import asyncio
import logging

from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.service import ContentService

from unique_internal_search.config import (
    InternalSearchServiceConfig as InternalSearchServiceConfigV1,
)
from unique_internal_search.schemas import (
    InternalSearchProgressMessage,
    InternalSearchServiceConfig,
    InternalSearchState,
    SearchStage,
)
from unique_internal_search.service import (
    InternalSearchService as InternalSearchServiceV1,
)
from unique_internal_search.service_v2 import InternalSearchService

SEARCH_QUERIES = ["Q2 revenue", "gross margin 2024", "unique ai"]
SCOPE_IDS = ["scope_v2c5urvrvslt5vw3epvkfw0g"]

settings = UniqueSettings.from_env_auto_with_sdk_init()
logger = logging.getLogger(__name__)


async def run_v1() -> None:
    config_v1 = InternalSearchServiceConfigV1(
        scope_ids=SCOPE_IDS, language_model_max_input_tokens=128_000
    )
    content_service = ContentService.from_settings(settings)
    chunk_relevancy_sorter = ChunkRelevancySorter.from_settings(settings)
    auth = settings.auth
    service_v1 = InternalSearchServiceV1(
        config=config_v1,
        content_service=content_service,
        chunk_relevancy_sorter=chunk_relevancy_sorter,
        chat_id=None,
        company_id=auth.company_id.get_secret_value(),
        logger=logger,
    )
    chunks = await service_v1.search(search_string=SEARCH_QUERIES)
    print(f"[v1] selected {len(chunks)} chunks")
    print(f"[v1] debug_info: {service_v1.debug_info}")


async def run_v2() -> None:
    config = InternalSearchServiceConfig(scope_ids=SCOPE_IDS)
    service = InternalSearchService.from_config(config)
    service.bind_settings(settings)
    service.state = InternalSearchState(
        search_queries=SEARCH_QUERIES,
        chat_only=config.chat_only,
        language_model_max_input_tokens=128_000,
    )

    async def on_progress(msg: InternalSearchProgressMessage) -> None:
        if msg.stage == SearchStage.COMPLETED:
            print(f"[v2] done: {len(msg.chunks)} chunks")
        else:
            print(f"[v2] {msg.stage}: {msg.search_queries}")

    service.progress_publisher.subscribe(on_progress)
    result = await service.run()
    print(f"[v2] selected {len(result.chunks)} chunks")
    print(f"[v2] debug_info: {result.debug_info}")


async def main() -> None:
    print("=== v1 ===")
    await run_v1()
    print("\n=== v2 ===")
    await run_v2()


asyncio.run(main())
