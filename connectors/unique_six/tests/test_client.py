from datetime import date

import pytest
import responses

from unique_six.client import API_URL, SixApiClient, split_cert_chain
from unique_six.exception import SixApiException, raise_errors_from_api_response
from unique_six.schema import ListingIdentifierScheme
from unique_six.schema.common.base.response import (
    BaseResponsePayload,
    ErrorCategory,
    ErrorCode,
    ErrorDetail,
)
from unique_six.schema.end_of_day_history import EndOfDayHistoryResponsePayload

# --- split_cert_chain ---


@pytest.mark.ai
def test_split_cert_chain_single_cert():
    """
    Purpose: Verify split_cert_chain returns a single-element list for one certificate.
    Why this matters: Correct chain splitting is required for mTLS authentication with SIX.
    Setup summary: Pass a single PEM cert string and assert a one-element list.
    """
    cert = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----"
    assert split_cert_chain(cert) == [cert]


@pytest.mark.ai
def test_split_cert_chain_two_certs():
    """
    Purpose: Verify split_cert_chain splits a concatenated chain into individual certs.
    Why this matters: mTLS requires each certificate in the chain to be handled separately.
    Setup summary: Concatenate two PEM certs, split, and assert two valid items.
    """
    c1 = "-----BEGIN CERTIFICATE-----\nA\n-----END CERTIFICATE-----"
    c2 = "-----BEGIN CERTIFICATE-----\nB\n-----END CERTIFICATE-----"
    got = split_cert_chain(c1 + "\n" + c2)
    assert len(got) == 2
    assert (
        "-----END CERTIFICATE-----" in got[0] and "-----END CERTIFICATE-----" in got[1]
    )


# --- SixApiException ---


@pytest.mark.ai
def test_six_api_exception_single_error_str():
    """
    Purpose: Verify SixApiException formats a single error into its string representation.
    Why this matters: Error messages are logged and surfaced to operators.
    Setup summary: Construct with one ErrorDetail and assert code and message appear in str.
    """
    err = ErrorDetail(
        category=ErrorCategory.VALIDATION_ERROR,
        code=ErrorCode.PARAMETER_REQUIRED,
        message="x",
    )
    ex = SixApiException([err])
    assert "PARAMETER_REQUIRED" in str(ex)
    assert "x" in str(ex)


@pytest.mark.ai
def test_six_api_exception_multiple_errors_str():
    """
    Purpose: Verify SixApiException formats multiple errors with an "Errors:" prefix.
    Why this matters: Multi-error responses need clear formatting for debugging.
    Setup summary: Construct with two ErrorDetail items and assert both messages appear.
    """
    errs = [
        ErrorDetail(category=ErrorCategory.OTHER, code=ErrorCode.OTHER, message="a"),
        ErrorDetail(category=ErrorCategory.OTHER, code=ErrorCode.OTHER, message="b"),
    ]
    ex = SixApiException(errs)
    assert "Errors:" in str(ex)
    assert "a" in str(ex) and "b" in str(ex)


# --- raise_errors_from_api_response ---


@pytest.mark.ai
def test_raise_errors_from_api_response_no_errors():
    """
    Purpose: Verify no exception is raised when errors is None.
    Why this matters: Normal responses with no errors must pass through cleanly.
    Setup summary: Create a payload with errors=None and call raise_errors_from_api_response.
    """
    payload = BaseResponsePayload(errors=None)
    raise_errors_from_api_response(payload)


@pytest.mark.ai
def test_raise_errors_from_api_response_empty_errors():
    """
    Purpose: Verify no exception is raised when errors is an empty list.
    Why this matters: An empty error list is equivalent to no errors.
    Setup summary: Create a payload with errors=[] and call raise_errors_from_api_response.
    """
    payload = BaseResponsePayload(errors=[])
    raise_errors_from_api_response(payload)


@pytest.mark.ai
def test_raise_errors_from_api_response_raises():
    """
    Purpose: Verify SixApiException is raised when errors are present.
    Why this matters: API errors must be propagated to callers for proper handling.
    Setup summary: Create a payload with one error and assert SixApiException is raised.
    """
    err = ErrorDetail(
        category=ErrorCategory.HTTP_ERROR,
        code=ErrorCode.ACCESS_DENIED,
        message="denied",
    )
    payload = BaseResponsePayload(errors=[err])
    with pytest.raises(SixApiException) as exc_info:
        raise_errors_from_api_response(payload)
    assert exc_info.value.errors == [err]


# --- SixApiClient (mocked HTTP) ---


@pytest.mark.ai
@responses.activate
def test_client_request_builds_url_and_parses_json(six_cert_and_key):
    """
    Purpose: Verify SixApiClient.request builds the correct URL and parses JSON.
    Why this matters: Incorrect URL construction would break all SIX API calls.
    Setup summary: Mock the HTTP response, call request, assert URL and parsed output.
    """
    cert, key = six_cert_and_key
    client = SixApiClient(cert, key)
    path = "v1/listings/marketData/endOfDayHistory"
    params = {"scheme": "ISIN_BC", "ids": "X", "dateFrom": "2025-01-01"}
    responses.add(
        responses.GET, f"{API_URL}{path}", json={"data": {"listings": []}}, status=200
    )
    out = client.request(path, params)
    assert out == {"data": {"listings": []}}
    assert len(responses.calls) == 1
    assert path in responses.calls[0].request.url


@pytest.mark.ai
@responses.activate
def test_client_end_of_day_history_returns_typed_response(six_cert_and_key):
    """
    Purpose: Verify end_of_day_history returns a typed EndOfDayHistoryResponsePayload.
    Why this matters: Typed responses enable downstream code to use field access safely.
    Setup summary: Mock the API response, call end_of_day_history, assert the return type.
    """
    cert, key = six_cert_and_key
    client = SixApiClient(cert, key)
    responses.add(
        responses.GET,
        f"{API_URL}v1/listings/marketData/endOfDayHistory",
        json={"data": {"listings": []}},
        status=200,
    )
    result = client.end_of_day_history(
        scheme=ListingIdentifierScheme.ISIN_BC,
        ids="CH001",
        date_from=date(2025, 1, 1),
    )
    assert isinstance(result, EndOfDayHistoryResponsePayload)
    assert result.data is not None
    assert result.data.listings == []
