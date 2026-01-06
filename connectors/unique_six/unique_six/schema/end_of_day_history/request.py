from datetime import date

from pydantic import Field

from unique_six.schema import (
    BaseRequestParams,
    ListingIdentifierScheme,
    PriceAdjustment,
)


class EndOfDayHistoryRequestParams(BaseRequestParams):
    scheme: ListingIdentifierScheme
    ids: str = Field(
        ...,
        description="Listing Identifier to be provided by client as input parameter. Several identifiers can be requested comma-separated.",
    )
    date_from: date
    date_to: date | None = None
    price_adjustment: PriceAdjustment | None = PriceAdjustment.ADJUSTED
