"""Exceptions for template handler operations."""


class TemplateHandlerError(Exception):
    """Base exception for all template handler errors."""

    pass


class TemplateParsingError(TemplateHandlerError):
    """Raised when Jinja template parsing fails."""

    def __init__(self, message: str, template_snippet: str | None = None):
        super().__init__(message)
        self.template_snippet = template_snippet


class TemplateStructureError(TemplateHandlerError):
    """Raised when template doesn't have the required structure."""

    def __init__(self, message: str, expected_structure: str | None = None):
        super().__init__(message)
        self.expected_structure = expected_structure


class TemplateRenderingError(TemplateHandlerError):
    """Raised when template rendering fails."""

    def __init__(self, message: str, context_keys: list[str] | None = None):
        super().__init__(message)
        self.context_keys = context_keys or []


class ColumnExtractionError(TemplateHandlerError):
    """Raised when extracting columns from template fails."""

    def __init__(self, message: str, detected_columns: list[str] | None = None):
        super().__init__(message)
        self.detected_columns = detected_columns or []
