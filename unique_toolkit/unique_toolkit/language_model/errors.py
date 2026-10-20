from collections.abc import Mapping
from typing import NoReturn

import unique_sdk


class LanguageModelCallError(unique_sdk.UniqueError):
    """LLM call rejected with node-chat's error contract.

    ``user_message`` is the text the API curated for the user. Display that
    field. ``str(self)`` is the same text, without the SDK's
    ``(Original error)`` suffix.

    Args:
        code (str): ``error.code`` from the API, for example ``content_filter``.
        user_message (str): Text to show the user.
        retryable (bool): Whether the API marked the call safe to retry.
        correlation_id (str | None): Request correlation id, when the API sent one.
        http_status (int | None): HTTP status of the failed call.
    """

    def __init__(
        self,
        *,
        code: str,
        user_message: str,
        retryable: bool,
        correlation_id: str | None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message=user_message, http_status=http_status, code=code)
        self.user_message = user_message
        self.retryable = retryable
        self.correlation_id = correlation_id


def _language_model_call_error_from(
    error: unique_sdk.UniqueError,
) -> LanguageModelCallError | None:
    """Build a ``LanguageModelCallError`` when ``error`` carries the contract.

    Returns None for legacy SDK errors that have no ``code`` or no boolean
    ``params.retryable``. Callers re-raise those unchanged.

    Args:
        error (unique_sdk.UniqueError): Error raised by ``unique_sdk``.

    Returns:
        LanguageModelCallError | None: The converted error, or None.
    """
    if not isinstance(error.code, str) or error.code == "":
        return None
    params = getattr(error, "params", None)
    if not isinstance(params, Mapping):
        return None
    retryable = params.get("retryable")
    if not isinstance(retryable, bool):
        return None
    user_message = error.args[0] if error.args else None
    if not isinstance(user_message, str) or user_message == "":
        return None
    correlation_id = params.get("correlationId")
    if not isinstance(correlation_id, str):
        correlation_id = None
    return LanguageModelCallError(
        code=error.code,
        user_message=user_message,
        retryable=retryable,
        correlation_id=correlation_id,
        http_status=error.http_status,
    )


def _reraise_as_language_model_call_error(error: BaseException) -> NoReturn:
    """Raise ``LanguageModelCallError`` for a contract error, else re-raise ``error``."""
    if isinstance(error, unique_sdk.UniqueError):
        converted = _language_model_call_error_from(error)
        if converted is not None:
            raise converted from error
    raise error
