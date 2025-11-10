from logging import getLogger

from pydantic import BaseModel, ConfigDict
from unique_quartr.endpoints.schemas import CompanyDto
from unique_quartr.service import QuartrService
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
    
    company: CompanyDto
    use_earnings_calls: bool
    upload_scope_id_earnings_calls: str
    
    use_web_sources: bool
    metadata_filter: dict | None


class SourceCollectionManager:
    def __init__(
        self,
        *,
        context: CollectionContext,
        knowledge_base_service: KnowledgeBaseService,
        content_chunk_registry: ContentChunkRegistry,
        quartr_service: QuartrService | None = None,
        notifier: ProgressNotifier,
    ):
        self._context = context
        self._knowledge_base_service = knowledge_base_service
        self._content_chunk_registry = content_chunk_registry
        self._quartr_service = quartr_service
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
        sources = []
        # sources = self._collect_internal_documents(
        #     metadata_filter=self._context.metadata_filter,
        #     chunk_registry=self._content_chunk_registry,
        # )

        sources.extend(
            self._collect_earnings_calls(
                quartr_service=self._quartr_service,
                use_earnings_calls=self._context.use_earnings_calls,
                upload_scope_id_earnings_calls=self._context.upload_scope_id_earnings_calls,
                chunk_registry=self._content_chunk_registry,
                company=self._context.company,
            )
        )
        sources.extend(
            self._collect_web_sources(
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

    def _collect_earnings_calls(
        self,
        *,
        use_earnings_calls: bool,
        quartr_service: QuartrService | None,
        upload_scope_id_earnings_calls: str | None,
        chunk_registry: ContentChunkRegistry,
        company: CompanyDto,
    ) -> list[Source]:
        if not use_earnings_calls:
            _LOGGER.warning("No earnings calls will be collected.")
            return []
        
        if quartr_service is None:
            _LOGGER.error("Quartr service is not provided. Check that your company has access to Quartr API.")
            return []
        
        if not upload_scope_id_earnings_calls:
            _LOGGER.error("Upload scope ID for earnings calls is not provided. This is a mandatory parameter when using earnings calls as a data source.")
            return []
        
        _LOGGER.info("Collecting earnings calls!")
        return collect_earnings_calls(
            chunk_registry=chunk_registry,
            quartr_service=quartr_service,
            upload_scope_id=upload_scope_id_earnings_calls,
            company=company,
        )



    def _collect_web_sources(
        self, *, use_web_sources: bool, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if not use_web_sources:
            _LOGGER.warning("No web sources will be collected.")
            return []
        _LOGGER.info("Collecting web sources!")
        return collect_web_sources()

    def _collect_internal_documents(
        self, *, metadata_filter: dict | None, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if metadata_filter is None:
            _LOGGER.warning(
                "No where clause provided. No internal documents will be collected."
            )
            return []
        _LOGGER.info("Collecting internal documents!")

        return collect_knowledge_base(
            knowledge_base_service=self._knowledge_base_service,
            metadata_filter=metadata_filter,
            chunk_registry=chunk_registry,
        )

    def _get_message_log_event_text(self) -> str:
        notification_prefix = "Collecting Sources from: "
        sources = []
        if self._context.metadata_filter is not None:
            sources.append("Internal Documents")
        if self._context.use_earnings_calls:
            sources.append("Earnings Calls")
        if self._context.use_web_sources:
            sources.append("Web Sources")
        return f"{notification_prefix} - {', '.join(sources)}"
