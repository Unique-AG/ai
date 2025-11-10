from datetime import datetime, timedelta
from logging import getLogger

from unique_quartr.constants.document_types import DocumentType
from unique_quartr.constants.event_types import EventType
from unique_quartr.endpoints.schemas import CompanyDto
from unique_quartr.service import QuartrService

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.collection.schema import Source

_LOGGER = getLogger(__name__)


def collect_earnings_calls(
    *,
    chunk_registry: ContentChunkRegistry,
    quartr_service: QuartrService,
    upload_scope_id: str,
    company: CompanyDto,
) -> list[Source]:
    _LOGGER.warning(
        "Collecting earnings calls as a data source is not implemented yet. No sources will be collected."
    )

    event_ids = quartr_service.get_event_subtype_ids_from_event_types(
        [EventType.EARNINGS_CALL]
    )
    document_ids = quartr_service.get_document_ids_from_document_types(
        [DocumentType.TRANSCRIPT, DocumentType.IN_HOUSE_TRANSCRIPT]
    )
    ticker = company.tickers[0].ticker if company.tickers else ""
    exchange = company.tickers[0].exchange if company.tickers else ""
    country = company.country if company.country else ""

    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    events = quartr_service.fetch_company_events(
        ticker=ticker,
        exchange=exchange,
        country=country,
        event_ids=event_ids,
        start_date=start_date,
        end_date=end_date,
    )

    with open("quartr_events.json", "w") as f:
        f.write("\n".join([event.model_dump_json(indent=2) for event in events]))

    event_ids = [int(event.id) for event in events]

    documents = quartr_service.fetch_event_documents(
        event_ids=event_ids,
        document_ids=document_ids,
    )

    with open("quartr_documents.json", "w") as f:
        f.write("\n".join([document.model_dump_json(indent=2) for document in documents]))
    return []
