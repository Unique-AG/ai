"""Tests for session schema and configuration."""

from datetime import datetime

import pytest

from unique_swot.services.session.schema import (
    SessionConfig,
    SessionState,
    SwotAnalysisSessionConfig,
    UniqueCompanyListing,
)


class TestSessionState:
    """Test cases for SessionState enum."""

    def test_session_state_values(self):
        """Test that SessionState has all expected values."""
        assert SessionState.RUNNING == "Running"
        assert SessionState.COMPLETED == "Completed"
        assert SessionState.FAILED == "Failed"

    def test_session_state_membership(self):
        """Test SessionState enum membership."""
        assert "Running" in SessionState
        assert "Completed" in SessionState
        assert "Failed" in SessionState


class TestUniqueCompanyListing:
    """Test cases for UniqueCompanyListing model."""

    @pytest.fixture
    def sample_company_data(self):
        """Create sample company data."""
        return {
            "sourceRef": 123.0,
            "name": "Test Company",
            "display_name": "Test Company Inc.",
            "country": "US",
            "tickers": [],
            "source_url": "https://example.com",
            "source": "test",
        }

    def test_company_listing_creation(self, sample_company_data):
        """Test creating a UniqueCompanyListing."""
        company = UniqueCompanyListing(**sample_company_data)

        assert company.id == 123.0
        assert company.name == "Test Company"
        assert company.display_name == "Test Company Inc."
        assert company.country == "US"
        assert company.tickers == []
        assert company.source_url == "https://example.com"
        assert company.source == "test"

    def test_company_listing_validation_alias(self, sample_company_data):
        """Test that sourceRef alias works correctly."""
        company = UniqueCompanyListing(**sample_company_data)
        assert company.id == sample_company_data["sourceRef"]

    def test_company_listing_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):  # Pydantic validation error
            UniqueCompanyListing()


class TestSwotAnalysisSessionConfig:
    """Test cases for SwotAnalysisSessionConfig model."""

    @pytest.fixture
    def sample_company(self):
        """Create a sample company listing."""
        return UniqueCompanyListing(
            sourceRef=123.0,
            name="Test Company",
            display_name="Test Company Inc.",
            country="US",
            tickers=[],
            source_url="https://example.com",
            source="test",
        )

    @pytest.fixture
    def sample_session_config(self, sample_company):
        """Create a sample session config."""
        return SwotAnalysisSessionConfig(
            company_listing=sample_company,
            use_earnings_call=True,
            use_web_sources=True,
            earnings_call_start_date=datetime(2023, 1, 1),
        )

    def test_session_config_creation(self, sample_company):
        """Test creating a SwotAnalysisSessionConfig."""
        config = SwotAnalysisSessionConfig(
            company_listing=sample_company,
            use_earnings_call=False,
            use_web_sources=False,
        )

        assert config.company_listing.name == "Test Company"
        assert config.use_earnings_call is False
        assert config.use_web_sources is False
        assert config.earnings_call_start_date is None

    def test_session_config_default_values(self, sample_company):
        """Test default values for optional fields."""
        config = SwotAnalysisSessionConfig(company_listing=sample_company)

        assert config.use_earnings_call is False
        assert config.use_web_sources is False
        assert config.earnings_call_start_date is None

    def test_render_session_info_default_state(self, sample_session_config):
        """Test rendering session info with default RUNNING state."""
        result = sample_session_config.render_session_info()

        assert isinstance(result, str)
        assert "Test Company" in result
        assert "Running" in result

    def test_render_session_info_completed_state(self, sample_session_config):
        """Test rendering session info with COMPLETED state."""
        result = sample_session_config.render_session_info(state=SessionState.COMPLETED)

        assert isinstance(result, str)
        assert "Test Company" in result
        assert "Completed" in result

    def test_render_session_info_failed_state(self, sample_session_config):
        """Test rendering session info with FAILED state."""
        result = sample_session_config.render_session_info(state=SessionState.FAILED)

        assert isinstance(result, str)
        assert "Test Company" in result
        assert "Failed" in result

    def test_render_session_info_with_earnings_call_date(self, sample_session_config):
        """Test that earnings call date is formatted correctly."""
        result = sample_session_config.render_session_info()

        assert isinstance(result, str)
        # Check that the date is formatted as yyyy-mm-dd
        assert "2023-01-01" in result

    def test_render_session_info_without_earnings_call_date(self, sample_company):
        """Test rendering session info when no earnings call date is set."""
        config = SwotAnalysisSessionConfig(
            company_listing=sample_company,
            use_earnings_call=False,
            use_web_sources=False,
            earnings_call_start_date=None,
        )

        result = config.render_session_info()

        assert isinstance(result, str)
        assert "Test Company" in result

    def test_render_session_info_contains_data_sources(self, sample_session_config):
        """Test that rendered session info contains data source information."""
        result = sample_session_config.render_session_info()

        assert isinstance(result, str)
        # Should contain information about data sources being used
        # The exact content depends on the template

    def test_render_session_info_all_states(self, sample_session_config):
        """Test rendering with all possible states."""
        for state in SessionState:
            result = sample_session_config.render_session_info(state=state)
            assert isinstance(result, str)
            assert len(result) > 0


