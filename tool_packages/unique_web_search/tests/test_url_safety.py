from __future__ import annotations

import socket

import pytest

import unique_web_search.services.url_safety as url_safety
from unique_web_search.services.url_safety import (
    CrawlTargetValidationError,
    validate_crawl_urls,
)


class TestValidateCrawlUrls:
    @pytest.mark.ai
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
    def test_validate_crawl_urls__returns_normalized_urls__when_targets_are_public_http(
        self,
        urls: list[str],
        expected: list[str],
    ) -> None:
        """
        Purpose: Verify public HTTP(S) crawl targets are accepted and normalized.
        Why this matters: Legitimate crawl requests must continue to work after the SSRF guard lands.
        Setup summary: Pass known-good public URLs and assert whitespace is stripped without changing the target.
        """
        assert validate_crawl_urls(urls) == expected

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("url", "category", "reason_snippet"),
        [
            ("file:///etc/passwd", "scheme", "scheme"),
            ("ftp://example.com/file.txt", "scheme", "scheme"),
            ("https://localhost/internal", "localhost", "localhost"),
            ("https://app.localhost/admin", "localhost", "localhost"),
            ("https://kubernetes/api", "cluster", "single-label"),
            ("https://api.default.svc/health", "cluster", "service"),
            (
                "https://api.default.svc.cluster.local/health",
                "cluster",
                "cluster-local",
            ),
            (
                "https://api.default.pod.cluster.local/health",
                "cluster",
                "cluster-local",
            ),
            ("http://127.0.0.1:8080", "private", "private"),
            ("http://10.0.0.8", "private", "private"),
            ("http://169.254.169.254/latest/meta-data", "metadata", "metadata"),
            ("http://[::1]/", "private", "private"),
            (
                "https://metadata.google.internal/computeMetadata/v1",
                "metadata",
                "metadata",
            ),
        ],
    )
    def test_validate_crawl_urls__raises__when_target_is_unsafe(
        self,
        url: str,
        category: str,
        reason_snippet: str,
    ) -> None:
        """
        Purpose: Verify obviously unsafe crawl targets are rejected deterministically.
        Why this matters: SSRF protection depends on blocking local, private, and metadata endpoints before any fetch occurs.
        Setup summary: Pass one unsafe target at a time and assert the validator raises with a policy-specific reason.
        """
        with pytest.raises(CrawlTargetValidationError) as exc_info:
            validate_crawl_urls([url])

        error = exc_info.value
        blocked_target = error.blocked_targets[0]
        assert blocked_target.url == url
        assert blocked_target.category == category
        assert reason_snippet in blocked_target.reason.lower()

    @pytest.mark.ai
    def test_validate_crawl_urls__reports_all_blocked_targets__when_multiple_urls_are_unsafe(
        self,
    ) -> None:
        """
        Purpose: Verify the validator reports every blocked target in one pass.
        Why this matters: Bulk crawl callers need actionable feedback instead of fixing one unsafe URL at a time.
        Setup summary: Pass multiple unsafe URLs together and assert both are preserved in the structured error details.
        """
        urls = [
            "http://127.0.0.1:8080",
            "https://metadata.google.internal/computeMetadata/v1",
        ]

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            validate_crawl_urls(urls)

        blocked_urls = [target.url for target in exc_info.value.blocked_targets]
        assert blocked_urls == urls

    @pytest.mark.ai
    def test_validate_crawl_urls__raises__when_hostname_resolves_to_private_ip(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify non-literal hostnames are blocked when DNS resolves them to private IPs.
        Why this matters: Internal hosts can be reached by name even when the URL does not embed a private IP directly.
        Setup summary: Patch DNS resolution for a Kubernetes-style short hostname and assert the validator rejects it.
        """

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

        monkeypatch.setattr(url_safety.socket, "getaddrinfo", fake_getaddrinfo)

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            validate_crawl_urls(["https://kubernetes.default/health"])

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.url == "https://kubernetes.default/health"
        assert "resolves" in blocked_target.reason.lower()
