"""Tests for unique_toolkit.experimental.components.feature_flags."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from unique_toolkit.experimental.components.feature_flags import (
    BoundFeatureFlagClient,
    FeatureFlagClient,
    FlagEvaluation,
)

# ---------------------------------------------------------------------------
# Minimal fakes for BoundFeatureFlagClient tests
# ---------------------------------------------------------------------------


class _FakeAuth:
    def get_confidential_company_id(self) -> str:
        return _COMPANY_ID

    def get_confidential_user_id(self) -> str:
        return _USER_ID


class _FakeSettings:
    authcontext = _FakeAuth()


_URL = "https://config-backend.test"
_FLAG = "FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION"
_SERVICE_ID = "agentic-ingestion"
_COMPANY_ID = "acme"
_USER_ID = "user-123"
_GQL_ENDPOINT = f"{_URL}/graphql"


def _make_client(url: str = _URL, ttl_ms: int = 30_000) -> FeatureFlagClient:
    return FeatureFlagClient(url=url, service_id=_SERVICE_ID, ttl_ms=ttl_ms)


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    """Reset the from_settings() singleton between tests so monkeypatch env changes take effect."""
    FeatureFlagClient._instance = None


def _gql_response(value: bool) -> dict:
    return {"data": {"evaluateFlag": value}}


@pytest.mark.ai
@respx.mock
async def test_evaluate__remote_hit__returns_remote_reason() -> None:
    """Verify a successful GraphQL response is returned with reason="remote"."""
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="remote")


@pytest.mark.ai
@respx.mock
async def test_evaluate__cache_hit__second_call_skips_http() -> None:
    """Verify that a second call with the same key uses the TTL cache and returns reason="cached"."""
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    first = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)
    second = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert route.call_count == 1
    assert first == FlagEvaluation(value=True, reason="remote")
    assert second == FlagEvaluation(value=True, reason="cached")


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_failure__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a transport error triggers graceful fallback to the env-var default."""
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_failure__env_var_true__returns_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify env-var fallback respects the actual env-var value (not always False)."""
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, "true")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="fallback")


@pytest.mark.ai
@respx.mock
async def test_evaluate__fallback_allowlist__company_in_list__returns_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that a comma-separated company-ID allowlist in the env var is respected on fallback."""
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, f"{_COMPANY_ID},other-company")

    client = _make_client()
    result_in = await client.evaluate(_FLAG, company_id=_COMPANY_ID)
    result_out = await client.evaluate(_FLAG, company_id="unknown-company")

    assert result_in == FlagEvaluation(value=True, reason="fallback")
    assert result_out == FlagEvaluation(value=False, reason="fallback")


@pytest.mark.ai
@respx.mock
async def test_evaluate__single_503__retries_and_succeeds() -> None:
    """Verify a single 503 response triggers one retry and the successful second attempt is returned."""
    _responses = iter(
        [
            httpx.Response(503),
            httpx.Response(200, json=_gql_response(True)),
        ]
    )
    route = respx.post(_GQL_ENDPOINT).mock(side_effect=lambda _req: next(_responses))

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="remote")
    assert route.call_count == 2


@pytest.mark.ai
@respx.mock
async def test_evaluate__two_503s__exhausts_retries__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify two consecutive 503 responses exhaust the retry budget and fall back to env-var."""
    route = respx.post(_GQL_ENDPOINT).mock(return_value=httpx.Response(503))
    monkeypatch.setenv(_FLAG, "true")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="fallback")
    assert route.call_count == 2


@pytest.mark.ai
@respx.mock
async def test_evaluate__read_timeout__no_retry__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that a ReadTimeout is not retried (only 5xx errors are) and falls back to env-var."""
    route = respx.post(_GQL_ENDPOINT).mock(
        side_effect=httpx.ReadTimeout("timed out", request=None)
    )
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")
    assert route.call_count == 1


@pytest.mark.ai
def test_bind_settings__returns_bound_client() -> None:
    """Verify bind_settings() returns a BoundFeatureFlagClient wrapping the parent client."""
    client = _make_client()
    bound = client.bind_settings(_FakeSettings())  # type: ignore[arg-type]

    assert isinstance(bound, BoundFeatureFlagClient)


