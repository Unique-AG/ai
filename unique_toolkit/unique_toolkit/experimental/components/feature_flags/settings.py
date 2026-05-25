from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlagSettings(BaseSettings):
    """Env-var settings for :class:`FeatureFlagClient`.

    ``CONFIGURATION_BACKEND_URL`` and ``FEATURE_FLAG_SERVICE_ID`` are required;
    :meth:`FeatureFlagClient.from_settings` raises ``ValueError`` if either is absent.
    """

    configuration_backend_url: str | None = Field(
        None, validation_alias="CONFIGURATION_BACKEND_URL"
    )
    service_id: str | None = Field(None, validation_alias="FEATURE_FLAG_SERVICE_ID")
    cache_ttl_ms: int = Field(30_000, validation_alias="FEATURE_FLAG_CACHE_TTL_MS")

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )
