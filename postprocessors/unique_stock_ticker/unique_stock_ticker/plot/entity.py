import logging

from unique_stock_ticker.clients.six import SixApiClient, raise_errors_from_api_response
from unique_stock_ticker.clients.six.schema import ListingIdentifierScheme
from unique_stock_ticker.clients.six.schema.entity_base.listing.response import (
    EntityBaseByListingEntityBase,
)

logger = logging.getLogger(__name__)


async def get_entity_info_for_listings(
    client: SixApiClient, scheme: ListingIdentifierScheme, ids: list[str]
) -> list[EntityBaseByListingEntityBase | None]:
    logger.info(f"Getting entity info for listings: {ids}")
    resp = client.entity_base_by_listing(scheme=scheme, ids=",".join(ids))

    raise_errors_from_api_response(resp)

    if resp.data is None or resp.data.listings is None:
        logger.error("No data returned from API")
        return [None] * len(ids)

    entity_base_by_identifier = {}

    for listing in resp.data.listings:
        if (
            listing.reference_data is not None
            and listing.reference_data.entity_base is not None
        ):
            entity_base_by_identifier[listing.requested_id] = (
                listing.reference_data.entity_base
            )

    res = []

    for id in ids:
        if id in entity_base_by_identifier:
            res.append(entity_base_by_identifier[id])
        else:
            logger.warning(f"No data found for listing: {id}")
            res.append(None)

    return res
