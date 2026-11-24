from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse


def _canonical(domain: str) -> str:
    # The crawler drops the DNS root dot, so "evil.com." fetches "evil.com".
    return domain.strip().lower().rstrip(".")


def _matches(host: str, domains: frozenset[str]) -> bool:
    # Same rule as AWS AgentCore: a domain also covers its subdomains.
    return any(host == d or host.endswith(f".{d}") for d in domains)


@dataclass(frozen=True)
class DomainPolicy:
    include: frozenset[str] = frozenset()
    exclude: frozenset[str] = frozenset()

    @classmethod
    def of(
        cls, *, include: Iterable[str] = (), exclude: Iterable[str] = ()
    ) -> DomainPolicy:
        def clean(domains: Iterable[str]) -> frozenset[str]:
            cleaned = (_canonical(d) for d in domains)
            return frozenset(d for d in cleaned if d)

        return cls(include=clean(include), exclude=clean(exclude))

    def allows(self, url: str) -> bool:
        if not self.include and not self.exclude:
            return True
        try:
            host = _canonical(urlparse(url).hostname or "")
        except ValueError:
            return False
        if _matches(host, self.exclude):
            return False
        return not self.include or _matches(host, self.include)
