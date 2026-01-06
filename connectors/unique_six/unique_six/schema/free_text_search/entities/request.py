from unique_six.schema import BaseRequestParams, EntityType


class FreeTextSearchEntitiesRequestParams(BaseRequestParams):
    text: str
    size: int | None = 10
    entity_type: EntityType | None = None
