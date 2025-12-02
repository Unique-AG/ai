from pydantic import BaseModel, Field
from core.schema import camelized_model_config


class GoogleSearchQueryParams(BaseModel):
    """
    Pagination parameters for Google Custom Search API.
    """

    model_config = camelized_model_config

    q: str = Field(..., description="Query string")
    cx: str = Field(
        ...,
        description="The Programmable Search Engine ID to use for this request",
    )
    key: str = Field(..., description="API key for authentication")

    start: int = Field(..., description="The index of the first result to return")
    num: int = Field(..., description="The number of results to return")
