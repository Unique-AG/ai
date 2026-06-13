from __future__ import annotations

import logging
import os
from typing import ClassVar

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt

from unique_toolkit._common.async_ttl_cache import AsyncTTLCache
from unique_toolkit.app.unique_settings import AuthContextProtocol, UniqueSettings

from ._graphql_client import evaluate_flag
from .schemas import FlagEvaluation
from .settings import FeatureFlagSettings

logger = logging.getLogger(__name__)


class FeatureFlagClient:
    """Feature flag client backed by configuration-backend's GraphQL API.

    Mirrors the OpenFeature ``evaluate`` / ``isEnabled`` semantics used by the
    Node.js ``@unique/feature-flags`` package without taking a dependency on
    the OpenFeature Python SDK.

    Evaluation order:
    1. Check the in-process TTL cache; return a cached value if present.
    2. Call configuration-backend's ``evaluateFlag`` GraphQL query (one
       retry on transient 5xx errors).
    3. On failure, return the last successfully fetched value (stale cache)
       if one exists, otherwise fall back to the env-var default.

    The ``flag`` argument must be the upper-snake env-var-style key, e.g.
    ``FEATURE_FLAG_ENABLE_MY_FEATURE``. This matches both the
    configuration-backend registry key convention and the existing env-var
    names, so env-var fallback requires no transformation.

    Example (with UniqueSettings)::

        client = FeatureFlagClient.from_settings()
        bound  = client.bind_settings(settings)
        if await bound.is_enabled("FEATURE_FLAG_ENABLE_MY_FEATURE"):
            ...

    Example (explicit IDs)::

        result = await client.evaluate(
            "FEATURE_FLAG_ENABLE_MY_FEATURE",
            company_id="acme",
            user_id="user-123",
        )
    """

    _instance: ClassVar[FeatureFlagClient | None] = None

    def __init__(self, *, url: str, service_id: str, ttl_ms: int = 5_000) -> None:
        self._url = url
        self._service_id = service_id
        self._cache = AsyncTTLCache(ttl_ms=ttl_ms)
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0))

    @classmethod
    def from_settings(cls) -> FeatureFlagClient:
        """Construct (or return the cached) singleton from environment variables.

        Reads :class:`.FeatureFlagSettings` (``CONFIGURATION_BACKEND_URL``,
        ``FEATURE_FLAG_SERVICE_ID``, ``FEATURE_FLAG_CACHE_TTL_MS``).

        Raises:
            ValueError: If ``CONFIGURATION_BACKEND_URL`` or
                ``FEATURE_FLAG_SERVICE_ID`` are not set.
        """
        if cls._instance is not None:
            return cls._instance
        s = FeatureFlagSettings()
        if not s.configuration_backend_url:
            raise ValueError(
                "CONFIGURATION_BACKEND_URL is required to use FeatureFlagClient"
            )
        if not s.feature_flag_service_id:
            raise ValueError(
                "FEATURE_FLAG_SERVICE_ID is required to use FeatureFlagClient"
            )
        cls._instance = cls(
            url=s.configuration_backend_url,
            service_id=s.feature_flag_service_id,
            ttl_ms=s.feature_flag_cache_ttl_ms,
        )
        return cls._instance

    def bind_settings(self, settings: UniqueSettings) -> BoundFeatureFlagClient:
        """Return a :class:`BoundFeatureFlagClient` for the request-level auth context."""
        return BoundFeatureFlagClient(self, settings.authcontext)

    async def evaluate(
        self,
        flag: str,
        *,
        company_id: str,
        user_id: str | None = None,
    ) -> FlagEvaluation:
        """Evaluate *flag* for the given context."""
        company_id = company_id.strip()
        if not company_id:
            raise ValueError("company_id must be a non-empty string")

        cache_key = (flag, company_id, user_id)
        try:
            value, from_cache = await self._cache.get_or_fetch(
                cache_key,
                lambda: self._fetch(flag=flag, company_id=company_id, user_id=user_id),
            )
            return FlagEvaluation(
                value=value, reason="cached" if from_cache else "remote"
            )
        except Exception as exc:
            logger.warning(
                "FeatureFlagClient: fetch failed for '%s' (company=%s) — trying stale cache",
                flag,
                company_id,
                exc_info=not isinstance(exc, httpx.HTTPError),
            )
            stale_value, stale_hit = self._cache.get_stale(cache_key)
            if stale_hit:
                logger.warning(
                    "FeatureFlagClient: stale cache hit for '%s' (company=%s, value=%s)",
                    flag,
                    company_id,
                    stale_value,
                )
                return FlagEvaluation(value=stale_value, reason="stale")
            logger.warning(
                "FeatureFlagClient: no stale value for '%s' (company=%s) — falling back to env var",
                flag,
                company_id,
            )
            return FlagEvaluation(
                value=self._env_fallback(flag, company_id), reason="fallback"
            )

    async def is_enabled(
        self,
        flag: str,
        *,
        company_id: str,
        user_id: str | None = None,
    ) -> bool:
        """Return ``True`` if *flag* is enabled for the given context."""
        return (await self.evaluate(flag, company_id=company_id, user_id=user_id)).value

    @retry(
        retry=retry_if_exception(
            lambda exc: (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code >= 500
            )
        ),
        stop=stop_after_attempt(2),
        reraise=True,
    )
    async def _fetch(
        self,
        *,
        flag: str,
        company_id: str,
        user_id: str | None,
    ) -> bool:
        return await evaluate_flag(
            http=self._http,
            url=self._url,
            flag=flag,
            service_id=self._service_id,
            company_id=company_id,
            user_id=user_id,
        )

    @staticmethod
    def _env_fallback(flag: str, company_id: str | None = None) -> bool:
        """Read *flag* from env vars using the same semantics as ``FeatureFlag``.

        Supports both plain booleans (``"true"`` / ``"false"``) and
        comma-separated company-ID allowlists (``"company1,company2"``),
        consistent with ``unique_toolkit.agentic.feature_flags.FeatureFlags``.
        """
        raw = os.getenv(flag, "false").strip()
        raw_lower = raw.lower()
        if raw_lower in ("true", "1", "yes"):
            return True
        if raw_lower in ("false", "0", "no", ""):
            return False
        # Comma-separated company-ID allowlist
        allowed = {part.strip() for part in raw.split(",") if part.strip()}
        return company_id in allowed if company_id else False


