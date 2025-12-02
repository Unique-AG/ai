class VertexAIException(Exception):
    """Base exception for VertexAI errors."""


class VertexAIClientNotConfiguredException(VertexAIException):
    """Exception raised when the VertexAI client is not configured."""

    def __init__(self, message: str = "VertexAI client is not configured"):
        super().__init__(message)


class VertexAICredentialNotFoundException(VertexAIException):
    """Exception raised when the VertexAI credential is not found."""

    def __init__(
        self, message: str = "VertexAI service account credentials are not set"
    ):
        super().__init__(message)


class VertexAIContentResponseEmptyException(VertexAIException):
    """Exception raised when the VertexAI content response is empty."""

    def __init__(self, message: str = "VertexAI content response is empty"):
        super().__init__(message)
