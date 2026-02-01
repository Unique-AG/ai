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

    feature_flag_enable_full_history_with_content_and_tools_un_15966: str = Field(
        default="",
        description="When enabled, it retains the tool calls in the history",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
    )

    def is_new_answers_ui_enabled(self, company_id: str | None = None) -> bool:
        """Check if new answers UI is enabled for the given company."""
        value = self.feature_flag_enable_new_answers_ui_un_14411
        return value.lower() == "true" or bool(
            company_id and company_id in [id.strip() for id in value.split(",")]
        )

    def is_full_history_with_content_and_tools_enabled(
        self, company_id: str | None = None
    ) -> bool:
        """Check if full_history_with_content_and_tools is enabled for the given company."""
        value = self.feature_flag_enable_full_history_with_content_and_tools_un_15966
        return value.lower() == "true" or bool(
            company_id and company_id in [id.strip() for id in value.split(",")]
        )


# Initialize once at module load - import this where needed
feature_flags = FeatureFlags()
