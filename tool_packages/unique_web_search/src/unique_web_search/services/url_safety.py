from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit

import httpx

from unique_web_search.metrics import crawl_blocked
from unique_web_search.settings import env_settings

_LOGGER = logging.getLogger(__name__)

_MAX_REDIRECT_HOPS = 10
_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})


def _allowed_schemes() -> frozenset[str]:
    return frozenset(env_settings.url_safety_allowed_schemes)


def _localhost_hosts() -> frozenset[str]:
    return frozenset(env_settings.url_safety_localhost_hosts)


def _metadata_hosts() -> frozenset[str]:
    return frozenset(env_settings.url_safety_metadata_hosts)


def _cluster_local_suffix() -> str:
    return env_settings.url_safety_cluster_local_suffix


def _service_suffix() -> str:
    return env_settings.url_safety_service_suffix


@dataclass(frozen=True)
class BlockedCrawlTarget:
    hostname: str | None
    category: str
    reason: str

    @property
    def display_target(self) -> str:
        return self.hostname or "<unknown-host>"


@dataclass(frozen=True)
class ResolvedCrawlTarget:
    """Carries the validated host/IP values reused when issuing crawl requests."""

    normalized_url: str
    hostname: str
    resolved_ip: str
    used_dns_resolution: bool

    @property
    def request_url(self) -> str:
        return _replace_url_host(urlsplit(self.normalized_url), host=self.resolved_ip)

    @property
    def host_header(self) -> str | None:
        if not self.used_dns_resolution:
            return None

        return _build_netloc(
            host=self.hostname, port=urlsplit(self.normalized_url).port
        )

    @property
    def sni_hostname(self) -> str | None:
        if not self.used_dns_resolution:
            return None

        if urlsplit(self.normalized_url).scheme.lower() != "https":
            return None

        return self.hostname


class CrawlTargetValidationError(ValueError):
    def __init__(self, blocked_targets: list[BlockedCrawlTarget]):
        self.blocked_targets: list[BlockedCrawlTarget] = blocked_targets

        for target in blocked_targets:
            crawl_blocked.labels(reason_category=target.category).inc()

        details = "; ".join(
            f"{target.display_target} ({target.reason})"
            for target in self.blocked_targets
        )
        super().__init__(f"Blocked crawl target(s) due to URL safety policy: {details}")


async def validate_crawl_urls(urls: list[str]) -> list[str]:
    normalized_urls: list[str] = []
    blocked_targets: list[BlockedCrawlTarget] = []

    for raw_url in urls:
        normalized_url = raw_url.strip()
        validation_error = _validate_crawl_target_cheap(normalized_url)
        if validation_error is not None:
            category, reason = validation_error
            blocked_targets.append(
                BlockedCrawlTarget(
                    hostname=_extract_hostname(normalized_url or raw_url),
                    category=category,
                    reason=reason,
                )
            )
        else:
            normalized_urls.append(normalized_url)

    if blocked_targets:
        raise CrawlTargetValidationError(blocked_targets)

    # Validate hostnames via DNS concurrently to avoid blocking the event loop
    urls_needing_dns = [
        (url, h)
        for url in normalized_urls
        if (h := _hostname_requiring_dns(url)) is not None
    ]
    if urls_needing_dns:
        dns_results = await asyncio.gather(
            *[_validate_resolved_host(h) for _, h in urls_needing_dns]
        )
        dns_blocked = [
            BlockedCrawlTarget(
                hostname=_extract_hostname(url),
                category=category,
                reason=reason,
            )
            for (url, _), dns_error in zip(urls_needing_dns, dns_results)
            if dns_error is not None
            for category, reason in [dns_error]
        ]
        if dns_blocked:
            raise CrawlTargetValidationError(dns_blocked)

    return normalized_urls


async def resolve_crawl_target(url: str) -> ResolvedCrawlTarget:
    """Validate and resolve a single URL, performing DNS exactly once."""
    normalized_url = url.strip()

    validation_error = _validate_crawl_target_cheap(normalized_url)
    if validation_error is not None:
        category, reason = validation_error
        raise CrawlTargetValidationError(
            [
                BlockedCrawlTarget(
                    hostname=_extract_hostname(normalized_url),
                    category=category,
                    reason=reason,
                )
            ]
        )

    parsed_url = urlsplit(normalized_url)
    hostname = parsed_url.hostname
    if hostname is None:
        raise CrawlTargetValidationError(
            [
                BlockedCrawlTarget(
                    hostname=None,
                    category="host",
                    reason="URL host is missing or malformed",
                )
            ]
        )

    normalized_host = hostname.rstrip(".").lower()

    try:
        target_ip = ip_address(normalized_host)
    except ValueError:
        resolved_addresses, validation_error = await _resolve_and_validate_host(
            normalized_host
        )
        if validation_error is not None:
            category, reason = validation_error
            raise CrawlTargetValidationError(
                [
                    BlockedCrawlTarget(
                        hostname=normalized_host,
                        category=category,
                        reason=reason,
                    )
                ]
            )
        return ResolvedCrawlTarget(
            normalized_url=normalized_url,
            hostname=normalized_host,
            resolved_ip=resolved_addresses[0],
            used_dns_resolution=True,
        )

    return ResolvedCrawlTarget(
        normalized_url=normalized_url,
        hostname=normalized_host,
        resolved_ip=str(target_ip),
        used_dns_resolution=False,
    )


