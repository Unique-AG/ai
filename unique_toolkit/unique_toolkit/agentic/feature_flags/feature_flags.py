from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    """Feature flags loaded from environment variables.

    Environment variables are automatically loaded based on field names.
    For example, `feature_flag_enable_new_answers_ui_un_14411` will be loaded from
    `FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411`.
    """

    feature_flag_enable_new_answers_ui_un_14411: str = Field(
        default="",
        description="Enable new answers UI (UN-14411). Can be 'true' or comma-separated company IDs.",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
    )

    def is_new_answers_ui_enabled(self, company_id: str) -> bool:
        """Check if new answers UI is enabled for the given company."""
        value = self.feature_flag_enable_new_answers_ui_un_14411
        return value.lower() == "true" or company_id in value.split(",")


# Initialize once at module load - import this where needed
feature_flags = FeatureFlags()
