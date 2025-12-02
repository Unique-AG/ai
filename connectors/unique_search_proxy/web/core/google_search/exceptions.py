class GoogleSearchException(Exception):
    """Base exception for Google Search errors."""


class GoogleSearchAPIKeyNotSetException(GoogleSearchException):
    """Exception raised when the Google Search API key is not set."""

    def __init__(self, message: str = "Google Search API key is not set"):
        super().__init__(message)


class GoogleSearchAPIEndpointNotSetException(GoogleSearchException):
    """Exception raised when the Google Search API endpoint is not set."""

    def __init__(self, message: str = "Google Search API endpoint is not set"):
        super().__init__(message)


class GoogleSearchEngineIDNotSetException(GoogleSearchException):
    """Exception raised when the Google Search Engine ID is not set."""

    def __init__(
        self,
        message: str = "Google Search Engine ID is not set. Provide a valid engine ID or set the GOOGLE_SEARCH_ENGINE_ID environment variable or the cx parameter in the GoogleSearchParams",
    ):
        super().__init__(message)