@pytest.mark.ai
@respx.mock
async def test_bound_client__evaluate__uses_auth_context_ids() -> None:
    """Verify bound.evaluate() forwards company_id and user_id from the auth context."""
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    bound = client.bind_settings(_FakeSettings())  # type: ignore[arg-type]
    result = await bound.evaluate(_FLAG)

    assert result == FlagEvaluation(value=True, reason="remote")
    headers = route.calls[0].request.headers
    assert headers["x-company-id"] == _COMPANY_ID
    assert headers["x-user-id"] == _USER_ID


@pytest.mark.ai
@respx.mock
async def test_bound_client__shares_cache_with_parent() -> None:
    """Verify a fetch via the parent client is visible to the bound client as a cache hit."""
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    bound = client.bind_settings(_FakeSettings())  # type: ignore[arg-type]
    result = await bound.evaluate(_FLAG)

    assert route.call_count == 1
    assert result == FlagEvaluation(value=True, reason="cached")


@pytest.mark.ai
@respx.mock
async def test_bound_client__stale_on_transport_error() -> None:
    """Verify the bound client returns a stale value on transport error after a prior fetch."""
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    bound = client.bind_settings(_FakeSettings())  # type: ignore[arg-type]
    first = await bound.evaluate(_FLAG)
    assert first.reason == "remote"

    client._cache._cache.clear()
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))

    result = await bound.evaluate(_FLAG)
    assert result == FlagEvaluation(value=True, reason="stale")


@pytest.mark.ai
@respx.mock
async def test_evaluate__tuple_cache_key__no_collision() -> None:
    """
    Verify (flag, "a:b", None) and (flag, "a", "b:None") are distinct cache entries.
    Why this matters: A string key with ":" separator would collide; tuple key must not.
    """
    _responses = iter(
        [
            httpx.Response(200, json=_gql_response(True)),
            httpx.Response(200, json=_gql_response(False)),
        ]
    )
    route = respx.post(_GQL_ENDPOINT).mock(side_effect=lambda _req: next(_responses))

    client = _make_client()
    r1 = await client.evaluate(_FLAG, company_id="a:b", user_id=None)
    r2 = await client.evaluate(_FLAG, company_id="a", user_id="b:None")

    assert route.call_count == 2
    assert r1.value is True
    assert r2.value is False


@pytest.mark.ai
@respx.mock
async def test_evaluate__false_value__cached_on_second_call() -> None:
    """
    Verify a flag evaluating to False is served from cache on the second call.
    Why this matters: Regression for the _MISSING sentinel bug — cache.get(key) returns None for
                      both a missing key and a stored False, so False values were never cached.
    """
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(False))
    )

    client = _make_client()
    first = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)
    second = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert route.call_count == 1
    assert first == FlagEvaluation(value=False, reason="remote")
    assert second == FlagEvaluation(value=False, reason="cached")


@pytest.mark.ai
@respx.mock
async def test_evaluate__false_stale__returned_on_transport_error() -> None:
    """
    Verify a stale False (not None) is returned correctly on transport error.
    Why this matters: Regression for the stale-value check — `if stale_value is not None` silently
                      discards a known-good stale False, falling through to env-var fallback.
    """
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(False))
    )

    client = _make_client()
    first = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)
    assert first == FlagEvaluation(value=False, reason="remote")

    client._cache._cache.clear()
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))

    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)
    assert result == FlagEvaluation(value=False, reason="stale")


@pytest.mark.ai
@respx.mock
async def test_evaluate__concurrent_calls__single_http_request() -> None:
    """Verify two concurrent evaluate() calls for the same key fire exactly one HTTP request."""
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    r1, r2 = await asyncio.gather(
        client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID),
        client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID),
    )

    assert route.call_count == 1
    assert r1.value is True
    assert r2.value is True


