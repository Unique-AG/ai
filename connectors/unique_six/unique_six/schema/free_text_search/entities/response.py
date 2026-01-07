from enum import StrEnum

from pydantic import Field

from unique_six.schema import (
    BaseAPIModel,
    BaseResponsePayload,
    EntityStatus,
    EntityType,
    Language,
)


class EntityMatchingDescription(StrEnum):
    ENTITY_SHORT_NAME = "ENTITY_SHORT_NAME"
    ENTITY_LONG_NAME = "ENTITY_LONG_NAME"
    LEI = "LEI"
    GK = "GK"
    OTHER = "OTHER"


class FreeTextEntitiesSearchHighlightsItem(BaseAPIModel):
    matching_description: EntityMatchingDescription = Field(
        ...,
        description="A human-readable explanation detailing the alignment between the search term and the content of a particular result.",
    )


class FreeTextEntitiesSearchHit(BaseAPIModel):
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


class FreeTextEntitiesSearchEntitiesItem(BaseAPIModel):
    hit: FreeTextEntitiesSearchHit | None = None
    normalized_score: float = Field(
        ...,
        description="A numerical value ranging from 0 to 1, representing the degree of correlation between the search term and a given result. A perfect match results in a score of 1, offering a standardized measure of relevance.",
    )
    highlights: list[FreeTextEntitiesSearchHighlightsItem] = Field(
        ...,
        description="A list of descriptions outlining the reasons why a particular search term led to a corresponding match. These highlights provide insights into the contextual relevance of the result.",
    )


class FreeTextEntitiesSearchEntitites(BaseAPIModel):
    entities: list[FreeTextEntitiesSearchEntitiesItem] = Field(
        ...,
        description="Search entities by free-text names and by identifiers.",
    )


class FreeTextEntitiesSearch(BaseAPIModel):
    free_text_search: FreeTextEntitiesSearchEntitites | None = None


class FreeTextEntitiesSearchData(BaseAPIModel):
    search: FreeTextEntitiesSearch | None = None


class FreeTextEntitiesSearchResponsePayload(BaseResponsePayload):
    data: FreeTextEntitiesSearchData | None = None