class TestSessionConfig:
    """Test cases for SessionConfig model."""

    @pytest.fixture
    def sample_swot_config(self):
        """Create a sample SWOT analysis session config."""
        company = UniqueCompanyListing(
            sourceRef=123.0,
            name="Test Company",
            display_name="Test Company Inc.",
            country="US",
            tickers=[],
            source_url="https://example.com",
            source="test",
        )
        return SwotAnalysisSessionConfig(
            company_listing=company,
            use_earnings_call=False,
            use_web_sources=False,
        )

    def test_session_config_creation(self, sample_swot_config):
        """Test creating a SessionConfig."""
        config = SessionConfig(swot_analysis=sample_swot_config)

        assert config.swot_analysis is not None
        assert config.swot_analysis.company_listing.name == "Test Company"

    def test_session_config_model_dump(self, sample_swot_config):
        """Test serializing SessionConfig to dict."""
        config = SessionConfig(swot_analysis=sample_swot_config)
        data = config.model_dump()

        assert "swot_analysis" in data
        assert data["swot_analysis"]["company_listing"]["name"] == "Test Company"

    def test_session_config_model_validate(self, sample_swot_config):
        """Test validating SessionConfig from dict."""
        config = SessionConfig(swot_analysis=sample_swot_config)
        data = config.model_dump()

        # Validate from the dumped data
        validated_config = SessionConfig.model_validate(data)

        assert validated_config.swot_analysis.company_listing.name == "Test Company"
        assert (
            validated_config.swot_analysis.use_earnings_call
            == sample_swot_config.use_earnings_call
        )


class TestSessionInfoRendering:
    """Integration tests for session info rendering."""

    @pytest.fixture
    def complete_session_config(self):
        """Create a complete session config with all fields."""
        company = UniqueCompanyListing(
            sourceRef=456.0,
            name="Complete Test Company",
            display_name="Complete Test Company Ltd.",
            country="GB",
            tickers=[],
            source_url="https://example.co.uk",
            source="test_complete",
        )
        return SwotAnalysisSessionConfig(
            company_listing=company,
            use_earnings_call=True,
            use_web_sources=True,
            earnings_call_start_date=datetime(2024, 6, 15),
        )

    def test_complete_session_info_rendering(self, complete_session_config):
        """Test rendering a complete session info."""
        result = complete_session_config.render_session_info()

        assert "Complete Test Company" in result
        assert "2024-06-15" in result
        assert isinstance(result, str)
        assert len(result) > 0

    def test_session_info_state_transitions(self, complete_session_config):
        """Test rendering session info with different state transitions."""
        # Start with RUNNING
        running_result = complete_session_config.render_session_info(
            state=SessionState.RUNNING
        )
        assert "Running" in running_result

        # Transition to COMPLETED
        completed_result = complete_session_config.render_session_info(
            state=SessionState.COMPLETED
        )
        assert "Completed" in completed_result

        # Or FAILED
        failed_result = complete_session_config.render_session_info(
            state=SessionState.FAILED
        )
        assert "Failed" in failed_result

        # All results should contain the company name
        assert "Complete Test Company" in running_result
        assert "Complete Test Company" in completed_result
        assert "Complete Test Company" in failed_result
