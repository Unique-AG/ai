"""Server-side ceilings that bound what a single proxy request may consume."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

REQUEST_LIMITS_ENV_PREFIX = "REQUEST_LIMITS_"


@helm_settings(
    title="Request Limits",
    helm_key="requestLimits",
    kind="internal",
    gated=False,
    egress=None,
    env_prefix=REQUEST_LIMITS_ENV_PREFIX,
    sections={
        "crawl": [
            "max_crawl_response_kib",
            "max_urls_per_crawl",
            "max_url_length",
            "max_concurrent_fetches",
            "max_concurrent_crawls",
        ],
        "timeouts": ["max_timeout_seconds"],
    },
)
class RequestLimitsSettings(BaseSettings):
    """Ceilings callers cannot raise, sized against the pod memory limit.

    Byte sizes are in KiB: Helm renders numbers >= 1e6 in scientific notation,
    which pydantic cannot parse back into an int.
    """

    model_config = SettingsConfigDict(
        env_prefix=REQUEST_LIMITS_ENV_PREFIX,
        extra="ignore",
    )

    max_crawl_response_kib: int = Field(
        default=10 * 1024,
        ge=1,
        description=(
            "Combined decoded size, in KiB, of all page bodies one crawl request "
            "may keep. URLs read after the budget is spent fail individually."
        ),
    )

    # Matches the search fetch_size ceiling: the web search tool crawls a whole
    # result page in one request.
    max_urls_per_crawl: int = Field(
        default=100,
        ge=1,
        description=(
            "Maximum number of URLs in one crawl request. Requests with more "
            "are rejected with a 422."
        ),
    )
    max_url_length: int = Field(
        default=2048,
        ge=1,
        description=(
            "Maximum length of each URL, in characters. Requests containing a "
            "longer URL are rejected with a 422."
        ),
    )
    max_concurrent_fetches: int = Field(
        default=10,
        ge=1,
        description=(
            "Ceiling on a basic crawl's maxConcurrentRequests; higher values "
            "are lowered to this."
        ),
    )
    max_concurrent_crawls: int = Field(
        default=2,
        ge=1,
        description=(
            "Crawl requests one worker process runs at once. Requests beyond "
            "this get a 429 instead of queueing."
        ),
    )
    max_timeout_seconds: int = Field(
        default=120,
        ge=1,
        description=(
            "Ceiling on the timeout of crawl and search requests; longer "
            "timeouts are lowered to this."
        ),
    )

    @property
    def max_crawl_response_bytes(self) -> int:
        return self.max_crawl_response_kib * 1024


def get_request_limits_settings() -> RequestLimitsSettings:
    return get_settings(RequestLimitsSettings, env_prefix=REQUEST_LIMITS_ENV_PREFIX)


request_limits_settings: RequestLimitsSettings = get_request_limits_settings()

__all__ = [
    "REQUEST_LIMITS_ENV_PREFIX",
    "RequestLimitsSettings",
    "get_request_limits_settings",
    "request_limits_settings",
]
