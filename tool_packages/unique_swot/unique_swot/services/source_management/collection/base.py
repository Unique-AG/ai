from datetime import datetime
from logging import getLogger

from pydantic import BaseModel, ConfigDict
from unique_quartr.service import QuartrService
from unique_toolkit import KnowledgeBaseService
from unique_toolkit._common.docx_generator import DocxGeneratorService

from unique_swot.services.orchestrator.service import Notifier
from unique_swot.services.session.schema import UniqueCompanyListing
from unique_swot.services.source_management.collection.sources import (
    collect_earnings_calls,
    collect_knowledge_base,
    collect_web_sources,
)
from unique_swot.services.source_management.registry import ContentChunkRegistry
from unique_swot.services.source_management.schema import Source

_LOGGER = getLogger(__name__)


class CollectionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    company: UniqueCompanyListing
    use_earnings_calls: bool
    upload_scope_id_earnings_calls: str
    earnings_call_start_date: datetime
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
        notifier: Notifier,
        earnings_call_docx_generator_service: DocxGeneratorService,
    ):
        self._context = context
        self._knowledge_base_service = knowledge_base_service
        self._content_chunk_registry = content_chunk_registry
        self._quartr_service = quartr_service
        self._notifier = notifier
        self._earnings_call_docx_generator_service = (
            earnings_call_docx_generator_service
        )
        self._notification_title = "Collecting Sources"

    async def collect(self) -> list[Source]:
        await self._notifier.increment_progress(
            step_increment=0,
            progress_info="Starting to collect sources",
        )

        sources = []

        sources = await self._collect_internal_documents(
            metadata_filter=self._context.metadata_filter,
            chunk_registry=self._content_chunk_registry,
        )

        sources.extend(
            await self._collect_earnings_calls(
                quartr_service=self._quartr_service,
                use_earnings_calls=self._context.use_earnings_calls,
                upload_scope_id_earnings_calls=self._context.upload_scope_id_earnings_calls,
                chunk_registry=self._content_chunk_registry,
                company=self._context.company,
                docx_generator_service=self._earnings_call_docx_generator_service,
                knowledge_base_service=self._knowledge_base_service,
                earnings_call_start_date=self._context.earnings_call_start_date,
            )
        )
        sources.extend(
            await self._collect_web_sources(
                use_web_sources=self._context.use_web_sources,
                chunk_registry=self._content_chunk_registry,
            )
        )
        await self._notifier.notify(
            title=self._notification_title,
            description=f"Completed collecting {len(sources)} sources",
        )

        # Save Registry Store in Memory Service
        self._content_chunk_registry.save()

        await self._notifier.increment_progress(
            step_increment=0,
            progress_info="Completed collecting sources",
        )

        return sources

    async def _collect_earnings_calls(
        self,
        *,
        use_earnings_calls: bool,
        quartr_service: QuartrService | None,
        upload_scope_id_earnings_calls: str | None,
        chunk_registry: ContentChunkRegistry,
        company: UniqueCompanyListing,
        earnings_call_start_date: datetime,
        docx_generator_service: DocxGeneratorService,
        knowledge_base_service: KnowledgeBaseService,
    ) -> list[Source]:
        if not use_earnings_calls:
            _LOGGER.warning("No earnings calls will be collected.")
            return []

        if quartr_service is None:
            _LOGGER.error(
                "Quartr service is not provided. Check that your company has access to Quartr API."
            )
            return []

        if not upload_scope_id_earnings_calls:
            _LOGGER.error(
                "Upload scope ID for earnings calls is not provided. This is a mandatory parameter when using earnings calls as a data source."
            )
            return []

        _LOGGER.info("Collecting earnings calls!")
        await self._notifier.notify(
            title=self._notification_title,
            description="Collecting Earnings Calls",
        )
        await self._notifier.increment_progress(
            step_increment=0,
            progress_info=f"Collecting earnings calls from {earnings_call_start_date.strftime('%Y-%m-%d')} to today",
        )
        sources = await collect_earnings_calls(
            chunk_registry=chunk_registry,
            quartr_service=quartr_service,
            upload_scope_id=upload_scope_id_earnings_calls,
            company=company,
            earnings_call_start_date=earnings_call_start_date,
            docx_generator_service=docx_generator_service,
            knowledge_base_service=knowledge_base_service,
        )
        await self._notifier.increment_progress(
            step_increment=0,
            progress_info=f"{len(sources)} earnings call(s) collected",
        )
        return sources

    async def _collect_web_sources(
        self, *, use_web_sources: bool, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if not use_web_sources:
            _LOGGER.warning("No web sources will be collected.")
            return []
        _LOGGER.info("Collecting web sources!")
        await self._notifier.notify(
            title=self._notification_title,
            description="Collecting Web Sources",
        )
        await self._notifier.increment_progress(
            step_increment=0,
            progress_info="Collecting web sources",
        )
        return collect_web_sources()

    async def _collect_internal_documents(
        self, *, metadata_filter: dict | None, chunk_registry: ContentChunkRegistry
    ) -> list[Source]:
        if metadata_filter is None:
            _LOGGER.warning(
                "No where clause provided. No internal documents will be collected."
            )
            return []

        _LOGGER.info("Collecting internal documents!")
        await self._notifier.notify(
            title=self._notification_title,
            description="Collecting Internal Documents",
        )
        await self._notifier.increment_progress(
            step_increment=0,
            progress_info="Collecting internal documents",
        )
        sources = await collect_knowledge_base(
            knowledge_base_service=self._knowledge_base_service,
            metadata_filter=metadata_filter,
            chunk_registry=chunk_registry,
        )
        await self._notifier.increment_progress(
            step_increment=0,
            progress_info=f"Finished collecting {len(sources)} internal documents",
        )
        return sources
