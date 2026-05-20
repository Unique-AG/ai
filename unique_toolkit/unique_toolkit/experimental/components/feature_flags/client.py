import logging
import os

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
    1. If the client was constructed without a URL (``_available=False``),
       return the env-var fallback immediately.
    2. Check the in-process TTL cache; return a cached value if present.
    3. Call configuration-backend's ``evaluateFlag`` GraphQL query.
    4. On any transport or GraphQL error, log a warning and return the
       env-var fallback.

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

    def __init__(
        self,
        *,
        url: str | None,
        service_id: str | None = None,
        ttl_ms: int = 30_000,
    ) -> None:
        self._url = url or None  # coerce empty string → None
        self._service_id = service_id or None  # coerce empty string → None
        self._available = bool(self._url) and bool(self._service_id)
        self._cache = AsyncTTLCache(ttl=ttl_ms / 1000)
        if not self._url:
            logger.warning(
                "FeatureFlagClient: CONFIGURATION_BACKEND_URL is not set — "
                "all flag evaluations will use env-var fallback"
            )
        elif not self._service_id:
            logger.warning(
                "FeatureFlagClient: FEATURE_FLAG_SERVICE_ID is not set — "
                "all flag evaluations will use env-var fallback"
            )

    @classmethod
    def from_settings(cls) -> "FeatureFlagClient":
        """Construct a client from environment variables.

        Reads :class:`.FeatureFlagSettings` (``CONFIGURATION_BACKEND_URL``,
        ``FEATURE_FLAG_SERVICE_ID``, ``FEATURE_FLAG_CACHE_TTL_MS``).
        """
        s = FeatureFlagSettings()
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
        if not self._available:
            return FlagEvaluation(value=self._env_fallback(flag), reason="fallback")

        assert self._url is not None  # _available guards this
        assert self._service_id is not None  # _available guards this
        url: str = self._url
        service_id: str = self._service_id
        try:
            cache_key = f"{flag}:{company_id}:{user_id or '__none__'}"
            value, from_cache = await self._cache.get_or_fetch(
                cache_key,
                lambda: evaluate_flag(
                    url=url,
                    flag=flag,
                    service_id=service_id,
                    company_id=company_id,
                    user_id=user_id,
                ),
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

    @staticmethod
    def _env_fallback(flag: str) -> bool:
        return os.getenv(flag, "false").lower() in ("true", "1", "yes")
