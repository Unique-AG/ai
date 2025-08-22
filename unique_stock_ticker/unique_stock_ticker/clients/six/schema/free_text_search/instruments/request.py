from unique_stock_ticker.clients.six.schema import (
    BaseRequestParams,
    InstrumentType,
)


class FreeTextSearchInstrumentsRequestParams(BaseRequestParams):
    text: str
    size: int | None = 10
    instrument_type: InstrumentType | None = None
