from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, ClassVar, Literal, Self, TypeAlias
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, StringConstraints, model_validator
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import NoneToDefault

from unique_search_proxy_core.param_policy.derive import derive_request_model
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.param_policy.request_base import SearchRequestBase
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

_DOMAIN = re.compile(
    r"^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def _bare_domains(entries: list[str] | None) -> list[str]:
    """Reduce entries to the bare domains AgentCore accepts (``https://www.snb.ch/`` -> ``www.snb.ch``)."""
    domains: list[str] = []
    for entry in entries or []:
        text = entry.strip().lower()
        if not text:
            continue
        if "://" in text:
            host = urlsplit(text).hostname or ""
        else:
            host = text.split("/")[0]
        try:
            host = host.rstrip(".").encode("idna").decode("ascii")
        except UnicodeError:
            host = ""
        if not _DOMAIN.match(host):
            raise ValueError(f"{entry!r} is not a domain such as `snb.ch`")
        domains.append(host)
    return domains


def _check_published_range(after: datetime | None, before: datetime | None) -> None:
    # astimezone: two values sharing a tzinfo compare without offsets or fold.
    def utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    if after is not None and before is not None and utc(after) > utc(before):
        raise ValueError("publishedAfter must not be later than publishedBefore")


class AwsSearchRequestBase(SearchRequestBase):
    """Request base that applies the AWS domain and date rules after merging."""

    query: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ...,
        min_length=1,
        max_length=AWS_MAX_QUERY_LENGTH,
        description=(
            f"Search query string, 1 to {AWS_MAX_QUERY_LENGTH} characters "
            "after trimming whitespace"
        ),
    )

    @model_validator(mode="after")
    def _aws_rules(self) -> Self:
        fields = type(self).model_fields
        if "include_domains" in fields:
            self.include_domains = _bare_domains(self.include_domains)
            self.exclude_domains = _bare_domains(self.exclude_domains)
        _check_published_range(
            getattr(self, "published_after", None),
            getattr(self, "published_before", None),
        )
        return self


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

    @model_validator(mode="after")
    def _aws_rules(self) -> Self:
        self.include_domains = _bare_domains(self.include_domains)
        self.exclude_domains = _bare_domains(self.exclude_domains)
        _check_published_range(self.published_after.value, self.published_before.value)
        return self

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        return derive_request_model(
            cls,
            base=AwsSearchRequestBase,
            name=cls._request_model_name,
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
