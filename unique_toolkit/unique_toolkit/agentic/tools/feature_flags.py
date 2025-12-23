import os

from pydantic import BaseModel, Field


class FeatureFlags(BaseModel):
    """Centralized feature flags passed from orchestrator to all tools.
    """

    feature_flag_enable_new_answers_ui: bool = Field(
        default=False,
        description="Enable new answers UI (UN-14411)",
    )

    @classmethod
    def from_env(cls, company_id: str) -> "FeatureFlags":
        """Parse feature flags from environment variables.

        Args:
            company_id: The company ID to check for per-company feature flags.

        Returns:
            FeatureFlags instance with all flags evaluated.
        """
        new_ui_value = os.getenv("FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411", "")
        feature_flag_enable_new_answers_ui = (
            new_ui_value.lower() == "true" or company_id in new_ui_value.split(",")
        )
        return cls(feature_flag_enable_new_answers_ui=feature_flag_enable_new_answers_ui)

