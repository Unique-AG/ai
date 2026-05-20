from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlagSettings(BaseSettings):
    """Settings for the feature flag client.

    All fields are read from environment variables. Both
    ``CONFIGURATION_BACKEND_URL`` and ``FEATURE_FLAG_SERVICE_ID`` are required;
    :meth:`FeatureFlagClient.from_settings` raises ``ValueError`` if either is
    absent or empty.

    Attributes:
        CONFIGURATION_BACKEND_URL: Base URL of the configuration-backend service
            (e.g. ``http://localhost:8095`` locally,
            ``https://<your-configuration-backend>`` in k8s).
        FEATURE_FLAG_SERVICE_ID: Identifier sent as ``x-service-id`` header.
            Must match a value in configuration-backend's ``Service`` enum
            (e.g. ``agentic-ingestion``).
        FEATURE_FLAG_CACHE_TTL_MS: TTL for the in-process flag cache in
            milliseconds. Defaults to 30 000 ms (30 s).
    """

    CONFIGURATION_BACKEND_URL: str | None = None
    FEATURE_FLAG_SERVICE_ID: str | None = None
    FEATURE_FLAG_CACHE_TTL_MS: int = 30_000

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )
