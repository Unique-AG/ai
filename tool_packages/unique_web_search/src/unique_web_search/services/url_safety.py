from __future__ import annotations

import socket
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlsplit

# NOTE: Keep this policy aligned with
# `unique_sdk/unique_sdk/api_resources/_web_search.py`.
# The SDK intentionally keeps a local copy so crawl URLs can be rejected before
# making the public API request.
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
    url: str
    category: str
    reason: str


class CrawlTargetValidationError(ValueError):
    def __init__(self, blocked_targets: list[BlockedCrawlTarget]):
        self.blocked_targets = blocked_targets

        details = "; ".join(
            f"{target.url} ({target.reason})" for target in self.blocked_targets
        )
        super().__init__(
            f"Blocked crawl target(s) due to URL safety policy: {details}"
        )


def validate_crawl_urls(urls: list[str]) -> list[str]:
    normalized_urls: list[str] = []
    blocked_targets: list[BlockedCrawlTarget] = []

    for raw_url in urls:
        normalized_url = raw_url.strip()
        validation_error = _validate_crawl_target(normalized_url)
        if validation_error is not None:
            category, reason = validation_error
            blocked_targets.append(
                BlockedCrawlTarget(url=raw_url, category=category, reason=reason)
            )
            continue

        normalized_urls.append(normalized_url)

    if blocked_targets:
        raise CrawlTargetValidationError(blocked_targets)

    return normalized_urls


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


def _validate_resolved_host(host: str) -> tuple[str, str] | None:
    try:
        resolved = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return None

    for _, _, _, _, sockaddr in resolved:
        resolved_ip = ip_address(sockaddr[0])
        if not resolved_ip.is_global:
            return (
                "private",
                "Target host resolves to a private or special-use IP address",
            )

    return None
