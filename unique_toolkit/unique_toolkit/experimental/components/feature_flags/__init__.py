"""Feature flag client backed by configuration-backend's GraphQL API.

Provides OpenFeature-compatible semantics (``evaluate`` / ``is_enabled``)
without a dependency on the OpenFeature Python SDK.

Usage::

    from unique_toolkit.experimental.components.feature_flags import (
        FeatureFlagClient,
        FlagEvaluation,
    )

    client = FeatureFlagClient.from_settings()

    # preferred — bind once per request, no explicit IDs needed
    bound = client.bind_settings(settings)
    if await bound.is_enabled("FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION"):
        ...
"""

from .client import BoundFeatureFlagClient, FeatureFlagClient
from .schemas import FlagEvaluation
from .settings import FeatureFlagSettings

__all__ = [
    "BoundFeatureFlagClient",
    "FeatureFlagClient",
    "FlagEvaluation",
    "FeatureFlagSettings",
]
