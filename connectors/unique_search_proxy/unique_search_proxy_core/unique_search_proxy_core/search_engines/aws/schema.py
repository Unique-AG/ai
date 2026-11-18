from __future__ import annotations

from datetime import datetime
from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import NoneToDefault

from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.schema import DeactivatedNone
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)

AWS_MAX_RESULTS = 25
AWS_MAX_QUERY_LENGTH = 200
AWS_MAX_DOMAINS = 100

DateTimeOrNone: TypeAlias = datetime | DeactivatedNone
ExposableDateTime = ExposableParam[DateTimeOrNone]


class AwsConfig(BaseSearchEngineConfig[Literal[SearchEngineType.AWS]]):
    """AWS AgentCore InvokeWebSearch deployment config."""

    _request_model_name: ClassVar[str] = "AwsSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "AwsExposedParams"

    engine: Annotated[
        Literal[SearchEngineType.AWS], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=SearchEngineType.AWS,
        title="Search engine",
        description="Provider discriminator; must be `aws` for this config.",
    )
    fetch_size: int = Field(
        default=10,
        ge=1,
        le=AWS_MAX_RESULTS,
        description=(
            "Default result count sent as InvokeWebSearch maxResults. "
            f"AWS accepts 1 to {AWS_MAX_RESULTS}."
        ),
    )
    include_domains: Annotated[list[str], NoneToDefault] = Field(
        default_factory=list,
        max_length=AWS_MAX_DOMAINS,
        title="Include domains",
        description=(
            "Only search and read these domains. A domain covers its subdomains: "
            f"`snb.ch` also matches `www.snb.ch`. Up to {AWS_MAX_DOMAINS}."
        ),
        json_schema_extra={"type": ["array", "null"]},
    )
    exclude_domains: Annotated[list[str], NoneToDefault] = Field(
        default_factory=list,
        max_length=AWS_MAX_DOMAINS,
        title="Exclude domains",
        description=(
            "Never search or read these domains. A domain covers its subdomains: "
            f"`wikipedia.org` also blocks `en.wikipedia.org`. Up to {AWS_MAX_DOMAINS}."
        ),
        json_schema_extra={"type": ["array", "null"]},
    )
    published_after: ExposableDateTime = Field(
        default=ExposableDateTime(expose=True, value=None),
        title="Published after",
        description=(
            "Keep pages AWS dates at or after this time. AWS dates a page by when "
            "it last changed, so an older document on an updated page still "
            "passes. Exposed to the model so it can narrow the range per query."
        ),
    )
    published_before: ExposableDateTime = Field(
        default=ExposableDateTime(expose=True, value=None),
        title="Published before",
        description=(
            "Keep pages AWS dates at or before this time. AWS dates a page by "
            "when it last changed, not by the date in the document. Exposed to "
            "the model so it can narrow the range per query."
        ),
    )


AwsSearchRequest = AwsConfig.request_model()


__all__ = [
    "AWS_MAX_DOMAINS",
    "AWS_MAX_QUERY_LENGTH",
    "AWS_MAX_RESULTS",
    "AwsConfig",
    "AwsSearchRequest",
    "ExposableDateTime",
]
