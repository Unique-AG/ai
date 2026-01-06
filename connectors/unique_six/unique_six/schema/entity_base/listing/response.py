from pydantic import Field

from unique_six.schema import (
    BaseAPIModel,
    BaseResponsePayload,
    EntityStatus,
    EntityType,
    Language,
    ListingIdentifierScheme,
    ListingStatus,
    LookupStatus,
)


class EntityBaseByListingEntityBase(BaseAPIModel):
    entity_short_name: str | None = Field(
        default=None, description="Legal entity short name."
    )
    entity_long_name: str | None = Field(
        default=None, description="Legal entity long name."
    )
    gk: int = Field(
        ...,
        description="The SIX Financial Information identifier (GK) of the legal entity.",
    )
    lei: str | None = Field(
        default=None,
        description="The Legal Entity Identifier (LEI) is a 20-digit alphanumeric code to identify a legal entity. The structure is defined in ISO 17442.",
    )
    entity_type: EntityType | None = Field(
        default=None,
        description="Legal entity classification allocated by SIX Financial Information. Present on all legal entities in the SIX Financial Information database.",
    )
    entity_status: EntityStatus | None = Field(
        default=None,
        description='Status indicating whether the legal entity is inactive (deleted) or active. In case of active legal entities the status may include whether it is "In Liquidation" or "In Foundation".',
    )
    language: Language | None = Field(
        default=None,
        description="Name of the legal entity in the main language as ISO 639 alpha-2 code.",
    )
    entity_location: str | None = Field(
        default=None,
        description="The location (e.g. city or town) of the legal entity.",
    )
    entity_country: str | None = Field(
        default=None,
        description="Country of the legal entity as ISO 3166 alpha-2 code.",
    )


class EntityBaseByListingLookup(BaseAPIModel):
    listing_short_name: str = Field(
        ..., description="Listing short name with up to 19 characters."
    )
    market_short_name: str = Field(
        ...,
        description="The market short name where the instrument is listed with up to 19 characters.",
    )
    listing_currency: str = Field(
        ...,
        description="The trading currency, as specified by SIX, typically follows the ISO 4217 alpha-3 code. This is shown in the main currency and not in fractional units. For cryptocurrencies, the Cryptocurrency Symbol in Instrument Symbology can be used for reference.",
    )
    listing_status: ListingStatus = Field(
        ...,
        description="This shows the instruments status on the market - it shows if it is listed, suspended, admited to trading, delisted, etc",
    )


class EntityBaseByListingReferenceData(BaseAPIModel):
    entity_base: EntityBaseByListingEntityBase | None = None


class EntityBaseByListingItem(BaseAPIModel):
    requested_id: str = Field(
        ..., description="The requested entity id used in the request"
    )
    requested_scheme: ListingIdentifierScheme = Field(
        ..., description="The requested scheme used in the request"
    )
    lookup_status: LookupStatus = Field(..., description="Status of the response")
    lookup: EntityBaseByListingLookup | None = None
    reference_data: EntityBaseByListingReferenceData | None = None


class EntityBaseByListingData(BaseAPIModel):
    listings: list[EntityBaseByListingItem] | None = None


class EntityBaseByListingResponsePayload(BaseResponsePayload):
    data: EntityBaseByListingData | None = None
