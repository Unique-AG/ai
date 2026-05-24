import logging
import os
from functools import lru_cache

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt

from ._graphql_client import evaluate_flag
from ._ttl_cache import AsyncTTLCache
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
    ``FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION``. This matches both the
    configuration-backend registry key convention and the agentic-ingestion
    env-var names, so env-var fallback requires no transformation.

    Example::

        client = FeatureFlagClient.from_settings()
        result = await client.evaluate(
            "FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION",
            company_id="acme",
            user_id="user-123",
        )
        if result.value:
            ...
    """

    def __init__(self, *, url: str, service_id: str, ttl_ms: int = 30_000) -> None:
        self._url = url
        self._service_id = service_id
        self._cache = AsyncTTLCache(ttl=ttl_ms / 1000)

    @classmethod
    @lru_cache(maxsize=1)
    def from_settings(cls) -> "FeatureFlagClient":
        """Construct a client from environment variables.

        Reads :class:`.FeatureFlagSettings` (``CONFIGURATION_BACKEND_URL``,
        ``FEATURE_FLAG_SERVICE_ID``, ``FEATURE_FLAG_CACHE_TTL_MS``).

        Raises:
            ValueError: If ``CONFIGURATION_BACKEND_URL`` or
                ``FEATURE_FLAG_SERVICE_ID`` are not set.
        """
        s = FeatureFlagSettings()
        if not s.CONFIGURATION_BACKEND_URL:
            raise ValueError(
                "CONFIGURATION_BACKEND_URL is required to use FeatureFlagClient"
            )
        if not s.FEATURE_FLAG_SERVICE_ID:
            raise ValueError(
                "FEATURE_FLAG_SERVICE_ID is required to use FeatureFlagClient"
            )
        return cls(
            url=s.CONFIGURATION_BACKEND_URL,
            service_id=s.FEATURE_FLAG_SERVICE_ID,
            ttl_ms=s.FEATURE_FLAG_CACHE_TTL_MS,
        )

    async def evaluate(
        self,
        flag: str,
        *,
        company_id: str,
        user_id: str | None = None,
    ) -> FlagEvaluation:
        """Evaluate *flag* for the given context.

        Args:
            flag: Upper-snake flag key (e.g. ``FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION``).
            company_id: Company context for the evaluation.
            user_id: Optional user context. Omitted from the request when ``None``;
                cache key uses ``__none__`` as the user component.

        Returns:
            A :class:`.FlagEvaluation` with ``value`` and ``reason``.
        """
        if not company_id:
            raise ValueError("company_id must be a non-empty string")

        cache_key = f"{flag}:{company_id}:{user_id!r}"
        try:
            value, from_cache = await self._cache.get_or_fetch(
                cache_key,
                lambda: self._fetch(flag=flag, company_id=company_id, user_id=user_id),
            )
            return FlagEvaluation(
                value=value, reason="cached" if from_cache else "remote"
            )
        except Exception:
            logger.warning(
                "FeatureFlagClient: evaluation failed for '%s' — using env-var fallback",
                flag,
                exc_info=True,
            )
            stale_value = self._cache.get_stale(cache_key)
            if stale_value is not None:
                return FlagEvaluation(value=stale_value, reason="stale")
            return FlagEvaluation(value=self._env_fallback(flag), reason="fallback")

    async def is_enabled(
        self,
        flag: str,
        *,
        company_id: str,
        user_id: str | None = None,
    ) -> bool:
        """Return ``True`` if *flag* is enabled for the given context.

        Convenience wrapper around :meth:`evaluate` that returns only the
        boolean value.
        """
        return (await self.evaluate(flag, company_id=company_id, user_id=user_id)).value

    @retry(
        retry=retry_if_exception(
            lambda exc: isinstance(exc, httpx.HTTPStatusError)
            and exc.response.status_code >= 500
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
            url=self._url,
            flag=flag,
            service_id=self._service_id,
            company_id=company_id,
            user_id=user_id,
        )

    @staticmethod
    def _env_fallback(flag: str) -> bool:
        return os.getenv(flag, "false").lower() in ("true", "1", "yes")
