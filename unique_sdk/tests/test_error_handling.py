from unique_sdk._error import APIConnectionError, UniqueError


def test_unique_error_with_original_error():
    original_exception = ValueError("Value error")
    error = UniqueError("Test error", original_error=original_exception)

    assert error.original_error == original_exception
    assert "(Original error) Value error" in str(error)


def test_api_connection_error_with_original_error():
    original_exception = ConnectionError("Connection failed")
    error = APIConnectionError(
        "API connection error", original_error=original_exception
    )

    assert error.original_error == original_exception
    assert "(Original error) Connection failed" in str(error)
