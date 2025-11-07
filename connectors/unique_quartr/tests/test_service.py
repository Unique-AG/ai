from unittest.mock import Mock, patch

import pytest

from unique_quartr.constants.document_types import DocumentType
from unique_quartr.constants.event_types import EventSubType, EventType
from unique_quartr.endpoints.schemas import (
    CursorPagination,
    Direction,
    PaginatedDocumentResponseDto,
    PaginatedEventResponseDto,
)
from unique_quartr.service import QuartrService, _convert_ids_to_str


class TestQuartrService:
    """Test cases for QuartrService class."""

    @pytest.fixture
    def mock_context(self):
        """Mock the get_quartr_context function."""
        with patch("unique_quartr.service.get_quartr_context") as mock:
            mock_ctx = Mock()
            mock.return_value = mock_ctx
            yield mock

    @pytest.fixture
    def mock_build_requestor(self):
        """Mock the build_requestor function."""
        with patch("unique_quartr.service.build_requestor") as mock:
            yield mock

    @pytest.fixture
    def quartr_service(self, mock_context, mock_build_requestor):
        """Create a QuartrService instance with mocked dependencies."""
        from unique_toolkit._common.endpoint_requestor import RequestorType

        events_requestor = Mock()
        documents_requestor = Mock()
        document_types_requestor = Mock()

        mock_build_requestor.side_effect = [
            events_requestor,
            documents_requestor,
            document_types_requestor,
        ]

        service = QuartrService(
            company_id="test_company",
            requestor_type=RequestorType.REQUESTS,
        )

        service.events_requestor = events_requestor
        service.documents_requestor = documents_requestor
        service.documents_types_requestor = document_types_requestor

        return service

    def test_init(self, mock_context, mock_build_requestor):
        """Test QuartrService initialization."""
        from unique_toolkit._common.endpoint_requestor import RequestorType

        service = QuartrService(
            company_id="test_company",
            requestor_type=RequestorType.REQUESTS,
        )

        mock_context.assert_called_once_with(company_id="test_company")
        assert mock_build_requestor.call_count == 3
        assert hasattr(service, "events_requestor")
        assert hasattr(service, "documents_requestor")
        assert hasattr(service, "documents_types_requestor")

    def test_get_event_subtype_ids_from_event_types_single(self):
        """Test get_event_subtype_ids_from_event_types with a single event type."""
        event_types = [EventType.EARNINGS_CALL]
        result = QuartrService.get_event_subtype_ids_from_event_types(event_types)

        expected = [
            EventSubType.Q1.value,
            EventSubType.Q2.value,
            EventSubType.Q3.value,
            EventSubType.Q4.value,
            EventSubType.H1.value,
            EventSubType.H2.value,
        ]
        assert result == expected

    def test_get_event_subtype_ids_from_event_types_multiple(self):
        """Test get_event_subtype_ids_from_event_types with multiple event types."""
        event_types = [EventType.ANALYST_DAY, EventType.CAPITAL_MARKETS_DAY]
        result = QuartrService.get_event_subtype_ids_from_event_types(event_types)

        expected = [EventSubType.ANALYST_DAY.value, EventSubType.CMD.value]
        assert result == expected

    def test_get_event_subtype_ids_from_event_types_empty(self):
        """Test get_event_subtype_ids_from_event_types with empty list."""
        event_types = []
        result = QuartrService.get_event_subtype_ids_from_event_types(event_types)
        assert result == []

    def test_get_document_ids_from_document_types_single(self):
        """Test get_document_ids_from_document_types with a single document type."""
        document_types = [DocumentType.TRANSCRIPT]
        result = QuartrService.get_document_ids_from_document_types(document_types)

        assert result == [15]

    def test_get_document_ids_from_document_types_multiple(self):
        """Test get_document_ids_from_document_types with multiple document types."""
        document_types = [
            DocumentType.TRANSCRIPT,
            DocumentType.SLIDES,
            DocumentType.QUARTERLY_REPORT_10Q,
        ]
        result = QuartrService.get_document_ids_from_document_types(document_types)

        assert result == [15, 5, 7]

    def test_get_document_ids_from_document_types_empty(self):
        """Test get_document_ids_from_document_types with empty list."""
        document_types = []
        result = QuartrService.get_document_ids_from_document_types(document_types)
        assert result == []

    def test_fetch_company_events_success(
        self, quartr_service, paginated_events_response
    ):
        """Test fetch_company_events with successful response."""
        quartr_service.events_requestor.request.return_value = paginated_events_response

        events = quartr_service.fetch_company_events(
            ticker="AAPL",
            exchange="NasdaqGS",
            country="US",
            event_ids=[26, 27],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        assert len(events) == 1
        assert events[0]["id"] == 128301
        assert events[0]["title"] == "Q1 2024"

        quartr_service.events_requestor.request.assert_called_once()
        call_kwargs = quartr_service.events_requestor.request.call_args.kwargs
        assert call_kwargs["tickers"] == "AAPL"
        assert call_kwargs["exchanges"] == "NasdaqGS"
        assert call_kwargs["countries"] == "US"
        assert call_kwargs["type_ids"] == "26,27"
        assert call_kwargs["start_date"] == "2024-01-01"
        assert call_kwargs["end_date"] == "2024-12-31"
        assert call_kwargs["limit"] == 500
        assert call_kwargs["direction"] == Direction.ASC

    def test_fetch_company_events_pagination(self, quartr_service, sample_event_dto):
        """Test fetch_company_events with pagination."""
        # Create multiple pages of responses
        first_response = PaginatedEventResponseDto(
            data=[sample_event_dto],
            pagination=CursorPagination(next_cursor=100),
        )
        second_response = PaginatedEventResponseDto(
            data=[sample_event_dto],
            pagination=CursorPagination(next_cursor=None),
        )

        quartr_service.events_requestor.request.side_effect = [
            first_response,
            second_response,
        ]

        events = quartr_service.fetch_company_events(
            ticker="AAPL",
            exchange="NasdaqGS",
            country="US",
            event_ids=[26],
        )

        assert len(events) == 2
        assert quartr_service.events_requestor.request.call_count == 2

        # Check that cursor was updated on second call
        second_call_kwargs = quartr_service.events_requestor.request.call_args_list[
            1
        ].kwargs
        assert second_call_kwargs["cursor"] == 100

    def test_fetch_company_events_max_iteration(self, quartr_service, sample_event_dto):
        """Test fetch_company_events respects max_iteration."""
        # Always return a next_cursor to simulate infinite pagination
        response = PaginatedEventResponseDto(
            data=[sample_event_dto],
            pagination=CursorPagination(next_cursor=100),
        )

        quartr_service.events_requestor.request.return_value = response

        events = quartr_service.fetch_company_events(
            ticker="AAPL",
            exchange="NasdaqGS",
            country="US",
            event_ids=[26],
            max_iteration=3,
        )

        assert len(events) == 3
        assert quartr_service.events_requestor.request.call_count == 3

    def test_fetch_event_documents_success(
        self, quartr_service, paginated_documents_response
    ):
        """Test fetch_event_documents with successful response."""
        quartr_service.documents_requestor.request.return_value = (
            paginated_documents_response
        )

        documents = quartr_service.fetch_event_documents(
            event_ids=[128301],
            document_ids=[7, 15],
        )

        assert len(documents) == 1
        assert documents[0]["id"] == 432907
        assert documents[0]["event_id"] == 128301

        quartr_service.documents_requestor.request.assert_called_once()
        call_kwargs = quartr_service.documents_requestor.request.call_args.kwargs
        assert call_kwargs["event_ids"] == "128301"
        assert call_kwargs["type_ids"] == "7,15"
        assert call_kwargs["limit"] == 500

    def test_fetch_event_documents_pagination(
        self, quartr_service, sample_document_dto
    ):
        """Test fetch_event_documents with pagination."""
        first_response = PaginatedDocumentResponseDto(
            data=[sample_document_dto],
            pagination=CursorPagination(next_cursor=50),
        )
        second_response = PaginatedDocumentResponseDto(
            data=[sample_document_dto],
            pagination=CursorPagination(next_cursor=None),
        )

        quartr_service.documents_requestor.request.side_effect = [
            first_response,
            second_response,
        ]

        documents = quartr_service.fetch_event_documents(
            event_ids=[128301],
            document_ids=[7],
        )

        assert len(documents) == 2
        assert quartr_service.documents_requestor.request.call_count == 2

    def test_fetch_event_documents_max_iteration(
        self, quartr_service, sample_document_dto
    ):
        """Test fetch_event_documents respects max_iteration."""
        response = PaginatedDocumentResponseDto(
            data=[sample_document_dto],
            pagination=CursorPagination(next_cursor=50),
        )

        quartr_service.documents_requestor.request.return_value = response

        documents = quartr_service.fetch_event_documents(
            event_ids=[128301],
            document_ids=[7],
            max_iteration=5,
        )

        assert len(documents) == 5
        assert quartr_service.documents_requestor.request.call_count == 5


class TestConvertIdsToStr:
    """Test cases for _convert_ids_to_str helper function."""

    def test_convert_single_id(self):
        """Test converting a single ID to string."""
        result = _convert_ids_to_str([26])
        assert result == "26"

    def test_convert_multiple_ids(self):
        """Test converting multiple IDs to comma-separated string."""
        result = _convert_ids_to_str([26, 27, 28])
        assert result == "26,27,28"

    def test_convert_empty_list(self):
        """Test converting empty list returns empty string."""
        result = _convert_ids_to_str([])
        assert result == ""
