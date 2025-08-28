from pydantic import Field

from unique_stock_ticker.clients.six.schema import (
    BaseRequestParams,
    ListingIdentifierScheme,
)


class EntityBaseByListingRequestParams(BaseRequestParams):
    scheme: ListingIdentifierScheme
    ids: str = Field(
        ...,
        description="Listing Identifier to be provided by client as input parameter. Several identifiers can be requested comma-separated.",
    )
