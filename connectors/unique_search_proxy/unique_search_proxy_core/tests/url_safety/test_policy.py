from __future__ import annotations

import socket

import pytest

import unique_search_proxy_core.url_safety.dns as url_safety_dns
from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    UrlSafetyService,
)


class TestValidateCrawlUrls:
    @pytest.fixture(autouse=True)
    def _use_fake_public_dns(self, fake_public_dns: None) -> None:
        pass

    @pytest.fixture(autouse=True)
    def _disable_redirects(self, disable_url_safety_redirects: None) -> None:
        pass

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("urls", "expected"),
        [
            (["https://example.com"], ["https://example.com"]),
            (
                [" http://example.com/path?q=1 ", "https://docs.python.org/3/"],
                ["http://example.com/path?q=1", "https://docs.python.org/3/"],
            ),
        ],
    )
    async def test_validate_crawl_urls__returns_normalized_urls__when_targets_are_public_http(
        self,
        urls: list[str],
        expected: list[str],
    ) -> None:
        targets = await UrlSafetyService.validate_batch_urls(urls)
        assert [target.normalized_url for target in targets] == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("url", "expected_hostname", "category", "reason_snippet"),
        [
            ("file:///etc/passwd", None, "scheme", "scheme"),
            ("ftp://example.com/file.txt", "example.com", "scheme", "scheme"),
            ("https://localhost/internal", "localhost", "localhost", "localhost"),
            ("https://app.localhost/admin", "app.localhost", "localhost", "localhost"),
            ("https://kubernetes/api", "kubernetes", "cluster", "single-label"),
            ("https://api.default.svc/health", "api.default.svc", "cluster", "service"),
            (
                "https://api.default.svc.cluster.local/health",
                "api.default.svc.cluster.local",
                "cluster",
                "cluster-local",
            ),
            (
                "https://api.default.pod.cluster.local/health",
                "api.default.pod.cluster.local",
                "cluster",
                "cluster-local",
            ),
            ("http://127.0.0.1:8080", "127.0.0.1", "private", "private"),
            ("http://10.0.0.8", "10.0.0.8", "private", "private"),
            (
                "http://169.254.169.254/latest/meta-data",
                "169.254.169.254",
                "metadata",
                "metadata",
            ),
            ("http://[::1]/", "::1", "private", "private"),
            (
                "https://metadata.google.internal/computeMetadata/v1",
                "metadata.google.internal",
                "metadata",
                "metadata",
            ),
        ],
    )
    async def test_validate_crawl_urls__raises__when_target_is_unsafe(
        self,
        url: str,
        expected_hostname: str | None,
        category: str,
        reason_snippet: str,
    ) -> None:
        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await UrlSafetyService.validate_batch_urls([url])

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.hostname == expected_hostname
        assert blocked_target.category == category
        assert reason_snippet in blocked_target.reason.lower()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_crawl_urls__reports_only_hostname__when_url_contains_credentials_and_query(
        self,
    ) -> None:
        url = "https://alice:secret@localhost/admin?token=top-secret#frag"

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await UrlSafetyService.validate_batch_urls([url])

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.hostname == "localhost"
        assert "localhost" in str(exc_info.value)
        assert "/admin" not in str(exc_info.value)
        assert "token" not in str(exc_info.value)
        assert "secret" not in str(exc_info.value)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_crawl_urls__reports_all_blocked_targets__when_multiple_urls_are_unsafe(
        self,
    ) -> None:
        urls = [
            "http://127.0.0.1:8080",
            "https://metadata.google.internal/computeMetadata/v1",
        ]

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await UrlSafetyService.validate_batch_urls(urls)

        blocked_hostnames = [
            target.hostname for target in exc_info.value.blocked_targets
        ]
        assert blocked_hostnames == ["127.0.0.1", "metadata.google.internal"]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_crawl_urls__raises__when_hostname_resolves_to_private_ip(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("10.96.0.1", 443),
                )
            ]

        monkeypatch.setattr(url_safety_dns.socket, "getaddrinfo", fake_getaddrinfo)

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await UrlSafetyService.validate_batch_urls(
                ["https://kubernetes.default/health"]
            )

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.hostname == "kubernetes.default"
        assert "resolves" in blocked_target.reason.lower()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_crawl_urls__raises__when_hostname_cannot_be_resolved(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
            raise socket.gaierror("resolution failed")

        monkeypatch.setattr(url_safety_dns.socket, "getaddrinfo", fake_getaddrinfo)

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await UrlSafetyService.validate_batch_urls(
                ["https://docs.example.com/path?token=abc"]
            )

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.hostname == "docs.example.com"
        assert blocked_target.category == "dns"
        assert "resolved" in blocked_target.reason.lower()
