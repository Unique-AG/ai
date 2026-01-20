"""Exceptions for generation handler operations."""


class GenerationHandlerError(Exception):
    """Base exception for all generation handler errors."""

    pass


class BatchCreationError(GenerationHandlerError):
    """Raised when batch creation fails."""

    def __init__(
        self,
        message: str,
        group_key: str | None = None,
        row_count: int | None = None,
    ):
        super().__init__(message)
        self.group_key = group_key
        self.row_count = row_count


class PromptBuildError(GenerationHandlerError):
    """Raised when prompt building fails."""

    def __init__(
        self,
        message: str,
        prompt_type: str | None = None,
        context: dict | None = None,
    ):
        super().__init__(message)
        self.prompt_type = prompt_type
        self.context = context or {}


class LLMCallError(GenerationHandlerError):
    """Raised when LLM call fails."""

    def __init__(
        self,
        message: str,
        group_key: str | None = None,
        batch_index: int | None = None,
        error_details: str | None = None,
    ):
        super().__init__(message)
        self.group_key = group_key
        self.batch_index = batch_index
        self.error_details = error_details


class AggregationError(GenerationHandlerError):
    """Raised when aggregating batch results fails."""

    def __init__(
        self,
        message: str,
        group_key: str | None = None,
        batch_count: int | None = None,
    ):
        super().__init__(message)
        self.group_key = group_key
        self.batch_count = batch_count


class TokenLimitError(GenerationHandlerError):
    """Raised when token counting or limit validation fails."""

    def __init__(
        self,
        message: str,
        estimated_tokens: int | None = None,
        max_tokens: int | None = None,
    ):
        super().__init__(message)
        self.estimated_tokens = estimated_tokens
        self.max_tokens = max_tokens
