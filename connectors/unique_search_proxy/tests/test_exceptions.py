from core.google_search.exceptions import (
    GoogleSearchAPIEndpointNotSetException,
    GoogleSearchAPIKeyNotSetException,
    GoogleSearchEngineIDNotSetException,
    GoogleSearchException,
)
from core.vertexai.exceptions import (
    VertexAIClientNotConfiguredException,
    VertexAIContentResponseEmptyException,
    VertexAICredentialNotFoundException,
    VertexAIException,
)


class TestGoogleSearchExceptions:
    def test_base_exception(self):
        exc = GoogleSearchException("test")
        assert str(exc) == "test"

    def test_api_key_not_set(self):
        exc = GoogleSearchAPIKeyNotSetException()
        assert "API key" in str(exc)
        assert isinstance(exc, GoogleSearchException)

    def test_api_endpoint_not_set(self):
        exc = GoogleSearchAPIEndpointNotSetException()
        assert "endpoint" in str(exc)
        assert isinstance(exc, GoogleSearchException)

    def test_engine_id_not_set(self):
        exc = GoogleSearchEngineIDNotSetException()
        assert "Engine ID" in str(exc)
        assert isinstance(exc, GoogleSearchException)

    def test_custom_message(self):
        exc = GoogleSearchAPIKeyNotSetException("custom msg")
        assert str(exc) == "custom msg"


class TestVertexAIExceptions:
    def test_base_exception(self):
        exc = VertexAIException("test")
        assert str(exc) == "test"

    def test_client_not_configured(self):
        exc = VertexAIClientNotConfiguredException()
        assert "not configured" in str(exc)
        assert isinstance(exc, VertexAIException)

    def test_credential_not_found(self):
        exc = VertexAICredentialNotFoundException()
        assert "credentials" in str(exc)
        assert isinstance(exc, VertexAIException)

    def test_content_response_empty(self):
        exc = VertexAIContentResponseEmptyException()
        assert "empty" in str(exc)
        assert isinstance(exc, VertexAIException)

    def test_custom_message(self):
        exc = VertexAIClientNotConfiguredException("custom")
        assert str(exc) == "custom"
