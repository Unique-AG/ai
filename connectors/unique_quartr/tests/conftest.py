from datetime import datetime
from unittest.mock import Mock

import pytest
from unique_toolkit._common.endpoint_requestor import RequestContext

from unique_quartr.endpoints.schemas import (
    CursorPagination,
    DocumentDto,
    DocumentTypeDto,
    EventDto,
    PaginatedDocumentResponseDto,
    PaginatedDocumentTypeResponseDto,
    PaginatedEventResponseDto,
)


@pytest.fixture
def mock_request_context():
    """Create a mock RequestContext for testing."""
    return RequestContext(
        base_url="https://api.quartr.com",
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": "test_api_key",
        },
    )


@pytest.fixture
def sample_event_dto():
    """Create a sample EventDto for testing."""
    return EventDto(
        company_id=4742,
        date=datetime(2024, 1, 15, 15, 0, 0),
        id=128301,
        title="Q1 2024",
        type_id=26,
        fiscal_year=2024,
        fiscal_period="Q1",
        backlink_url="https://quartr.com/companies/apple",
        updated_at=datetime(2024, 1, 19, 15, 0, 0),
        created_at=datetime(2024, 1, 15, 15, 0, 0),
    )


@pytest.fixture
def sample_document_dto():
    """Create a sample DocumentDto for testing."""
    return DocumentDto(
        company_id=4742,
        event_id=128301,
        file_url="https://quartr.com/file.pdf",
        id=432907,
        type_id=7,
        updated_at=datetime(2024, 1, 19, 15, 0, 0),
        created_at=datetime(2024, 1, 15, 15, 0, 0),
    )


@pytest.fixture
def sample_document_type_dto():
    """Create a sample DocumentTypeDto for testing."""
    return DocumentTypeDto(
        id=7,
        name="Quarterly Report",
        description="General form for quarterly reports under Section 13 or 15(d)",
        form="10-Q",
        updated_at=datetime(2024, 4, 9, 14, 19, 21),
        created_at=datetime(2024, 4, 5, 14, 19, 21),
        category="Report",
        document_group_id=1,
    )


@pytest.fixture
def paginated_events_response(sample_event_dto):
    """Create a paginated events response for testing."""
    return PaginatedEventResponseDto(
        data=[sample_event_dto],
        pagination=CursorPagination(next_cursor=None),
    )


@pytest.fixture
def paginated_documents_response(sample_document_dto):
    """Create a paginated documents response for testing."""
    return PaginatedDocumentResponseDto(
        data=[sample_document_dto],
        pagination=CursorPagination(next_cursor=None),
    )


@pytest.fixture
def paginated_document_types_response(sample_document_type_dto):
    """Create a paginated document types response for testing."""
    return PaginatedDocumentTypeResponseDto(
        data=[sample_document_type_dto],
        pagination=CursorPagination(next_cursor=None),
    )


@pytest.fixture
def mock_events_requestor(paginated_events_response):
    """Create a mock events requestor for testing."""
    mock = Mock()
    mock.request.return_value = paginated_events_response
    return mock


@pytest.fixture
def mock_documents_requestor(paginated_documents_response):
    """Create a mock documents requestor for testing."""
    mock = Mock()
    mock.request.return_value = paginated_documents_response
    return mock


@pytest.fixture
def mock_document_types_requestor(paginated_document_types_response):
    """Create a mock document types requestor for testing."""
    mock = Mock()
    mock.request.return_value = paginated_document_types_response
    return mock
