import re
import urllib.parse
import urllib.request
from typing import Any, Callable, ParamSpec, TypeVar

import requests

from unique_stock_ticker.clients.six.exception import NoCredentialsException
from unique_stock_ticker.clients.six.http_adapter import InMemoryCertAdapter
from unique_stock_ticker.clients.six.schema import (
    BaseRequestParams,
    BaseResponsePayload,
)
from unique_stock_ticker.clients.six.schema.end_of_day_history import (
    EndOfDayHistoryRequestParams,
    EndOfDayHistoryResponsePayload,
)
from unique_stock_ticker.clients.six.schema.entity_base import (
    EntityBaseByListingRequestParams,
    EntityBaseByListingResponsePayload,
)
from unique_stock_ticker.clients.six.schema.free_text_search import (
    FreeTextEntitiesSearchResponsePayload,
    FreeTextInstrumentsSearchResponsePayload,
    FreeTextMarketsSearchResponsePayload,
    FreeTextSearchEntitiesRequestParams,
    FreeTextSearchInstrumentsRequestParams,
    FreeTextSearchMarketsRequestParams,
)
from unique_stock_ticker.clients.six.schema.intraday_history import (
    IntradayHistorySummaryRequestParams,
    IntradayHistorySummaryResponsePayload,
)
from unique_stock_ticker.clients.six.schema.intraday_snapshot import (
    IntradaySnapshotRequestParams,
    IntradaySnapshotResponsePayload,
)

API_URL = "https://api.six-group.com/web/"


def split_cert_chain(cert: str) -> list[str]:
    return re.findall(".*?-----END CERTIFICATE-----", cert, re.DOTALL)


class SixApiClient:
    def __init__(self, cert: str, key: str) -> None:
        self._session = requests.Session()
        self._session.headers = {"accept": "application/json"}
        self._url = API_URL

        certs = [c.encode("utf-8") for c in split_cert_chain(cert)]
        cert_adapter = InMemoryCertAdapter(
            certs[0],
            key.encode("utf-8"),
            certs[1:],
        )
        self._session.mount(self._url, cert_adapter)

        # Endpoints
        self.end_of_day_history = endpoint(
            self,
            "v1/listings/marketData/endOfDayHistory",
            EndOfDayHistoryRequestParams,
            EndOfDayHistoryResponsePayload,
        )
        self.free_text_search_instruments = endpoint(
            self,
            "v1/search/freeTextSearch/instruments",
            FreeTextSearchInstrumentsRequestParams,
            FreeTextInstrumentsSearchResponsePayload,
        )
        self.free_text_search_entities = endpoint(
            self,
            "v1/search/freeTextSearch/entities",
            FreeTextSearchEntitiesRequestParams,
            FreeTextEntitiesSearchResponsePayload,
        )
        self.free_text_search_markets = endpoint(
            self,
            "v1/search/freeTextSearch/markets",
            FreeTextSearchMarketsRequestParams,
            FreeTextMarketsSearchResponsePayload,
        )
        self.intraday_history_summary = endpoint(
            self,
            "v1/listings/marketData/intradayHistory/summary",
            IntradayHistorySummaryRequestParams,
            IntradayHistorySummaryResponsePayload,
        )
        self.intraday_snapshot = endpoint(
            self,
            "v1/listings/marketData/intradaySnapshot",
            IntradaySnapshotRequestParams,
            IntradaySnapshotResponsePayload,
        )
        self.entity_base_by_listing = endpoint(
            self,
            "v1/listings/referenceData/entityBase",
            EntityBaseByListingRequestParams,
            EntityBaseByListingResponsePayload,
        )

    def request(
        self, end_point: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        complete_url = (
            f"{self._url}{end_point}?{urllib.parse.urlencode(params)}"
        )
        response = self._session.get(complete_url)
        response.raise_for_status()
        return response.json()


ResponseType = TypeVar("ResponseType", bound=BaseResponsePayload)
RequestType = TypeVar("RequestType", bound=BaseRequestParams)
RequestConstructorSpec = ParamSpec("RequestConstructorSpec")


def endpoint(
    client: SixApiClient,
    url: str,
    params: Callable[RequestConstructorSpec, RequestType],
    response_type: type[ResponseType],
) -> Callable[RequestConstructorSpec, ResponseType]:
    def endpoint_f(
        *args: RequestConstructorSpec.args,
        **kwargs: RequestConstructorSpec.kwargs,
    ) -> ResponseType:
        return response_type.model_validate(
            client.request(
                url,
                params(*args, **kwargs).model_dump(
                    exclude_unset=True,
                    by_alias=True,
                    exclude_defaults=True,
                    mode="json",
                ),
            )
        )

    return endpoint_f


def get_six_api_client(company_id: str) -> SixApiClient:
    from unique_stock_ticker.clients.six.settings import six_api_settings

    creds = six_api_settings.creds_for_company(company_id)
    if creds is None:
        raise NoCredentialsException(company_id)
    return SixApiClient(creds.cert, creds.key)
