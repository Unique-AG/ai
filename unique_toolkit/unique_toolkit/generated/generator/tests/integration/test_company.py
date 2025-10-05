"""Integration tests for company operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestCompanyOperations:
    """Test company-related operations."""

    def test_company_acronyms__retrieves_acronyms__successfully(self, request_context):
        """
        Purpose: Verify company acronyms retrieval works.
        Why: Acronym expansion is useful for content understanding.
        Setup: Request context only (company-wide resource).
        """
        # Arrange - No specific setup needed

        # Act
        response = unique_SDK.company.acronyms.GetCompanyAcronyms.request(
            context=request_context,
        )

        # Assert
        assert response is not None
        # Response should be a list or dict with acronyms
        if isinstance(response, list):
            # List of acronym objects
            pass  # Valid response
        elif isinstance(response, dict):
            # Dict with acronyms key
            assert "acronyms" in response or "data" in response
