from unittest.mock import Mock, patch

import pytest

from unique_quartr.endpoints.api import (
    QuartrDocumentsApiOperation,
    QuartrDocumentsTypesApiOperation,
    QuartrEventsApiOperation,
    get_quartr_context,
)
from unique_quartr.endpoints.schemas import (
    PublicV3DocumentsGetParametersQuery,
    PublicV3DocumentTypesGetParametersQuery,
    PublicV3EventsGetParametersQuery,
)


class TestGetQuartrContext:
    """Test cases for get_quartr_context function."""

    @patch("unique_quartr.endpoints.api.quartr_settings")
    def test_get_quartr_context_success(self, mock_settings):
        """Test get_quartr_context with valid settings."""
        # Mock the settings
        mock_creds = Mock()
        mock_creds.api_key = "test_api_key_12345"
        mock_settings.quartr_api_creds_model = mock_creds
        mock_settings.quartr_api_activated_companies = ["company1", "company2"]

        # Get context
        context = get_quartr_context(company_id="company1")

        # Verify context
        assert context.base_url == "https://api.quartr.com"
        assert context.headers["Content-Type"] == "application/json"
        assert context.headers["X-Api-Key"] == "test_api_key_12345"

    @patch("unique_quartr.endpoints.api.quartr_settings")
    def test_get_quartr_context_no_credentials(self, mock_settings):
        """Test get_quartr_context raises error when credentials are not set."""
        mock_settings.quartr_api_creds_model = None

        with pytest.raises(ValueError, match="Quartr API credentials are not set"):
            get_quartr_context(company_id="company1")

    @patch("unique_quartr.endpoints.api.quartr_settings")
    def test_get_quartr_context_company_not_activated(self, mock_settings):
        """Test get_quartr_context raises error when company is not activated."""
        mock_creds = Mock()
        mock_creds.api_key = "test_api_key"
        mock_settings.quartr_api_creds_model = mock_creds
        mock_settings.quartr_api_activated_companies = ["company1", "company2"]

        with pytest.raises(ValueError, match="Company company3 is not activated"):
            get_quartr_context(company_id="company3")


class TestQuartrApiOperations:
    """Test cases for Quartr API operations."""

    def test_quartr_events_api_operation_callable(self):
        """Test quartr_events_api_operation is callable."""
        # build_api_operation returns a callable class/type
        assert callable(QuartrEventsApiOperation)

    def test_quartr_documents_api_operation_callable(self):
        """Test quartr_documents_api_operation is callable."""
        assert callable(QuartrDocumentsApiOperation)

    def test_quartr_documents_types_api_operation_callable(self):
        """Test quartr_documents_types_api_operation is callable."""
        assert callable(QuartrDocumentsTypesApiOperation)


class TestApiSchemas:
    """Test cases for API schema models."""

    def test_events_query_parameters_default_values(self):
        """Test PublicV3EventsGetParametersQuery default values."""
        query = PublicV3EventsGetParametersQuery()

        assert query.limit == 10
        assert query.cursor == 0
        assert query.direction is not None  # Has a default

    def test_events_query_parameters_with_values(self):
        """Test PublicV3EventsGetParametersQuery with custom values."""
        query = PublicV3EventsGetParametersQuery(
            countries="US,CA",
            exchanges="NasdaqGS,NYSE",
            tickers="AAPL,AMZN",
            limit=500,
            cursor=100,
            start_date="2024-01-01T00:00:00Z",
            end_date="2024-12-31T23:59:59Z",
            type_ids="26,27,28",
        )

        assert query.countries == "US,CA"
        assert query.exchanges == "NasdaqGS,NYSE"
        assert query.tickers == "AAPL,AMZN"
        assert query.limit == 500
        assert query.cursor == 100
        assert query.start_date == "2024-01-01T00:00:00Z"
        assert query.end_date == "2024-12-31T23:59:59Z"
        assert query.type_ids == "26,27,28"

    def test_documents_query_parameters_with_event_ids(self):
        """Test PublicV3DocumentsGetParametersQuery with event IDs."""
        query = PublicV3DocumentsGetParametersQuery(
            event_ids="128301,128302",
            type_ids="7,15",
            limit=100,
        )

        assert query.event_ids == "128301,128302"
        assert query.type_ids == "7,15"
        assert query.limit == 100

    def test_document_types_query_parameters(self):
        """Test PublicV3DocumentTypesGetParametersQuery."""
        query = PublicV3DocumentTypesGetParametersQuery(
            limit=50,
            cursor=10,
        )

        assert query.limit == 50
        assert query.cursor == 10

    def test_query_parameters_limit_validation(self):
        """Test that limit parameter respects maximum value."""
        # This should work (at limit)
        query = PublicV3EventsGetParametersQuery(limit=500)
        assert query.limit == 500

        # This should fail (above limit)
        with pytest.raises(Exception):  # Pydantic validation error
            PublicV3EventsGetParametersQuery(limit=501)

    def test_query_parameters_cursor_validation(self):
        """Test that cursor parameter respects minimum value."""
        # This should work
        query = PublicV3EventsGetParametersQuery(cursor=0)
        assert query.cursor == 0

        # This should fail (below minimum)
        with pytest.raises(Exception):  # Pydantic validation error
            PublicV3EventsGetParametersQuery(cursor=-1)
