from functools import reduce

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
    get_quartr_context,
    quartr_documents_api_operation,
    quartr_documents_types_api_operation,
    quartr_events_api_operation,
)
from unique_quartr.endpoints.schemas import (
    Direction,
    DocumentDto,
    EventDto,
    PublicV3DocumentsGetParametersQuery,
    PublicV3DocumentTypesGetParametersQuery,
    PublicV3EventsGetParametersQuery,
)


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
            quartr_events_api_operation,
            PublicV3EventsGetParametersQuery,
        )
        self.documents_requestor = build_requestor(
            requestor_type,
            quartr_documents_api_operation,
            PublicV3DocumentsGetParametersQuery,
        )
        self.documents_types_requestor = build_requestor(
            requestor_type,
            quartr_documents_types_api_operation,
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
    ) -> list[EventDto]:
        """Retrieve all earnings call events for a given company.

        Args:
            ticker (str): Company ticker symbol (e.g. 'AMZN', 'AAPL')
            exchange (str): Exchange code (e.g. 'BASE', 'NasdaqGS')
            country (str): Country code (e.g. 'US')
            start_date (str | None): Optional start date to retrieve events from in ISO format (e.g. '2024-01-01')
            end_date (str | None): Optional end date to retrieve events from in ISO format (e.g. '2024-01-01')

        Returns:
            pd.DataFrame: DataFrame containing earnings call events with columns:
                - company_id (float): Quartr company ID
                - date (datetime): ChatEvent date
                - id (float): ChatEvent ID
                - title (str): ChatEvent title (e.g. 'Q1 2024')
                - type_id (float): ChatEvent type ID
                - fiscal_year (float): Fiscal year
                - fiscal_period (str): Fiscal period (e.g. 'Q1')
                - backlink_url (str): URL to event page on Quartr
                - updated_at (datetime): Last update timestamp
                - created_at (datetime): Creation timestamp
                - passed (bool): Whether the event has passed
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

        return events

    def fetch_event_documents(
        self,
        event_ids: list[int],
        document_ids: list[int],
        limit: int = 500,
        max_iteration: int = 20,
    ) -> list[DocumentDto]:
        """Retrieve documents for a list of events from Quartr API.

        Args:
            event_ids (list[str]): List of event IDs to retrieve documents for
            document_type_ids (list[str]): List of document type IDs to filter by
            limit (int, optional): Maximum number of documents to retrieve per request. Defaults to 500.

        Returns:
            pd.DataFrame: DataFrame containing event documents with columns:
                - company_id (float): Quartr company ID
                - event_id (float): ChatEvent ID
                - file_url (str): URL to document file
                - id (float): Document ID
                - type_id (float): Document type ID
                - updated_at (datetime): Last update timestamp
                - created_at (datetime): Creation timestamp
                - document_type (str): Document type name
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

        return documents


def _convert_ids_to_str(ids: list[int]) -> str:
    return ",".join([str(id) for id in ids])
