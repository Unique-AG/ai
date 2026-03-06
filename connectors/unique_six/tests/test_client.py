from datetime import date

import pytest
import responses

from unique_six.client import API_URL, SixApiClient, split_cert_chain
from unique_six.exception import SixApiException, raise_errors_from_api_response
from unique_six.schema.common.base.response import BaseResponsePayload, ErrorDetail
from unique_six.schema.common.base.response import ErrorCategory, ErrorCode
from unique_six.schema.end_of_day_history import (
    EndOfDayHistoryRequestParams,
    EndOfDayHistoryResponsePayload,
)
from unique_six.schema import ListingIdentifierScheme


# --- split_cert_chain ---


def test_split_cert_chain_single_cert():
    cert = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----"
    assert split_cert_chain(cert) == [cert]


def test_split_cert_chain_two_certs():
    c1 = "-----BEGIN CERTIFICATE-----\nA\n-----END CERTIFICATE-----"
    c2 = "-----BEGIN CERTIFICATE-----\nB\n-----END CERTIFICATE-----"
    got = split_cert_chain(c1 + "\n" + c2)
    assert len(got) == 2
    assert "-----END CERTIFICATE-----" in got[0] and "-----END CERTIFICATE-----" in got[1]


# --- SixApiException ---


def test_six_api_exception_single_error_str():
    err = ErrorDetail(category=ErrorCategory.VALIDATION_ERROR, code=ErrorCode.PARAMETER_REQUIRED, message="x")
    ex = SixApiException([err])
    assert "PARAMETER_REQUIRED" in str(ex)
    assert "x" in str(ex)


def test_six_api_exception_multiple_errors_str():
    errs = [
        ErrorDetail(category=ErrorCategory.OTHER, code=ErrorCode.OTHER, message="a"),
        ErrorDetail(category=ErrorCategory.OTHER, code=ErrorCode.OTHER, message="b"),
    ]
    ex = SixApiException(errs)
    assert "Errors:" in str(ex)
    assert "a" in str(ex) and "b" in str(ex)


# --- raise_errors_from_api_response ---


def test_raise_errors_from_api_response_no_errors():
    payload = BaseResponsePayload(errors=None)
    raise_errors_from_api_response(payload)


def test_raise_errors_from_api_response_empty_errors():
    payload = BaseResponsePayload(errors=[])
    raise_errors_from_api_response(payload)


def test_raise_errors_from_api_response_raises():
    err = ErrorDetail(category=ErrorCategory.HTTP_ERROR, code=ErrorCode.ACCESS_DENIED, message="denied")
    payload = BaseResponsePayload(errors=[err])
    with pytest.raises(SixApiException) as exc_info:
        raise_errors_from_api_response(payload)
    assert exc_info.value.errors == [err]


# --- SixApiClient (mocked HTTP) ---


@responses.activate
def test_client_request_builds_url_and_parses_json(six_cert_and_key):
    cert, key = six_cert_and_key
    client = SixApiClient(cert, key)
    path = "v1/listings/marketData/endOfDayHistory"
    params = {"scheme": "ISIN_BC", "ids": "X", "dateFrom": "2025-01-01"}
    responses.add(responses.GET, f"{API_URL}{path}", json={"data": {"listings": []}}, status=200)
    out = client.request(path, params)
    assert out == {"data": {"listings": []}}
    assert len(responses.calls) == 1
    assert path in responses.calls[0].request.url


@responses.activate
def test_client_end_of_day_history_returns_typed_response(six_cert_and_key):
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
