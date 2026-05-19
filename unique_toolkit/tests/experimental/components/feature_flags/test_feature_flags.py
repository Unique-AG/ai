"""Tests for unique_toolkit.experimental.components.feature_flags."""

from __future__ import annotations

import httpx
import pytest
import respx

from unique_toolkit.experimental.components.feature_flags import (
    FeatureFlagClient,
    FlagEvaluation,
)

_URL = "https://config-backend.test"
_FLAG = "FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION"
_SERVICE_ID = "agentic-ingestion"
_COMPANY_ID = "acme"
_USER_ID = "user-123"
_GQL_ENDPOINT = f"{_URL}/graphql"


def _make_client(url: str | None = _URL, ttl_ms: int = 30_000) -> FeatureFlagClient:
    return FeatureFlagClient(url=url, service_id=_SERVICE_ID, ttl_ms=ttl_ms)


def _gql_response(value: bool) -> dict:
    return {"data": {"evaluateFlag": value}}


# ---------------------------------------------------------------------------
# 1. Remote evaluation — returns FlagEvaluation(value=True, reason="remote")
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__remote_hit__returns_remote_reason() -> None:
    """
    Purpose: Verify a successful GraphQL response is returned with reason="remote".
    Why this matters: Confirms the happy path — remote eval reaches the server and propagates the value.
    Setup summary: Mock GraphQL endpoint returns True; assert FlagEvaluation(True, "remote").
    """
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="remote")


# ---------------------------------------------------------------------------
# 2. Cache hit — second call does not fire HTTP; reason is "cached"
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__cache_hit__second_call_skips_http() -> None:
    """
    Purpose: Verify that a second call with the same key uses the TTL cache and returns reason="cached".
    Why this matters: Ensures connection-backend is not called on every request within the TTL window.
    Setup summary: Call evaluate twice with the same context; assert HTTP mock called once and second reason is "cached".
    """
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    first = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)
    second = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert route.call_count == 1
    assert first == FlagEvaluation(value=True, reason="remote")
    assert second == FlagEvaluation(value=True, reason="cached")


# ---------------------------------------------------------------------------
# 3. Transport failure → env-var fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_failure__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a transport error triggers graceful fallback to the env-var default.
    Why this matters: Ensures ingestion is never blocked by a configuration-backend outage.
    Setup summary: Mock raises ConnectError; env var set to "false"; assert FlagEvaluation(False, "fallback").
    """
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
    """
    Purpose: Verify env-var fallback respects the actual env-var value (not always False).
    Why this matters: Services with the flag enabled via env-var must stay enabled on outage.
    Setup summary: Mock raises ConnectError; env var set to "true"; assert FlagEvaluation(True, "fallback").
    """
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, "true")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="fallback")


# ---------------------------------------------------------------------------
# 4. Missing URL → immediate fallback without HTTP
# ---------------------------------------------------------------------------


@pytest.mark.ai
async def test_evaluate__no_url__immediate_fallback_no_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify that a client constructed without a URL never makes HTTP calls.
    Why this matters: Services without CONFIGURATION_BACKEND_URL must still work via env-vars.
    Setup summary: Construct client with url=None; assert reason="fallback" without any HTTP mock.
    """
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client(url=None)
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")


# ---------------------------------------------------------------------------
# 5. user_id=None — x-user-id header omitted; cache key uses __none__
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__no_user_id__header_omitted_and_cache_key_uses_none() -> None:
    """
    Purpose: Verify user_id=None omits the x-user-id header and uses a stable cache key.
    Why this matters: Service-to-service calls have no user context; header must be absent.
    Setup summary: Call evaluate with user_id=None; assert header absent and second call is cached.
    """
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


# ---------------------------------------------------------------------------
# 6. is_enabled() returns bool, delegates to evaluate()
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_is_enabled__returns_bool() -> None:
    """
    Purpose: Verify is_enabled() returns a plain bool by delegating to evaluate().
    Why this matters: Callers using is_enabled() expect a bool, not a FlagEvaluation.
    Setup summary: Mock returns True; assert result is True and isinstance(result, bool).
    """
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    result = await client.is_enabled(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result is True
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# 7. GraphQL returns null → RuntimeError → fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__graphql_null_response__falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a null GraphQL response triggers fallback rather than silently caching None.
    Why this matters: An unregistered flag returns null; must not corrupt the bool type contract.
    Setup summary: Mock returns evaluateFlag=null; assert reason="fallback".
    """
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"data": {"evaluateFlag": None}})
    )
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")


# ---------------------------------------------------------------------------
# 8. GraphQL errors field → RuntimeError → fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__graphql_errors_field__falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a GraphQL errors response triggers fallback.
    Why this matters: Authorization failures or bad queries must not crash the ingestion path.
    Setup summary: Mock returns errors field; assert reason="fallback".
    """
    respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"errors": [{"message": "Unauthorized"}]})
    )
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")


# ---------------------------------------------------------------------------
# 9. Different (company, user) pairs are cached independently
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__different_contexts__cached_independently() -> None:
    """
    Purpose: Verify that different (company_id, user_id) combinations are not cross-contaminated in cache.
    Why this matters: Per-company/per-user flag rollout requires independent cache entries.
    Setup summary: Call evaluate for two distinct contexts; assert HTTP mock called twice.
    """
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    await client.evaluate(_FLAG, company_id="company-a", user_id="user-1")
    await client.evaluate(_FLAG, company_id="company-b", user_id="user-2")

    assert route.call_count == 2


# ---------------------------------------------------------------------------
# 10. from_settings() constructs client from env vars
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_from_settings__constructs_client_from_env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify from_settings() reads env vars and produces a correctly configured client.
    Why this matters: This is the primary adoption path for consuming services.
    Setup summary: Set all three env vars; assert client._url, _service_id, and _available.
    """
    monkeypatch.setenv("CONFIGURATION_BACKEND_URL", "https://config.test")
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "agentic-ingestion")
    monkeypatch.setenv("FEATURE_FLAG_CACHE_TTL_MS", "5000")

    client = FeatureFlagClient.from_settings()

    assert client._url == "https://config.test"
    assert client._service_id == "agentic-ingestion"
    assert client._available is True


@pytest.mark.ai
def test_from_settings__no_url__client_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify from_settings() produces an unavailable client when URL is absent.
    Why this matters: Ensures _available=False is set correctly for the fallback path.
    Setup summary: Set only FEATURE_FLAG_SERVICE_ID; assert _available is False.
    """
    monkeypatch.delenv("CONFIGURATION_BACKEND_URL", raising=False)
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "agentic-ingestion")

    client = FeatureFlagClient.from_settings()

    assert client._url is None
    assert client._available is False
