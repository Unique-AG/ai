from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_toolkit.app.find_env_file import find_env_file


class FeatureFlagSettings(BaseSettings):
    """Env-var settings for :class:`FeatureFlagClient`.

    ``CONFIGURATION_BACKEND_URL`` and ``FEATURE_FLAG_SERVICE_ID`` are required;
    :meth:`FeatureFlagClient.from_settings` raises ``ValueError`` if either is absent.
    """

    configuration_backend_url: str | None = None
    feature_flag_service_id: str | None = None
    feature_flag_cache_ttl_ms: int = 5_000

    @field_validator(
        "configuration_backend_url", "feature_flag_service_id", mode="before"
    )
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
        env_file=find_env_file(".env", required=False),
        env_file_encoding="utf-8",
    )
