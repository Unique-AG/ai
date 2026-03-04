from unique_six import SixApiClient, SixApiException, raise_errors_from_api_response

from unique_stock_ticker.clients.six.exception import NoCredentialsException


def get_six_api_client(company_id: str) -> SixApiClient:
    from unique_stock_ticker.clients.six.settings import six_api_settings

    creds = six_api_settings.creds_for_company(company_id)
    if creds is None:
        raise NoCredentialsException(company_id)
    return SixApiClient(creds.cert, creds.key)


__all__ = [
    "SixApiClient",
    "get_six_api_client",
    "SixApiException",
    "raise_errors_from_api_response",
    "NoCredentialsException",
]
