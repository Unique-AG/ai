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
# 14. env-var fallback respects company-ID allowlist
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__fallback_allowlist__company_in_list__returns_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify that a comma-separated company-ID allowlist in the env var is respected on fallback.
    Why this matters: Matches FeatureFlags semantics — same env-var format must behave identically.
    Setup summary: Env var set to "acme,other"; mock raises ConnectError; assert True for acme, False for unknown.
    """
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, f"{_COMPANY_ID},other-company")

    client = _make_client()
    result_in = await client.evaluate(_FLAG, company_id=_COMPANY_ID)
    result_out = await client.evaluate(_FLAG, company_id="unknown-company")

    assert result_in == FlagEvaluation(value=True, reason="fallback")
    assert result_out == FlagEvaluation(value=False, reason="fallback")


# ---------------------------------------------------------------------------
# 15. Retry: single 503 → retries once → second attempt succeeds → reason="remote"
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__single_503__retries_and_succeeds() -> None:
    """
    Purpose: Verify a single 503 response triggers one retry and the successful second attempt is returned.
    Why this matters: Transient backend blips must not surface as errors to callers.
    Setup summary: First call returns 503, second returns 200 True; assert FlagEvaluation(True, "remote").
    """
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


# ---------------------------------------------------------------------------
# 16. Retry: two consecutive 503s → both attempts fail → env-var fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__two_503s__exhausts_retries__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify two consecutive 503 responses exhaust the retry budget and fall back to env-var.
    Why this matters: A sustained backend outage must degrade gracefully, not raise.
    Setup summary: Both attempts return 503; env var set to "true"; assert FlagEvaluation(True, "fallback").
    """
    route = respx.post(_GQL_ENDPOINT).mock(return_value=httpx.Response(503))
    monkeypatch.setenv(_FLAG, "true")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=True, reason="fallback")
    assert route.call_count == 2


# ---------------------------------------------------------------------------
# 17. Timeout → no retry → env-var fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__read_timeout__no_retry__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify that a ReadTimeout is not retried (only 5xx errors are) and falls back to env-var.
    Why this matters: Retrying on timeouts could amplify load on an already-slow backend.
    Setup summary: Mock raises ReadTimeout; env var set to "false"; assert FlagEvaluation(False, "fallback") and route called once.
    """
    route = respx.post(_GQL_ENDPOINT).mock(
        side_effect=httpx.ReadTimeout("timed out", request=None)
    )
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")
    assert route.call_count == 1


# ---------------------------------------------------------------------------
# 18. BoundFeatureFlagClient: bind_settings returns correct type
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_bind_settings__returns_bound_client() -> None:
    """
    Purpose: Verify bind_settings() returns a BoundFeatureFlagClient wrapping the parent client.
    Why this matters: Confirms the binding API works without making any network call.
    Setup summary: Call bind_settings with _FakeSettings; assert result is BoundFeatureFlagClient.
    """
    client = _make_client()
    bound = client.bind_settings(_FakeSettings())  # type: ignore[arg-type]

    assert isinstance(bound, BoundFeatureFlagClient)


# ---------------------------------------------------------------------------
# 19. BoundFeatureFlagClient: evaluate extracts correct company_id / user_id
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_bound_client__evaluate__uses_auth_context_ids() -> None:
    """
    Purpose: Verify bound.evaluate() forwards company_id and user_id from the auth context.
    Why this matters: The whole point of BoundFeatureFlagClient is transparent ID injection.
    Setup summary: Bind to _FakeSettings; call evaluate; assert request headers carry correct IDs.
    """
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


# ---------------------------------------------------------------------------
# 20. BoundFeatureFlagClient: shares cache with parent client
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_bound_client__shares_cache_with_parent() -> None:
    """
    Purpose: Verify a fetch via the parent client is visible to the bound client as a cache hit.
    Why this matters: Singleton parent + per-request bound client must share the same TTL cache.
    Setup summary: Fetch via parent; call bound.evaluate for same key; assert route called once and bound reason is "cached".
    """
    route = respx.post(_GQL_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_gql_response(True))
    )

    client = _make_client()
    await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    bound = client.bind_settings(_FakeSettings())  # type: ignore[arg-type]
    result = await bound.evaluate(_FLAG)

    assert route.call_count == 1
    assert result == FlagEvaluation(value=True, reason="cached")


# ---------------------------------------------------------------------------
# 21. BoundFeatureFlagClient: stale path on transport error
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_bound_client__stale_on_transport_error() -> None:
    """
    Purpose: Verify the bound client returns a stale value on transport error after a prior fetch.
    Why this matters: Ensures stale-cache resilience works end-to-end through the bound interface.
    Setup summary: Fetch via bound; expire TTL cache; transport error on retry; assert FlagEvaluation(True, "stale").
    """
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


# ---------------------------------------------------------------------------
# 22. Cache key collision: tuple key prevents cross-tenant leakage
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__tuple_cache_key__no_collision() -> None:
    """
    Purpose: Verify (flag, "a:b", None) and (flag, "a", "b:None") are distinct cache entries.
    Why this matters: A string key with ":" separator would collide; tuple key must not.
    Setup summary: Fetch for company_id="a:b" user_id=None (True), then company_id="a" user_id="b:None" (False); assert both are cached independently.
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


