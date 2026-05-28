from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

from unique_web_search.services.crawlers.url_safety.settings import url_safety_settings


def validate_target_cheap(url: str) -> tuple[str, str] | None:
    """Static validation only — no DNS. Returns (category, reason) if blocked, None otherwise."""
    if not url:
        return "empty", "URL is empty"

    parsed_url = urlsplit(url)
    if parsed_url.scheme.lower() not in url_safety_settings.allowed_schemes:
        return "scheme", "URL scheme must be http or https"

    hostname = parsed_url.hostname
    if not hostname:
        return "host", "URL host is missing or malformed"

    normalized_host = hostname.rstrip(".").lower()

    if normalized_host in url_safety_settings.metadata_hosts:
        return "metadata", "Target points to a metadata endpoint"

    if (
        normalized_host in url_safety_settings.localhost_hosts
        or normalized_host.endswith(".localhost")
    ):
        return "localhost", "Target points to a localhost host"

    if normalized_host.endswith(url_safety_settings.service_suffix):
        return "cluster", "Target points to an internal service host"

    if normalized_host.endswith(url_safety_settings.cluster_local_suffix):
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
