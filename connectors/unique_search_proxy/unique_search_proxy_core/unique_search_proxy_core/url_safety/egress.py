from __future__ import annotations

from unique_search_proxy_core.url_safety.models import ResolvedCrawlTarget


def pinned_httpx_get_args(
    target: ResolvedCrawlTarget,
) -> tuple[str, dict[str, str], dict[str, str]]:
    """Build httpx GET url, headers, and extensions for DNS-pinned egress."""
    headers: dict[str, str] = {}
    if target.host_header is not None:
        headers["Host"] = target.host_header

    extensions: dict[str, str] = {}
    if target.sni_hostname is not None:
        extensions["sni_hostname"] = target.sni_hostname

    return target.request_url, headers, extensions


__all__ = ["pinned_httpx_get_args"]
