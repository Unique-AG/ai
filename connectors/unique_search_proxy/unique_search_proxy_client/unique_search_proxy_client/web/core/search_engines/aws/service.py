from __future__ import annotations

import asyncio
import json
import logging
import re
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlsplit

import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from botocore.exceptions import BotoCoreError, ClientError
from botocore.session import Session, get_session
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    EngineNotConfiguredError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationProxyError,
)
from unique_search_proxy_core.schema import (
    SearchEngineRaw,
    WebSearchResult,
    WebSearchResults,
)
from unique_search_proxy_core.search_engines.aws.schema import (
    AWS_MAX_QUERY_LENGTH,
    AwsSearchRequest,
)
from unique_search_proxy_core.search_engines.base import (
    SearchEngineType,
    get_search_engine_mode,
)

from unique_search_proxy_client.web.core.provider_response import (
    transport_error_raw,
    upstream_error_message,
    upstream_response_raw,
)
from unique_search_proxy_client.web.core.search_engines.service_base import (
    SearchEngineService,
)
from unique_search_proxy_client.web.settings.providers.aws import (
    aws_search_credentials as credentials,
)

_LOGGER = logging.getLogger(__name__)
_PROVIDER_LABEL = "AWS AgentCore Web Search"
_SIGNING_SERVICE = "bedrock-agentcore"
_WEB_SEARCH_ID = "web-search.v1"


# One dedicated thread: a slow STS refresh queues credential lookups here
# instead of holding threads in the shared pool that DNS and crawling use.
_CREDENTIALS_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="aws-credentials"
)
# In-flight credential lookup, shared by all callers on this event loop.
_credentials_lookup: (
    tuple[asyncio.AbstractEventLoop, asyncio.Future[Credentials]] | None
) = None

# Regional (optionally FIPS) AgentCore hosts, and PrivateLink endpoint names.
_AGENTCORE_HOST = re.compile(
    r"^(?:bedrock-agentcore(?:-fips)?\.(?P<regional>[a-z0-9-]+)"
    r"|[a-z0-9-]+\.bedrock-agentcore\.(?P<private>[a-z0-9-]+)\.vpce)\.amazonaws\.com$"
)


@cache
def _aws_session() -> Session:
    # One session per process: it keeps the loaded credentials and refreshes
    # them before expiry, so web identity does not call STS on every search.
    return get_session()


_STS_SETUP_ERROR_CODES = frozenset(
    {
        "AccessDenied",
        "AccessDeniedException",
        "ExpiredToken",
        "ExpiredTokenException",
        "IDPRejectedClaim",
        "InvalidClientTokenId",
        "InvalidIdentityToken",
    }
)
_STS_THROTTLING_ERROR_CODES = frozenset(
    {"Throttling", "ThrottlingException", "TooManyRequestsException"}
)


def _sts_error(exc: ClientError) -> Exception:
    code = exc.response.get("Error", {}).get("Code", "")
    _LOGGER.warning(
        "AWS credential exchange failed: %s", code or "unknown error", exc_info=exc
    )
    if code in _STS_SETUP_ERROR_CODES:
        return EngineNotConfiguredError()
    message = f"AWS credential exchange failed: {code or 'unknown error'}"
    if code in _STS_THROTTLING_ERROR_CODES:
        return RateLimitedError(message)
    return UpstreamError(message)


def resolve_aws_credentials() -> Credentials:
    """Return frozen credentials from the default AWS chain."""
    try:
        resolved = _aws_session().get_credentials()
    except BotoCoreError as exc:
        _LOGGER.warning("AWS credentials are not available", exc_info=exc)
        raise EngineNotConfiguredError() from exc
    except ClientError as exc:
        raise _sts_error(exc) from exc
    if resolved is None:
        raise EngineNotConfiguredError()
    try:
        frozen = resolved.get_frozen_credentials()
    except BotoCoreError as exc:
        _LOGGER.warning("AWS credentials are not available", exc_info=exc)
        raise EngineNotConfiguredError() from exc
    except ClientError as exc:
        raise _sts_error(exc) from exc
    if not frozen.access_key or not frozen.secret_key:
        raise EngineNotConfiguredError()
    return Credentials(frozen.access_key, frozen.secret_key, frozen.token)


def _shared_credentials_lookup() -> asyncio.Future[Credentials]:
    global _credentials_lookup
    loop = asyncio.get_running_loop()
    if (
        _credentials_lookup is None
        or _credentials_lookup[0] is not loop
        or _credentials_lookup[1].done()
    ):
        lookup: Future[Credentials] = _CREDENTIALS_EXECUTOR.submit(
            resolve_aws_credentials
        )
        _credentials_lookup = (loop, asyncio.wrap_future(lookup, loop=loop))
    return _credentials_lookup[1]


async def aws_credentials_within(timeout: float) -> Credentials:
    """Resolve credentials off the event loop, sharing one lookup across callers."""
    # shield: a caller that times out must not cancel the lookup others share,
    # and its cancelled shield detaches from the shared future.
    try:
        return await asyncio.wait_for(
            asyncio.shield(_shared_credentials_lookup()),
            timeout=timeout,
        )
    except TimeoutError as exc:
        raise UpstreamTimeoutError(
            f"AWS credential exchange timed out after {timeout}s",
        ) from exc


