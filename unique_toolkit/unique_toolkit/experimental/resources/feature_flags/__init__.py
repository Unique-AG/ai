"""Feature flag client backed by configuration-backend's GraphQL API.

Evaluates flags remotely with a 5 s TTL cache, stale-value fallback on
transport errors, and env-var fallback when no prior value exists.
Env-var values support both plain booleans and comma-separated company-ID
allowlists, consistent with ``unique_toolkit.agentic.feature_flags``.

Required env vars::

    CONFIGURATION_BACKEND_URL=https://<your-configuration-backend>
    FEATURE_FLAG_SERVICE_ID=your-service-name

Quick start — explicit IDs::

    from unique_toolkit.experimental.resources.feature_flags import FeatureFlagClient, is_flag_enabled

    # Requires CONFIGURATION_BACKEND_URL / FEATURE_FLAG_SERVICE_ID to be set;
    # falls back to the env-var value (or stale cache) on transport errors.
    enabled = await is_flag_enabled("FEATURE_FLAG_ENABLE_X", company_id=company_id)

    # Or manage the singleton directly:
    client = FeatureFlagClient.from_settings()  # raises if URL/service_id absent
    client = get_feature_flag_client()          # same — thin passthrough to from_settings()

Per-request binding (when you have UniqueSettings / AuthContext)::

    bound = client.bind_settings(settings)      # bind once per request
    enabled = await bound.is_enabled("FEATURE_FLAG_ENABLE_X")

Define flag name constants in your service to avoid magic strings::

    class MyServiceFlags:
        ENABLE_X = "FEATURE_FLAG_ENABLE_X"
        ENABLE_Y = "FEATURE_FLAG_ENABLE_Y"

See README.md for the full evaluation-order diagram and adoption steps.
"""

from .client import (
    BoundFeatureFlagClient,
    FeatureFlagClient,
    get_feature_flag_client,
    is_flag_enabled,
)
from .schemas import FlagEvaluation
from .settings import FeatureFlagSettings

__all__ = [
    "BoundFeatureFlagClient",
    "FeatureFlagClient",
    "FlagEvaluation",
    "FeatureFlagSettings",
    "get_feature_flag_client",
    "is_flag_enabled",
]