def _validate_crawl_target_cheap(url: str) -> tuple[str, str] | None:
    """Static validation only — no DNS. Returns (category, reason) if blocked, None otherwise."""
    if not url:
        return "empty", "URL is empty"

    parsed_url = urlsplit(url)
    if parsed_url.scheme.lower() not in _allowed_schemes():
        return "scheme", "URL scheme must be http or https"

    hostname = parsed_url.hostname
    if not hostname:
        return "host", "URL host is missing or malformed"

    normalized_host = hostname.rstrip(".").lower()

    if normalized_host in _metadata_hosts():
        return "metadata", "Target points to a metadata endpoint"

    if normalized_host in _localhost_hosts() or normalized_host.endswith(".localhost"):
        return "localhost", "Target points to a localhost host"

    if normalized_host.endswith(_service_suffix()):
        return "cluster", "Target points to an internal service host"

    if normalized_host.endswith(_cluster_local_suffix()):
        return "cluster", "Target points to an internal cluster-local host"

    try:
        target_ip = ip_address(normalized_host)
    except ValueError:
        pass
    else:
        if not target_ip.is_global:
            return "private", "Target points to a private or special-use IP address"

        return None

    if "." not in normalized_host:
        return "cluster", "Target points to a single-label internal host"

    return None


async def _validate_crawl_target(url: str) -> tuple[str, str] | None:
    """Full validation including async DNS check."""
    error = _validate_crawl_target_cheap(url)
    if error is not None:
        return error

    hostname = urlsplit(url).hostname
    if hostname is None:
        return None

    normalized_host = hostname.rstrip(".").lower()
    try:
        ip_address(normalized_host)
        return None
    except ValueError:
        pass

    return await _validate_resolved_host(normalized_host)


def _hostname_requiring_dns(url: str) -> str | None:
    """Return the normalized hostname if DNS validation is needed, None otherwise."""
    hostname = urlsplit(url).hostname
    if hostname is None:
        return None
    normalized_host = hostname.rstrip(".").lower()
    try:
        ip_address(normalized_host)
        return None
    except ValueError:
        return normalized_host


def _extract_hostname(url: str) -> str | None:
    normalized_url = url.strip()
    if not normalized_url:
        return None

    hostname = urlsplit(normalized_url).hostname
    if hostname is None:
        return None

    return hostname.rstrip(".").lower()


async def _validate_resolved_host(host: str) -> tuple[str, str] | None:
    _, validation_error = await _resolve_and_validate_host(host)
    return validation_error


async def _resolve_and_validate_host(
    host: str,
) -> tuple[tuple[str, ...], tuple[str, str] | None]:
    try:
        resolved_addresses = await _resolve_host_addresses(host)
    except socket.gaierror:
        return (), (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    return resolved_addresses, _block_reason_for_resolved_addresses(resolved_addresses)


async def _resolve_host_addresses(host: str) -> tuple[str, ...]:
    loop = asyncio.get_running_loop()
    resolved = await loop.run_in_executor(
        None, lambda: socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    )
    return tuple(
        dict.fromkeys(str(ip_address(sockaddr[0])) for _, _, _, _, sockaddr in resolved)
    )


def _block_reason_for_resolved_addresses(
    resolved_addresses: tuple[str, ...],
) -> tuple[str, str] | None:
    if not resolved_addresses:
        return (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    for resolved_address in resolved_addresses:
        if not ip_address(resolved_address).is_global:
            return (
                "private",
                "Target host resolves to a private or special-use IP address",
            )

    return None


def _replace_url_host(parsed_url: SplitResult, *, host: str) -> str:
    netloc = _build_netloc(
        host=host,
        port=parsed_url.port,
        username=parsed_url.username,
        password=parsed_url.password,
    )
    return urlunsplit(
        (
            parsed_url.scheme,
            netloc,
            parsed_url.path,
            parsed_url.query,
            "",
        )
    )


def _build_netloc(
    host: str,
    port: int | None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    credential_prefix = ""
    if username is not None:
        credential_prefix = username
        if password is not None:
            credential_prefix = f"{credential_prefix}:{password}"
        credential_prefix = f"{credential_prefix}@"

    try:
        host_ip = ip_address(host)
    except ValueError:
        normalized_host = host
    else:
        normalized_host = (
            f"[{host_ip.compressed}]" if host_ip.version == 6 else host_ip.compressed
        )

    if port is None:
        return f"{credential_prefix}{normalized_host}"

    return f"{credential_prefix}{normalized_host}:{port}"


async def resolve_redirect_chain(
    url: str,
    *,
    max_hops: int = _MAX_REDIRECT_HOPS,
    timeout: float = 10.0,
) -> str:
    """Follow HTTP 3xx redirects hop-by-hop, validating each destination
    against url_safety rules before issuing the next request.

    Returns the final validated URL.
    Raises CrawlTargetValidationError if any hop is blocked.
    """
    current = url
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        for _ in range(max_hops):
            error = await _validate_crawl_target(current)
            if error is not None:
                category, reason = error
                raise CrawlTargetValidationError(
                    [
                        BlockedCrawlTarget(
                            hostname=_extract_hostname(current),
                            category=category,
                            reason=reason,
                        )
                    ]
                )

            try:
                resp = await client.head(current)
            except Exception as exc:
                _LOGGER.debug(
                    "Redirect resolution stopped at %s due to network error: %s",
                    current,
                    exc,
                )
                break

            if resp.status_code not in _REDIRECT_STATUS_CODES:
                break

            location = resp.headers.get("location")
            if not location:
                break

            current = urljoin(current, location)

    error = await _validate_crawl_target(current)
    if error is not None:
        category, reason = error
        raise CrawlTargetValidationError(
            [
                BlockedCrawlTarget(
                    hostname=_extract_hostname(current),
                    category=category,
                    reason=reason,
                )
            ]
        )

    return current