class AwsSearchService(SearchEngineService[AwsSearchRequest]):
    """AgentCore InvokeWebSearch, signed with SigV4 and sent through httpx."""

    engine_id = SearchEngineType.AWS.value

    @property
    def mode(self) -> str:
        return get_search_engine_mode(SearchEngineType.AWS).value

    async def search(
        self,
        request: AwsSearchRequest,  # type: ignore[override]
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        query = request.query.strip()
        if not query or len(query) > AWS_MAX_QUERY_LENGTH:
            raise ValidationProxyError(
                f"AWS search query must be 1 to {AWS_MAX_QUERY_LENGTH} characters",
            )

        client = self._http_client
        if client is None:
            raise RuntimeError("HTTP client is required for AWS search")

        url = _invoke_url(credentials.api_endpoint, credentials.region)
        body = _request_body(request, query)
        payload = body.encode()
        aws_credentials = await aws_credentials_within(request.timeout)
        headers = _signed_headers(
            url=url,
            payload=payload,
            region=credentials.region,
            aws_credentials=aws_credentials,
        )

        try:
            response = await client.post(
                url,
                content=payload,
                headers=headers,
                timeout=request.timeout,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"AWS search timed out after {request.timeout}s",
                upstream_raw=transport_error_raw(exc),
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"AWS search request failed: {exc}",
                upstream_raw=transport_error_raw(exc),
            ) from exc

        _raise_for_aws_response(response)
        try:
            page = response.json()
        except ValueError as exc:
            raise UpstreamError(
                "AWS search returned a response that is not JSON",
                upstream_raw=upstream_response_raw(response),
            ) from exc
        if not isinstance(page, dict):
            raise UpstreamError(
                "AWS search returned an unexpected response shape",
                upstream_raw=upstream_response_raw(response),
            )
        curated = WebSearchResults(results=_extract_results(page))
        if not curated.results:
            raise EmptySearchResultsError("AWS search returned no results")
        _LOGGER.info("AWS search returned %s curated results", len(curated))
        return SearchEngineRaw(pages=[page]), curated


def _invoke_url(api_endpoint: str, region: str) -> str:
    # Signed headers carry the session token, so only AgentCore hosts in the
    # signing region may receive them, not e.g. API Gateway on amazonaws.com.
    parts = urlsplit(api_endpoint)
    host = (parts.hostname or "").rstrip(".").lower()
    match = _AGENTCORE_HOST.match(host)
    endpoint_region = match and (match["regional"] or match["private"])
    if (
        parts.scheme != "https"
        or parts.username is not None
        or parts.password is not None
        or endpoint_region != region.strip().lower()
    ):
        _LOGGER.warning(
            "AWS_SEARCH_API_ENDPOINT is not an AgentCore HTTPS endpoint "
            "in AWS_SEARCH_REGION"
        )
        raise EngineNotConfiguredError(
            missing_env_vars=["AWS_SEARCH_API_ENDPOINT", "AWS_SEARCH_REGION"]
        )
    return f"{api_endpoint.rstrip('/')}/web-search/{_WEB_SEARCH_ID}/invoke"


def _request_body(request: AwsSearchRequest, query: str) -> str:  # type: ignore[valid-type]
    payload: dict[str, Any] = {
        "searchQuery": query,
        "maxResults": request.fetch_size,
    }
    filters = _filters(request)
    if filters:
        payload["filters"] = filters
    return json.dumps(payload, separators=(",", ":"))


def _filters(request: AwsSearchRequest) -> dict[str, Any]:  # type: ignore[valid-type]
    filters: dict[str, Any] = {}
    include = _domains(request.include_domains)
    exclude = _domains(request.exclude_domains)
    domain_filter: dict[str, list[str]] = {}
    if include:
        domain_filter["include"] = include
    if exclude:
        domain_filter["exclude"] = exclude
    if domain_filter:
        filters["domainFilter"] = domain_filter

    published: dict[str, str] = {}
    if request.published_after is not None:
        published["publishedAfter"] = _timestamp(request.published_after)
    if request.published_before is not None:
        published["publishedBefore"] = _timestamp(request.published_before)
    if published:
        filters["publishedDateFilter"] = published
    return filters


def _domains(values: list[str] | None) -> list[str]:
    if not values:
        return []
    return [value.strip() for value in values if value and value.strip()]


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _signed_headers(
    *,
    url: str,
    payload: bytes,
    region: str,
    aws_credentials: Credentials,
) -> dict[str, str]:
    aws_request = AWSRequest(
        method="POST",
        url=url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(aws_credentials, _SIGNING_SERVICE, region).add_auth(aws_request)
    return {str(key): str(value) for key, value in aws_request.headers.items()}


def _raise_for_aws_response(response: httpx.Response) -> None:
    if response.is_success:
        return
    raw = upstream_response_raw(response)
    message = upstream_error_message(response, provider_label=_PROVIDER_LABEL)
    if response.status_code in {401, 403}:
        raise EngineNotConfiguredError()
    if response.status_code == 429:
        raise RateLimitedError(message, upstream_raw=raw)
    # AWS answers a request it rejects (ValidationException) with 400; retrying
    # the same request cannot succeed.
    if response.status_code == 400:
        raise ValidationProxyError(message, upstream_raw=raw)
    raise UpstreamError(message, upstream_raw=raw)


def _extract_results(payload: dict[str, Any]) -> list[WebSearchResult]:
    items = payload.get("results")
    if not isinstance(items, list):
        return []
    results: list[WebSearchResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        title = item.get("title")
        text = item.get("text")
        results.append(
            WebSearchResult(
                url=url.strip(),
                title=title.strip() if isinstance(title, str) else "",
                snippet=text if isinstance(text, str) else "",
            ),
        )
    return results