@pytest.mark.ai
def test_from_settings__no_url__raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify from_settings() raises ValueError when CONFIGURATION_BACKEND_URL is absent."""
    monkeypatch.delenv("CONFIGURATION_BACKEND_URL", raising=False)
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "agentic-ingestion")

    with pytest.raises(ValueError, match="CONFIGURATION_BACKEND_URL"):
        FeatureFlagClient.from_settings()


@pytest.mark.ai
@respx.mock
async def test_evaluate__no_user_id__header_omitted_and_cache_key_uses_none() -> None:
    """Verify user_id=None omits the x-user-id header and uses a stable cache key."""
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(False))
    )

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=None)

    assert result.value is False
    assert result.reason == "remote"
    sent_headers = route.calls[0].request.headers
    assert "x-user-id" not in sent_headers

    second = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=None)
    assert second.reason == "cached"
    assert route.call_count == 1


@pytest.mark.ai
@respx.mock
async def test_is_enabled__returns_bool() -> None:
    """Verify is_enabled() returns a plain bool by delegating to evaluate()."""
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    result = await client.is_enabled(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result is True
    assert isinstance(result, bool)


@pytest.mark.ai
@respx.mock
async def test_evaluate__graphql_null_response__falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a null GraphQL response triggers fallback rather than silently caching None."""
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"data": {"evaluateFlag": None}})
    )
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")


@pytest.mark.ai
@respx.mock
async def test_evaluate__graphql_errors_field__falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify a GraphQL errors response triggers fallback."""
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"errors": [{"message": "Unauthorized"}]})
    )
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")


@pytest.mark.ai
@respx.mock
async def test_evaluate__different_contexts__cached_independently() -> None:
    """Verify that different (company_id, user_id) combinations are not cross-contaminated in cache."""
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    await client.evaluate(_FLAG, company_id="company-a", user_id="user-1")
    await client.evaluate(_FLAG, company_id="company-b", user_id="user-2")

    assert route.call_count == 2


@pytest.mark.ai
async def test_evaluate__empty_company_id__raises_value_error() -> None:
    """Verify that an empty company_id is rejected before any HTTP call."""
    client = _make_client()

    with pytest.raises(ValueError, match="company_id"):
        await client.evaluate(_FLAG, company_id="")


@pytest.mark.ai
async def test_evaluate__whitespace_company_id__raises_value_error() -> None:
    """Whitespace-only company_id is truthy but must be rejected like an empty string."""
    client = _make_client()

    with pytest.raises(ValueError, match="company_id"):
        await client.evaluate(_FLAG, company_id="   ")


@pytest.mark.ai
def test_from_settings__whitespace_url__raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only CONFIGURATION_BACKEND_URL must raise ValueError, not produce an invalid URL."""
    monkeypatch.setenv("CONFIGURATION_BACKEND_URL", "   ")
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "my-service")

    with pytest.raises(ValueError, match="CONFIGURATION_BACKEND_URL"):
        FeatureFlagClient.from_settings()


@pytest.mark.ai
def test_from_settings__whitespace_service_id__raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only FEATURE_FLAG_SERVICE_ID must raise ValueError."""
    monkeypatch.setenv("CONFIGURATION_BACKEND_URL", "https://config.test")
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "   ")

    with pytest.raises(ValueError, match="FEATURE_FLAG_SERVICE_ID"):
        FeatureFlagClient.from_settings()


@pytest.mark.ai
def test_from_settings__constructs_client_from_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify from_settings() reads env vars and produces a correctly configured client."""
    monkeypatch.setenv("CONFIGURATION_BACKEND_URL", "https://config.test")
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "agentic-ingestion")
    monkeypatch.setenv("FEATURE_FLAG_CACHE_TTL_MS", "5000")

    client = FeatureFlagClient.from_settings()

    assert client._url == "https://config.test"
    assert client._service_id == "agentic-ingestion"


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_error_after_prior_fetch__returns_stale() -> None:
    """
    Verify a transport error returns the last-known-good value (reason="stale") when
    the flag was previously fetched for this company.
    """
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    first = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)
    assert first == FlagEvaluation(value=True, reason="remote")

    # Expire the TTL cache so the next call attempts a fetch, then make that fetch fail.
    client._cache._cache.clear()
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))

    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="stale")


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_error_no_prior_fetch__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that when no prior value exists, a transport error still falls back to env-var."""
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")
