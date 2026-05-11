from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import unique_web_search.services.url_safety as url_safety
from unique_web_search.services.url_safety import (
    CrawlTargetValidationError,
    resolve_crawl_target,
    resolve_redirect_chain,
    validate_crawl_urls,
)


class TestValidateCrawlUrls:
    @pytest.fixture(autouse=True)
    def stable_public_dns_for_tests(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Return a deterministic public IP for dotted hostnames in these tests."""

        def fake_getaddrinfo(host: str, *args: object, **kwargs: object) -> list[tuple]:
            normalized_host = str(host).rstrip(".").lower()
            if "." not in normalized_host:
                raise socket.gaierror("single-label host not resolved in tests")

            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", 443),
                )
            ]

        monkeypatch.setattr(url_safety.socket, "getaddrinfo", fake_getaddrinfo)

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
        """
        Purpose: Verify public HTTP(S) crawl targets are accepted and normalized.
        Why this matters: Legitimate crawl requests must continue to work after the SSRF guard lands.
        Setup summary: Pass known-good public URLs and assert whitespace is stripped without changing the target.
        """
        assert await validate_crawl_urls(urls) == expected

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
        """
        Purpose: Verify obviously unsafe crawl targets are rejected deterministically.
        Why this matters: SSRF protection depends on blocking local, private, and metadata endpoints before any fetch occurs.
        Setup summary: Pass one unsafe target at a time and assert the validator raises with a policy-specific reason.
        """
        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await validate_crawl_urls([url])

        error = exc_info.value
        blocked_target = error.blocked_targets[0]
        assert blocked_target.hostname == expected_hostname
        assert blocked_target.category == category
        assert reason_snippet in blocked_target.reason.lower()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_crawl_urls__reports_only_hostname__when_url_contains_credentials_and_query(
        self,
    ) -> None:
        """
        Purpose: Verify blocked target details keep only the hostname for rejected targets.
        Why this matters: Security logs and surfaced errors must avoid leaking credentials, query params, or paths from rejected URLs.
        Setup summary: Reject a localhost URL that includes userinfo and secrets, then assert the structured error keeps only the hostname.
        """
        url = "https://alice:secret@localhost/admin?token=top-secret#frag"

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await validate_crawl_urls([url])

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
            await validate_crawl_urls(urls)

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
            await validate_crawl_urls(["https://kubernetes.default/health"])

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.hostname == "kubernetes.default"
        assert "resolves" in blocked_target.reason.lower()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_crawl_urls__raises__when_hostname_cannot_be_resolved(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Purpose: Verify unresolved hostnames fail closed during crawl safety validation.
        Why this matters: Treating DNS lookup failures as safe leaves a gap that attackers can exploit with rebinding or transient resolution tricks.
        Setup summary: Patch DNS resolution to fail for a public-looking hostname and assert the validator blocks the target with a DNS-specific reason.
        """

        def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple]:
            raise socket.gaierror("resolution failed")

        monkeypatch.setattr(url_safety.socket, "getaddrinfo", fake_getaddrinfo)

        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await validate_crawl_urls(["https://docs.example.com/path?token=abc"])

        blocked_target = exc_info.value.blocked_targets[0]
        assert blocked_target.hostname == "docs.example.com"
        assert blocked_target.category == "dns"
        assert "resolved" in blocked_target.reason.lower()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_crawl_target__returns_request_values__for_dns_resolved_https_target(
        self,
    ) -> None:
        """
        Purpose: Verify the resolved target object carries the request-time values needed by crawlers.
        Why this matters: Request construction should reuse the security-validated host, IP, and SNI details instead of rebuilding them in each crawler.
        Setup summary: Resolve a public HTTPS hostname under the deterministic DNS fixture and assert the derived request URL and headers are exposed.
        """
        resolved_target = await resolve_crawl_target("https://example.com/docs?q=1")

        assert resolved_target.normalized_url == "https://example.com/docs?q=1"
        assert resolved_target.request_url == "https://93.184.216.34/docs?q=1"
        assert resolved_target.host_header == "example.com"
        assert resolved_target.sni_hostname == "example.com"


