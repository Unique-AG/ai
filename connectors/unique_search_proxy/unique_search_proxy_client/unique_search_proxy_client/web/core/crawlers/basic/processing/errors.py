class ContentProcessingError(Exception):
    """Raised when a registered processor cannot convert a response body."""


class ContentProcessingTimeoutError(ContentProcessingError):
    """Raised when body processing exceeds the allotted time."""