class BoundFeatureFlagClient:
    """A :class:`FeatureFlagClient` bound to a request-level auth context.

    Obtain via :meth:`FeatureFlagClient.bind_settings` — do not instantiate directly.
    """

    def __init__(self, client: FeatureFlagClient, auth: AuthContextProtocol) -> None:
        self._client = client
        self._auth = auth

    async def evaluate(self, flag: str) -> FlagEvaluation:
        return await self._client.evaluate(
            flag,
            company_id=self._auth.get_confidential_company_id(),
            user_id=self._auth.get_confidential_user_id(),
        )

    async def is_enabled(self, flag: str) -> bool:
        return (await self.evaluate(flag)).value


def get_feature_flag_client() -> FeatureFlagClient:
    """Return the process-level :class:`FeatureFlagClient` singleton.

    Built lazily via :meth:`FeatureFlagClient.from_settings` which reads
    ``CONFIGURATION_BACKEND_URL`` and ``FEATURE_FLAG_SERVICE_ID`` from env.
    Falls back to env-var defaults on missing config or transport errors.
    """
    return FeatureFlagClient.from_settings()


async def is_flag_enabled(
    flag: str,
    company_id: str,
    user_id: str | None = None,
) -> bool:
    """Evaluate *flag* and log when disabled.

    Convenience wrapper for route handlers that want a single call-site
    without manually managing the client singleton.
    """
    enabled = await get_feature_flag_client().is_enabled(
        flag, company_id=company_id, user_id=user_id
    )
    if not enabled:
        user_suffix = f" user {user_id}" if user_id else ""
        logger.info(
            "Feature flag '%s' disabled for company %s%s.",
            flag,
            company_id,
            user_suffix,
        )
    return enabled
