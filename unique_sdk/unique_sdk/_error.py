from typing import Dict, Optional, Union, cast


class UniqueError(Exception):
    _message: Optional[str]
    http_body: Optional[str]
    http_status: Optional[int]
    json_body: Optional[object]
    headers: Optional[Dict[str, str]]
    code: Optional[str]
    request_id: Optional[str]
    original_error: Optional[Exception | str]

    def __init__(
        self,
        message: Optional[str] = None,
        http_body: Optional[Union[bytes, str]] = None,
        http_status: Optional[int] = None,
        json_body: Optional[object] = None,
        headers: Optional[Dict[str, str]] = None,
        code: Optional[str] = None,
        original_error: Optional[Exception | str] = None,
    ):
        super(UniqueError, self).__init__(message)

        body: Optional[str] = None
        if http_body and hasattr(http_body, "decode"):
            try:
                body = cast(bytes, http_body).decode("utf-8")
            except BaseException:
                body = (
                    "<Could not decode body as utf-8. "
                    "Please report to support@unique.ch>"
                )

        self._message = message
        self.http_body = body
        self.http_status = http_status
        self.json_body = json_body
        self.headers = headers or {}
        self.code = code
        self.request_id = self.headers.get("request-id", None)
        self.original_error = original_error

    def __str__(self):
        msg = self._message or "<empty message>"
        if self.original_error:
            msg += f"\n(Original error) {str(self.original_error)}"
        return msg


class UniqueErrorWithParamsCode(UniqueError):
    def __repr__(self):
        return (
            "%s(message=%r, params=%r, code=%r, http_status=%r, "
            "request_id=%r)"
            % (
                self.__class__.__name__,
                self._message,
                self.params,  # type: ignore
                self.code,
                self.http_status,
                self.request_id,
            )
        )


class APIError(UniqueError):
    pass


class APIConnectionError(UniqueError):
    should_retry: bool

    def __init__(
        self,
        message,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
        code=None,
        should_retry=False,
        original_error=None,
    ):
        super(APIConnectionError, self).__init__(
            message, http_body, http_status, json_body, headers, code, original_error
        )
        self.should_retry = should_retry


class AuthenticationError(UniqueError):
    pass


class PermissionError(UniqueError):
    pass


class InvalidRequestError(UniqueErrorWithParamsCode):
    def __init__(
        self,
        message,
        params,
        code=None,
        http_body=None,
        http_status=None,
        json_body=None,
        headers=None,
        original_error=None,
    ):
        super(InvalidRequestError, self).__init__(
            message, http_body, http_status, json_body, headers, code, original_error
        )
        self.params = params


class SignatureVerificationError(UniqueError):
    def __init__(self, message, sig_header=None, http_body=None):
        super(SignatureVerificationError, self).__init__(message, http_body)
        self.sig_header = sig_header