class TestResolveRedirectChain:
    """Test cases for resolve_redirect_chain()."""

    @pytest.fixture(autouse=True)
    def stable_public_dns_for_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Return a deterministic public IP for dotted hostnames in these tests."""

        def fake_getaddrinfo(host: str, *args: object, **kwargs: object) -> list[tuple]:
            normalized_host = str(host).rstrip(".").lower()
            if "." not in normalized_host:
                raise socket.gaierror("single-label host not resolved in tests")
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", 443),
                )
            ]

        monkeypatch.setattr(url_safety.socket, "getaddrinfo", fake_getaddrinfo)

    def _make_mock_client(self, responses: list[tuple[int, str | None]]) -> AsyncMock:
        """Build a mock AsyncClient that returns the given (status_code, location) sequence."""
        mock_responses = []
        for status_code, location in responses:
            resp = MagicMock()
            resp.status_code = status_code
            resp.headers = {"location": location} if location else {}
            mock_responses.append(resp)

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=mock_responses)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__no_redirect__returns_original_url(
        self,
    ) -> None:
        """
        Purpose: Verify a URL with no redirect is returned unchanged.
        Why this matters: Non-redirecting pages must pass through without modification.
        Setup summary: Mock HEAD to return 200; assert the original URL is returned.
        """
        mock_client = self._make_mock_client([(200, None)])

        with patch(
            "unique_web_search.services.url_safety.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await resolve_redirect_chain("https://example.com/page")

        assert result == "https://example.com/page"
        mock_client.head.assert_called_once_with("https://example.com/page")

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__safe_http_to_https__returns_final_https_url(
        self,
    ) -> None:
        """
        Purpose: Verify a legitimate http→https redirect is followed and the final URL returned.
        Why this matters: Canonical redirects on public sites must not be treated as unsafe.
        Setup summary: Mock HEAD to return 301→https, then 200; assert the https URL is returned.
        """
        mock_client = self._make_mock_client(
            [
                (301, "https://example.com/page"),
                (200, None),
            ]
        )

        with patch(
            "unique_web_search.services.url_safety.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await resolve_redirect_chain("http://example.com/page")

        assert result == "https://example.com/page"
        assert mock_client.head.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__blocked_redirect__raises_before_head_to_blocked_host(
        self,
    ) -> None:
        """
        Purpose: Verify a redirect to an internal cluster-service host raises before contacting it.
        Why this matters: The whole point of pre-resolution is that the blocked address is never reached.
        Setup summary: Mock first HEAD to redirect to a .svc host; assert error is raised and only
        one HEAD (to the original host, not the redirect target) was issued.
        """
        mock_client = self._make_mock_client(
            [(302, "http://api.default.svc/loki/api/v1/query_range")]
        )

        with patch(
            "unique_web_search.services.url_safety.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with pytest.raises(CrawlTargetValidationError) as exc_info:
                await resolve_redirect_chain("https://evil.example.com/article")

        blocked = exc_info.value.blocked_targets[0]
        assert blocked.hostname == "api.default.svc"
        assert blocked.category == "cluster"
        # Only one HEAD request issued — to evil.example.com, never to the blocked host
        assert mock_client.head.call_count == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__network_error_on_hop__stops_and_returns_last_valid_url(
        self,
    ) -> None:
        """
        Purpose: Verify a network error during resolution stops gracefully at the last validated URL.
        Why this matters: Transient network failures must not crash the crawl pipeline or expose data.
        Setup summary: Mock HEAD to raise a connection error; assert the original URL is returned.
        """
        mock_client = AsyncMock()
        mock_client.head = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "unique_web_search.services.url_safety.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await resolve_redirect_chain("https://example.com/page")

        assert result == "https://example.com/page"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__max_hops_exceeded__stops_at_last_validated_url(
        self,
    ) -> None:
        """
        Purpose: Verify the hop limit prevents infinite redirect loops.
        Why this matters: An attacker can set up a long redirect chain to exhaust resources or confuse validators.
        Setup summary: Produce more 302s than max_hops; assert resolution stops at hop 9 (index 0-based).
        """
        # 15 redirects — more than _MAX_REDIRECT_HOPS (10)
        responses = [(302, f"https://hop{i}.example.com/") for i in range(15)]
        responses.append((200, None))
        mock_client = self._make_mock_client(responses)

        with patch(
            "unique_web_search.services.url_safety.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await resolve_redirect_chain("https://start.example.com/")

        # After 10 hops the loop exits; current URL is the 10th redirect destination
        assert result == "https://hop9.example.com/"
        assert mock_client.head.call_count == 10
