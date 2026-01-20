from datetime import datetime
from logging import getLogger

from pydantic import BaseModel, ConfigDict
from unique_quartr.service import QuartrService
from unique_toolkit import KnowledgeBaseService
from unique_toolkit._common.docx_generator import DocxGeneratorService
from unique_toolkit.content import Content

from unique_swot.services.orchestrator.service import StepNotifier
from unique_swot.services.session.schema import UniqueCompanyListing
from unique_swot.services.source_management.collection.sources import (
    collect_earnings_calls,
    collect_knowledge_base,
    collect_web_sources,
)

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
        quartr_service: QuartrService | None = None,
        earnings_call_docx_generator_service: DocxGeneratorService,
    ):
        self._context = context
        self._knowledge_base_service = knowledge_base_service
        self._quartr_service = quartr_service
        self._earnings_call_docx_generator_service = (
            earnings_call_docx_generator_service
        )

    @property
    def notification_title(self) -> str:
        return "**Collecting Sources**"

    async def collect(self, *, step_notifier: StepNotifier) -> list[Content]:
        await step_notifier.notify(title=self.notification_title, progress=0)

        internal_documents_sources = await self._collect_internal_documents(
            metadata_filter=self._context.metadata_filter, step_notifier=step_notifier
        )

        earnings_calls_sources = await self._collect_earnings_calls(
            quartr_service=self._quartr_service,
            use_earnings_calls=self._context.use_earnings_calls,
            upload_scope_id_earnings_calls=self._context.upload_scope_id_earnings_calls,
            company=self._context.company,
            docx_generator_service=self._earnings_call_docx_generator_service,
            knowledge_base_service=self._knowledge_base_service,
            earnings_call_start_date=self._context.earnings_call_start_date,
            step_notifier=step_notifier,
        )

        web_sources = await self._collect_web_sources(
            use_web_sources=self._context.use_web_sources,
            step_notifier=step_notifier,
        )

        all_sources = internal_documents_sources + earnings_calls_sources + web_sources

        await step_notifier.notify(
            title=self.notification_title,
            description=f"Collected {len(all_sources)} sources!",
            progress=100,
            completed=True,
        )

        return all_sources

    async def _collect_earnings_calls(
        self,
        *,
        use_earnings_calls: bool,
        quartr_service: QuartrService | None,
        upload_scope_id_earnings_calls: str | None,
        company: UniqueCompanyListing,
        earnings_call_start_date: datetime,
        docx_generator_service: DocxGeneratorService,
        knowledge_base_service: KnowledgeBaseService,
        step_notifier: StepNotifier,
    ) -> list[Content]:
        if not use_earnings_calls:
            _LOGGER.warning("No earnings calls will be collected.")
            return []

        if quartr_service is None:
            _LOGGER.error(
                "Quartr service is not provided. Check that your company has access to Quartr API."
            )
            await step_notifier.notify(
                title=self.notification_title,
                description="Cannot collect earnings calls. Quartr service is not provided. Check that your company has access to Quartr API.",
                progress=0,
                completed=True,
            )
            return []

        if not upload_scope_id_earnings_calls:
            _LOGGER.error(
                "Upload scope ID for earnings calls is not provided. This is a mandatory parameter when using earnings calls as a data source."
            )
            await step_notifier.notify(
                title=self.notification_title,
                description="Cannot collect earnings calls. Upload scope ID for earnings calls is not provided. This is a mandatory parameter when using earnings calls as a data source.",
                progress=0,
                completed=True,
            )
            return []

        _LOGGER.info("Collecting earnings calls!")

        contents = await collect_earnings_calls(
            quartr_service=quartr_service,
            upload_scope_id=upload_scope_id_earnings_calls,
            company=company,
            earnings_call_start_date=earnings_call_start_date,
            docx_generator_service=docx_generator_service,
            knowledge_base_service=knowledge_base_service,
        )

        await step_notifier.notify(
            title=self.notification_title,
            description=f"Collected {len(contents)} earnings call(s)!",
            progress=0,
        )
        return contents

    async def _collect_web_sources(
        self,
        *,
        use_web_sources: bool,
        step_notifier: StepNotifier,
    ) -> list[Content]:
        if not use_web_sources:
            _LOGGER.warning("No web sources will be collected.")
            return []
        _LOGGER.info("Collecting web sources!")

        return collect_web_sources()

    async def _collect_internal_documents(
        self,
        *,
        metadata_filter: dict | None,
        step_notifier: StepNotifier,
    ) -> list[Content]:
        if metadata_filter is None:
            _LOGGER.warning(
                "No where clause provided. No internal documents will be collected."
            )
            return []

        _LOGGER.info("Collecting internal documents!")

        contents = await collect_knowledge_base(
            knowledge_base_service=self._knowledge_base_service,
            metadata_filter=metadata_filter,
        )
        await step_notifier.notify(
            title=self.notification_title,
            description=f"Collected {len(contents)} internal documents!",
            progress=0,
        )
        return contents
