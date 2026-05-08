from __future__ import annotations

import socket
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import SplitResult, urlsplit, urlunsplit

_ALLOWED_SCHEMES = {"http", "https"}
_LOCALHOST_HOSTS = {
    "localhost",
    "localhost.localdomain",
}
_CLUSTER_LOCAL_SUFFIX = ".cluster.local"
_SERVICE_SUFFIX = ".svc"
_METADATA_HOSTS = {
    "100.100.100.200",  # Alibaba Cloud
    "169.254.169.254",  # AWS / GCP / Azure IMDS
    "169.254.170.2",  # AWS ECS task credentials
    "metadata.azure.internal",
    "metadata.google.internal",
}


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

        return _build_netloc(host=self.hostname, port=urlsplit(self.normalized_url).port)

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

        details = "; ".join(
            f"{target.display_target} ({target.reason})"
            for target in self.blocked_targets
        )
        super().__init__(f"Blocked crawl target(s) due to URL safety policy: {details}")


def validate_crawl_urls(urls: list[str]) -> list[str]:
    normalized_urls: list[str] = []
    blocked_targets: list[BlockedCrawlTarget] = []

    for raw_url in urls:
        normalized_url = raw_url.strip()
        validation_error = _validate_crawl_target(normalized_url)
        if validation_error is not None:
            category, reason = validation_error
            blocked_targets.append(
                BlockedCrawlTarget(
                    hostname=_extract_hostname(normalized_url or raw_url),
                    category=category,
                    reason=reason,
                )
            )
            continue

        normalized_urls.append(normalized_url)

    if blocked_targets:
        raise CrawlTargetValidationError(blocked_targets)

    return normalized_urls


def resolve_crawl_target(url: str) -> ResolvedCrawlTarget:
    normalized_url = validate_crawl_urls([url])[0]
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
        resolved_addresses, validation_error = _resolve_and_validate_host(
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


def _validate_crawl_target(url: str) -> tuple[str, str] | None:
    if not url:
        return "empty", "URL is empty"

    parsed_url = urlsplit(url)
    if parsed_url.scheme.lower() not in _ALLOWED_SCHEMES:
        return "scheme", "URL scheme must be http or https"

    hostname = parsed_url.hostname
    if not hostname:
        return "host", "URL host is missing or malformed"

    normalized_host = hostname.rstrip(".").lower()

    if normalized_host in _METADATA_HOSTS:
        return "metadata", "Target points to a metadata endpoint"

    if normalized_host in _LOCALHOST_HOSTS or normalized_host.endswith(".localhost"):
        return "localhost", "Target points to a localhost host"

    if normalized_host.endswith(_SERVICE_SUFFIX):
        return "cluster", "Target points to an internal service host"

    if normalized_host.endswith(_CLUSTER_LOCAL_SUFFIX):
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

    return _validate_resolved_host(normalized_host)


def _extract_hostname(url: str) -> str | None:
    normalized_url = url.strip()
    if not normalized_url:
        return None

    hostname = urlsplit(normalized_url).hostname
    if hostname is None:
        return None

    return hostname.rstrip(".").lower()


def _validate_resolved_host(host: str) -> tuple[str, str] | None:
    _, validation_error = _resolve_and_validate_host(host)
    return validation_error


def _resolve_and_validate_host(
    host: str,
) -> tuple[tuple[str, ...], tuple[str, str] | None]:
    try:
        resolved_addresses = _resolve_host_addresses(host)
    except socket.gaierror:
        return (), (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    return resolved_addresses, _block_reason_for_resolved_addresses(resolved_addresses)


def _resolve_host_addresses(host: str) -> tuple[str, ...]:
    resolved = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
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
