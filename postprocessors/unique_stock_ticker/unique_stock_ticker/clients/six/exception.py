from unique_stock_ticker.clients.six.schema.common.base.response import (
    BaseResponsePayload,
    ErrorDetail,
)


def error_to_str(error: ErrorDetail) -> str:
    error_str = f"Error {error.code}: {error.category}"
    if error.message:
        error_str += f": {error.message}"
    return error_str


class SixApiException(Exception):
    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors

    def __str__(self) -> str:
        if len(self.errors) == 1:
            return error_to_str(self.errors[0])
        else:
            return "Errors:\n" + "\n".join(
                [error_to_str(error) for error in self.errors]
            )


def raise_errors_from_api_response(response: BaseResponsePayload) -> None:
    if response.errors is not None and len(response.errors) > 0:
        raise SixApiException(response.errors)


class NoCredentialsException(Exception): ...
