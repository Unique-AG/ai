from pydantic import Field

from unique_stock_ticker.clients.six.schema import (
    BaseRequestParams,
    ListingIdentifierScheme,
)
from unique_stock_ticker.clients.six.schema.intraday_snapshot.quality_of_service import (
    QualityOfService,
)


class IntradaySnapshotRequestParams(BaseRequestParams):
    scheme: ListingIdentifierScheme
    ids: str = Field(
        description="Listing Identifier to be provided by client as input parameter. Several identifiers can be requested comma-separated.",
    )
    quality_of_service: QualityOfService | None = None