# ---------------------------------------------------------------------------
# 23. False-value sentinel: disabled flag is cached correctly (regression)
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__false_value__cached_on_second_call() -> None:
    """
    Purpose: Verify a flag evaluating to False is served from cache on the second call.
    Why this matters: Regression for the _MISSING sentinel bug — cache.get(key) returns None for
                      both a missing key and a stored False, so False values were never cached.
    Setup summary: Remote returns False; second call must return reason="cached" and route called once.
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


# ---------------------------------------------------------------------------
# 24. False-value stale: stale False is returned on transport error (regression)
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__false_stale__returned_on_transport_error() -> None:
    """
    Purpose: Verify a stale False (not None) is returned correctly on transport error.
    Why this matters: Regression for the stale-value check — `if stale_value is not None` silently
                      discards a known-good stale False, falling through to env-var fallback.
    Setup summary: Fetch returns False; expire TTL; transport error; assert FlagEvaluation(False, "stale").
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


# ---------------------------------------------------------------------------
# 25. Stampede protection: concurrent calls fire exactly one HTTP request
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__concurrent_calls__single_http_request() -> None:
    """
    Purpose: Verify two concurrent evaluate() calls for the same key fire exactly one HTTP request.
    Why this matters: Without per-key locking, a cache miss under concurrency would send N parallel
                      requests to configuration-backend — a stampede.
    Setup summary: asyncio.gather two evaluate() calls; assert route called once and both return same value.
    """
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


# ---------------------------------------------------------------------------
# 4. Missing URL → immediate fallback without HTTP
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_from_settings__no_url__raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify from_settings() raises ValueError when CONFIGURATION_BACKEND_URL is absent.
    Why this matters: Prevents silent misconfiguration — callers must set the URL explicitly.
    Setup summary: Unset CONFIGURATION_BACKEND_URL; assert ValueError is raised.
    """
    monkeypatch.delenv("CONFIGURATION_BACKEND_URL", raising=False)
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "agentic-ingestion")

    with pytest.raises(ValueError, match="CONFIGURATION_BACKEND_URL"):
        FeatureFlagClient.from_settings()


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
# 10. empty company_id raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.ai
async def test_evaluate__empty_company_id__raises_value_error() -> None:
    """
    Purpose: Verify that an empty company_id is rejected before any HTTP call.
    Why this matters: An empty company_id would send a meaningless x-company-id header and produce an ambiguous cache key.
    Setup summary: Call evaluate with company_id=""; assert ValueError is raised.
    """
    client = _make_client()

    with pytest.raises(ValueError, match="company_id"):
        await client.evaluate(_FLAG, company_id="")


# ---------------------------------------------------------------------------
# 11. from_settings() constructs client from env vars
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


# ---------------------------------------------------------------------------
# 12. Stale cache: transport error with prior value → reason="stale"
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_error_after_prior_fetch__returns_stale() -> None:
    """
    Purpose: Verify a transport error returns the last-known-good value (reason="stale") when
             the flag was previously fetched for this company.
    Why this matters: Config-backend outage must not fall back to a process-wide env-var default
                      when we already know the per-company value.
    Setup summary: First call succeeds (value=True). TTL cache is cleared to force a miss.
                   Second call raises ConnectError. Assert FlagEvaluation(True, "stale").
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


# ---------------------------------------------------------------------------
# 13. Stale cache: transport error with no prior value → reason="fallback"
# ---------------------------------------------------------------------------


@pytest.mark.ai
@respx.mock
async def test_evaluate__transport_error_no_prior_fetch__returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify that when no prior value exists, a transport error still falls back to env-var.
    Why this matters: On first-ever evaluation for a company, stale cache is empty; must not crash.
    Setup summary: First call raises ConnectError (no prior fetch). Env var set to "false".
                   Assert FlagEvaluation(False, "fallback").
    """
    respx.post(_GQL_ENDPOINT).mock(side_effect=httpx.ConnectError("unreachable"))
    monkeypatch.setenv(_FLAG, "false")

    client = _make_client()
    result = await client.evaluate(_FLAG, company_id=_COMPANY_ID, user_id=_USER_ID)

    assert result == FlagEvaluation(value=False, reason="fallback")
