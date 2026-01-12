"""Exceptions for DataFrame handler operations."""


class DataFrameHandlerError(Exception):
    """Base exception for all DataFrame handler errors."""

    pass


class DataFrameValidationError(DataFrameHandlerError):
    """Raised when DataFrame validation fails (e.g., missing columns)."""

    def __init__(self, message: str, missing_columns: list[str] | None = None):
        super().__init__(message)
        self.missing_columns = missing_columns or []


class DataFrameGroupingError(DataFrameHandlerError):
    """Raised when DataFrame grouping operation fails."""

    def __init__(self, message: str, grouping_column: str | None = None):
        super().__init__(message)
        self.grouping_column = grouping_column


class DataFrameProcessingError(DataFrameHandlerError):
    """Raised when general DataFrame processing fails."""

    pass
