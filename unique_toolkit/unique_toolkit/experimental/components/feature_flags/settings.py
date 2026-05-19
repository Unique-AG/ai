from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlagSettings(BaseSettings):
    """Settings for the feature flag client.

    All fields are read from environment variables. ``FEATURE_FLAG_SERVICE_ID``
    is required and must be non-empty; the client will refuse to construct if
    it is absent, preventing silent misconfiguration.

    Attributes:
        CONFIGURATION_BACKEND_URL: Base URL of the configuration-backend service
            (e.g. ``https://<your-configuration-backend>``). When ``None``,
            all evaluations fall back to env-var defaults immediately.
        FEATURE_FLAG_SERVICE_ID: Identifier sent as ``x-service-id`` header.
            Must match a value in configuration-backend's ``Service`` enum.
        FEATURE_FLAG_CACHE_TTL_MS: TTL for the in-process flag cache in
            milliseconds. Defaults to 30 000 ms (30 s).
    """

    CONFIGURATION_BACKEND_URL: str | None = None
    FEATURE_FLAG_SERVICE_ID: str = Field(..., min_length=1)
    FEATURE_FLAG_CACHE_TTL_MS: int = 30_000

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )
