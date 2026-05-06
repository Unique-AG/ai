import pytest

from unique_search_proxy.web.core.google_search.exceptions import (
    GoogleSearchAPIEndpointNotSetException,
    GoogleSearchAPIKeyNotSetException,
    GoogleSearchEngineIDNotSetException,
    GoogleSearchException,
)
from unique_search_proxy.web.core.vertexai.exceptions import (
    VertexAIClientNotConfiguredException,
    VertexAIContentResponseEmptyException,
    VertexAICredentialNotFoundException,
    VertexAIException,
)


class TestGoogleSearchExceptions:
    @pytest.mark.ai
    def test_base_exception(self):
        """
        Purpose: Verify GoogleSearchException stores and returns its message.
        Why this matters: Base exception message is surfaced in error responses.
        Setup summary: Construct with a message and assert str output.
        """
        exc = GoogleSearchException("test")
        assert str(exc) == "test"

    @pytest.mark.ai
    def test_api_key_not_set(self):
        """
        Purpose: Verify default message mentions the API key.
        Why this matters: Operators need a clear hint about what env var is missing.
        Setup summary: Construct with no args and check the default message.
        """
        exc = GoogleSearchAPIKeyNotSetException()
        assert "API key" in str(exc)
        assert isinstance(exc, GoogleSearchException)

    @pytest.mark.ai
    def test_api_endpoint_not_set(self):
        """
        Purpose: Verify default message mentions the endpoint.
        Why this matters: Operators need a clear hint about what env var is missing.
        Setup summary: Construct with no args and check the default message.
        """
        exc = GoogleSearchAPIEndpointNotSetException()
        assert "endpoint" in str(exc)
        assert isinstance(exc, GoogleSearchException)

    @pytest.mark.ai
    def test_engine_id_not_set(self):
        """
        Purpose: Verify default message mentions the Engine ID.
        Why this matters: Operators need a clear hint about what env var is missing.
        Setup summary: Construct with no args and check the default message.
        """
        exc = GoogleSearchEngineIDNotSetException()
        assert "Engine ID" in str(exc)
        assert isinstance(exc, GoogleSearchException)

    @pytest.mark.ai
    def test_custom_message(self):
        """
        Purpose: Verify a custom message overrides the default.
        Why this matters: Callers may provide context-specific error messages.
        Setup summary: Construct with a custom message and assert it.
        """
        exc = GoogleSearchAPIKeyNotSetException("custom msg")
        assert str(exc) == "custom msg"


class TestVertexAIExceptions:
    @pytest.mark.ai
    def test_base_exception(self):
        """
        Purpose: Verify VertexAIException stores and returns its message.
        Why this matters: Base exception message is surfaced in error responses.
        Setup summary: Construct with a message and assert str output.
        """
        exc = VertexAIException("test")
        assert str(exc) == "test"

    @pytest.mark.ai
    def test_client_not_configured(self):
        """
        Purpose: Verify default message mentions configuration.
        Why this matters: Operators need a clear hint about missing Vertex AI setup.
        Setup summary: Construct with no args and check the default message.
        """
        exc = VertexAIClientNotConfiguredException()
        assert "not configured" in str(exc)
        assert isinstance(exc, VertexAIException)

    @pytest.mark.ai
    def test_credential_not_found(self):
        """
        Purpose: Verify default message mentions credentials.
        Why this matters: Missing credentials are a common deployment failure.
        Setup summary: Construct with no args and check the default message.
        """
        exc = VertexAICredentialNotFoundException()
        assert "credentials" in str(exc)
        assert isinstance(exc, VertexAIException)

    @pytest.mark.ai
    def test_content_response_empty(self):
        """
        Purpose: Verify default message mentions empty response.
        Why this matters: Empty AI responses need distinct handling from errors.
        Setup summary: Construct with no args and check the default message.
        """
        exc = VertexAIContentResponseEmptyException()
        assert "empty" in str(exc)
        assert isinstance(exc, VertexAIException)

    @pytest.mark.ai
    def test_custom_message(self):
        """
        Purpose: Verify a custom message overrides the default.
        Why this matters: Callers may provide context-specific error messages.
        Setup summary: Construct with a custom message and assert it.
        """
        exc = VertexAIClientNotConfiguredException("custom")
        assert str(exc) == "custom"
