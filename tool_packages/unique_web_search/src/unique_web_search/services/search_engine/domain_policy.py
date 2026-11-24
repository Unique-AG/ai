from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


def _host(host: str) -> str:
    # The crawler drops the DNS root dot, so "evil.com." fetches "evil.com";
    # a leading dot is a TLD rule such as Perplexity's ".gov".
    return host.strip().lower().strip(".")


def _rule(entry: str) -> str:
    host, _, path = entry.strip().partition("/")
    host = _host(host)
    if not host:
        return ""
    path = path.strip("/")
    return f"{host}/{path}" if path else host


def _rule_matches(host: str, path: str, rule: str) -> bool:
    rule_host, _, rule_path = rule.partition("/")
    # Same rule as AWS AgentCore: a domain also covers its subdomains.
    if host != rule_host and not host.endswith(f".{rule_host}"):
        return False
    return not rule_path or path == rule_path or path.startswith(f"{rule_path}/")


def _matches(host: str, path: str, rules: frozenset[str]) -> bool:
    return any(_rule_matches(host, path, rule) for rule in rules)


@dataclass(frozen=True)
class DomainPolicy:
    include: frozenset[str] = frozenset()
    exclude: frozenset[str] = frozenset()

    @classmethod
    def of(
        cls, *, include: Iterable[str] = (), exclude: Iterable[str] = ()
    ) -> DomainPolicy:
        def clean(entries: Iterable[str]) -> frozenset[str]:
            rules = (_rule(entry) for entry in entries)
            return frozenset(rule for rule in rules if rule)

        return cls(include=clean(include), exclude=clean(exclude))

    def allows(self, url: str) -> bool:
        if not self.include and not self.exclude:
            return True
        try:
            host = _host(urlparse(url).hostname or "")
            # The path as the crawler's httpx client sends it: dot segments are
            # resolved, but percent-encoded ones survive decoding as "..".
            path = httpx.URL(url).path
        except (ValueError, httpx.InvalidURL):
            return False
        if {".", ".."} & set(path.split("/")):
            return False
        path = path.strip("/")
        if _matches(host, path, self.exclude):
            return False
        return not self.include or _matches(host, path, self.include)
