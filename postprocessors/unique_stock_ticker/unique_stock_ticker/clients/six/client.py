from unique_six.client import SixApiClient

from unique_stock_ticker.clients.six.settings import six_api_settings


class NoCredentialsException(Exception): ...


def get_six_api_client(company_id: str) -> SixApiClient:
    creds = six_api_settings.creds_for_company(company_id)
    if creds is None:
        raise NoCredentialsException(company_id)
    return SixApiClient(creds.cert, creds.key)
