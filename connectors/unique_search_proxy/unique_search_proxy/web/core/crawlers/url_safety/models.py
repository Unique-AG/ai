from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from unique_search_proxy.web.core.crawlers.url_safety.netloc import (
    build_netloc,
    replace_url_host,
)


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
    """Carries validated host/IP values reused when issuing crawl requests."""

    normalized_url: str
    hostname: str
    resolved_ip: str
    used_dns_resolution: bool

    @property
    def request_url(self) -> str:
        if not self.used_dns_resolution and not self.resolved_ip:
            return self.normalized_url
        return replace_url_host(urlsplit(self.normalized_url), host=self.resolved_ip)

    @property
    def host_header(self) -> str | None:
        if not self.used_dns_resolution:
            return None

        return build_netloc(host=self.hostname, port=urlsplit(self.normalized_url).port)

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

        from unique_search_proxy.web.monitoring.metrics import record_crawl_blocked

        for target in blocked_targets:
            record_crawl_blocked(target.category)

        details = "; ".join(
            f"{target.display_target} ({target.reason})" for target in blocked_targets
        )
        super().__init__(f"Blocked crawl target(s) due to URL safety policy: {details}")


def bypass_crawl_target(url: str) -> ResolvedCrawlTarget:
    return ResolvedCrawlTarget(
        normalized_url=url.strip(),
        hostname="",
        resolved_ip="",
        used_dns_resolution=False,
    )
