from functools import reduce

from pydantic import BaseModel
from unique_toolkit._common.endpoint_requestor import (
    RequestorType,
    build_requestor,
)

from unique_quartr.constants.document_types import DocumentType
from unique_quartr.constants.event_types import (
    EVENT_TYPE_MAPPING,
    EventSubType,
    EventType,
)
from unique_quartr.endpoints.api import (
    QuartrDocumentsApiOperation,
    QuartrDocumentsTypesApiOperation,
    QuartrEventsApiOperation,
    get_quartr_context,
)
from unique_quartr.endpoints.schemas import (
    Direction,
    DocumentDto,
    EventDto,
    PublicV3DocumentsGetParametersQuery,
    PublicV3DocumentTypesGetParametersQuery,
    PublicV3EventsGetParametersQuery,
)


class EventResults(BaseModel):
    data: list[EventDto]


class DocumentResults(BaseModel):
    data: list[DocumentDto]


class QuartrService:
    def __init__(
        self,
        *,
        company_id: str,
        requestor_type: RequestorType,
    ):
        self._context = get_quartr_context(company_id=company_id)

        self.events_requestor = build_requestor(
            requestor_type,
            QuartrEventsApiOperation,
            PublicV3EventsGetParametersQuery,
        )
        self.documents_requestor = build_requestor(
            requestor_type,
            QuartrDocumentsApiOperation,
            PublicV3DocumentsGetParametersQuery,
        )
        self.documents_types_requestor = build_requestor(
            requestor_type,
            QuartrDocumentsTypesApiOperation,
            PublicV3DocumentTypesGetParametersQuery,
        )

    @staticmethod
    def get_event_subtype_ids_from_event_types(
        event_types: list[EventType],
    ) -> list[int]:
        event_subtypes: list[EventSubType] = reduce(
            lambda acc, x: acc + EVENT_TYPE_MAPPING[x], event_types, []
        )
        return [event_subtype.value for event_subtype in event_subtypes]

    @staticmethod
    def get_document_ids_from_document_types(
        document_types: list[DocumentType],
    ) -> list[int]:
        return [document_type.value for document_type in document_types]

    def fetch_company_events(
        self,
        ticker: str,
        exchange: str,
        country: str,
        event_ids: list[int],
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 500,
        max_iteration: int = 20,
    ) -> EventResults:
        """Retrieve all earnings call events for a given company.

        Args:
            ticker (str): Company ticker symbol (e.g. 'AMZN', 'AAPL')
            exchange (str): Exchange code (e.g. 'BASE', 'NasdaqGS')
            country (str): Country code (e.g. 'US')
            event_ids (list[int]): List of event IDs to retrieve events for
            start_date (str | None): Optional start date to retrieve events from in ISO format (e.g. '2024-01-01')
            end_date (str | None): Optional end date to retrieve events from in ISO format (e.g. '2024-01-01')
            limit (int): Maximum number of events to retrieve per request. Defaults to 500.
            max_iteration (int): Maximum number of iterations to retrieve events. Defaults to 20.

        Returns:
            list[EventDto]: List of EventDto objects
        """

        events = []
        cursor = 0
        for _ in range(max_iteration):
            response = self.events_requestor.request(
                context=self._context,
                countries=country,
                exchanges=exchange,
                tickers=ticker,
                limit=limit,
                direction=Direction.ASC,
                type_ids=_convert_ids_to_str(event_ids),
                start_date=start_date,
                end_date=end_date,
                cursor=cursor,
            )

            events.extend(response.model_dump()["data"])
            cursor = response.pagination.next_cursor
            if cursor is None:
                break

        return EventResults.model_validate({"data": events})

    def fetch_event_documents(
        self,
        event_ids: list[int],
        document_ids: list[int],
        limit: int = 500,
        max_iteration: int = 20,
    ) -> DocumentResults:
        """Retrieve documents for a list of events from Quartr API.

        Args:
            event_ids (list[int]): List of event IDs to retrieve documents for
            document_ids (list[int]): List of document IDs to retrieve documents for
            limit (int): Maximum number of documents to retrieve per request. Defaults to 500.
            max_iteration (int): Maximum number of iterations to retrieve documents. Defaults to 20.

        Returns:
            list[DocumentDto]: List of DocumentDto objects
        """

        documents = []
        cursor = 0
        for _ in range(max_iteration):
            response = self.documents_requestor.request(
                context=self._context,
                event_ids=_convert_ids_to_str(event_ids),
                type_ids=_convert_ids_to_str(document_ids),
                limit=limit,
                cursor=cursor,
            )
            documents.extend(response.model_dump()["data"])
            cursor = response.pagination.next_cursor
            if cursor is None:
                break

        return DocumentResults.model_validate({"data": documents})


def _convert_ids_to_str(ids: list[int]) -> str:
    return ",".join([str(id) for id in ids])
