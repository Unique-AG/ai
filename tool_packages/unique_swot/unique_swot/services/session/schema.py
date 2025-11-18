from datetime import datetime

from pydantic import BaseModel, Field
from unique_quartr.endpoints.schemas import TickerDto
from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class UniqueCompanyListing(BaseModel):
    model_config = get_configuration_dict()
    id: float = Field(
        ...,
        description="The id of the company",
        validation_alias="sourceRef",
        alias="sourceRef",
    )
    name: str = Field(..., description="The name of the company")
    display_name: str = Field(
        ...,
        description="The display name of the company",
    )
    country: str = Field(..., description="The country of the company")
    tickers: list[TickerDto] = Field(..., description="The tickers of the company")
    source_url: str = Field(..., description="The source URL of the company")
    source: str = Field(..., description="The source of the company")


class SwotAnalysisSessionConfig(BaseModel):
    model_config = get_configuration_dict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    company_listing: UniqueCompanyListing = Field(
        ..., description="The company listing to use for the SWOT analysis"
    )
    use_earnings_call: bool = Field(
        default=False, description="Whether to use earnings calls as a data source"
    )
    use_web_sources: bool = Field(
        default=False, description="Whether to use web sources as a data source"
    )
    earnings_call_start_date: datetime | None = Field(
        default=None, description="The metadata filter to use for the data source"
    )


class SessionConfig(BaseModel):
    model_config = get_configuration_dict()

    swot_analysis: SwotAnalysisSessionConfig
