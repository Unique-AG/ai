"""Feature flag client backed by configuration-backend's GraphQL API.

Provides OpenFeature-compatible semantics (``evaluate`` / ``is_enabled``)
without a dependency on the OpenFeature Python SDK.

Usage::

    from unique_toolkit.experimental.components.feature_flags import (
        FeatureFlagClient,
        FlagEvaluation,
        FeatureFlagSettings,
    )

    client = FeatureFlagClient.from_settings()
    result = await client.evaluate(
        "FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION",
        company_id="acme",
        user_id="user-123",
    )
"""

from .client import FeatureFlagClient
from .schemas import FlagEvaluation
from .settings import FeatureFlagSettings

__all__ = ["FeatureFlagClient", "FlagEvaluation", "FeatureFlagSettings"]
