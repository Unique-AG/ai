from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlagSettings(BaseSettings):
    """Env-var settings for :class:`FeatureFlagClient`.

    ``CONFIGURATION_BACKEND_URL`` and ``FEATURE_FLAG_SERVICE_ID`` are required;
    :meth:`FeatureFlagClient.from_settings` raises ``ValueError`` if either is absent.
    """

    CONFIGURATION_BACKEND_URL: str | None = None
    FEATURE_FLAG_SERVICE_ID: str | None = None
    FEATURE_FLAG_CACHE_TTL_MS: int = 30_000

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )
