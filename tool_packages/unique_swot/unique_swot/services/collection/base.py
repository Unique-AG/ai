from logging import getLogger

from pydantic import BaseModel, ConfigDict
from unique_toolkit import KnowledgeBaseService

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.collection.schema import Source
from unique_swot.services.collection.sources import (
    collect_earnings_calls,
    collect_knowledge_base,
    collect_web_sources,
)
from unique_swot.services.notifier import (
    MessageLogEvent,
    MessageLogStatus,
    ProgressNotifier,
)

_LOGGER = getLogger(__name__)


class CollectionContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    use_earnings_calls: bool
    use_web_sources: bool
    metadata_filter: dict | None


class SourceCollectionManager:
    def __init__(
        self,
        *,
        context: CollectionContext,
        knowledge_base_service: KnowledgeBaseService,
        content_chunk_registry: ContentChunkRegistry,
        notifier: ProgressNotifier,
    ):
        self._context = context
        self._knowledge_base_service = knowledge_base_service
        self._content_chunk_registry = content_chunk_registry
        self._notifier = notifier

    def collect_sources(self) -> list[Source]:
        notification_title = "Collecting Sources"
        self._notifier.notify(
            notification_title=notification_title,
            status=MessageLogStatus.RUNNING,
            message_log_event=MessageLogEvent(
                type="InternalSearch",
                text=self._get_message_log_event_text(),
            ),
        )
        sources = self.collect_internal_documents(
            metadata_filter=self._context.metadata_filter,
            chunk_registry=self._content_chunk_registry,
        )

        sources.extend(
            self.collect_earnings_calls(
                use_earnings_calls=self._context.use_earnings_calls,
                chunk_registry=self._content_chunk_registry,
            )
        )
        sources.extend(
            self.collect_web_sources(
                use_web_sources=self._context.use_web_sources,
                chunk_registry=self._content_chunk_registry,
            )
        )
        self._notifier.notify(
            notification_title=notification_title,
            status=MessageLogStatus.COMPLETED,
            message_log_event=MessageLogEvent(
                type="InternalSearch",
                text=f"Completed collecting {len(sources)} sources",
            ),
        )

        # Save Registry Store in Memory Service
        self._content_chunk_registry.save()

        self._notifier.update_progress(step_precentage_increment=1)

        return sources

    def collect_earnings_calls(
        self, *, use_earnings_calls: bool, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if not use_earnings_calls:
            _LOGGER.warning("No earnings calls will be collected.")
            return []
        _LOGGER.info("Collecting earnings calls!")
        return collect_earnings_calls()

    def collect_web_sources(
        self, *, use_web_sources: bool, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if not use_web_sources:
            _LOGGER.warning("No web sources will be collected.")
            return []
        _LOGGER.info("Collecting web sources!")
        return collect_web_sources()

    def collect_internal_documents(
        self, *, metadata_filter: dict | None, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if metadata_filter is None:
            _LOGGER.warning(
                "No where clause provided. No internal documents will be collected."
            )
            return []
        _LOGGER.info("Collecting internal documents!")
        _LOGGER.info(f"Metadata filter: {metadata_filter}")
        return collect_knowledge_base(
            knowledge_base_service=self._knowledge_base_service,
            metadata_filter=metadata_filter,
            chunk_registry=chunk_registry,
        )

    def _get_message_log_event_text(self) -> str:
        notification_prefix = "Collecting Sources from: "
        if self._context.metadata_filter is not None:
            notification_prefix += "Internal Documents"
        if self._context.use_earnings_calls:
            notification_prefix += "Earnings Calls"
        if self._context.use_web_sources:
            notification_prefix += "Web Sources"
        return notification_prefix
