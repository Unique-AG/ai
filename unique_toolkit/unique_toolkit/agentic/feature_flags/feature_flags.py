from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlag:
    """A feature flag that can be enabled globally or for specific company IDs.

    Examples:
        >>> flag = FeatureFlag(True)
        >>> flag.is_enabled("any_company")
        True

        >>> flag = FeatureFlag(["company1", "company2"])
        >>> flag.is_enabled("company1")
        True
        >>> flag.is_enabled("company3")
        False
    """

    def __init__(self, value: list[str] | bool):
        self.value = value

    def is_enabled(self, company_id: str | None = None) -> bool:
        """Check if the feature is enabled for the given company.

        Args:
            company_id: The company ID to check. Required if flag is a list.

        Returns:
            True if the feature is enabled, False otherwise.
        """

        if isinstance(self.value, bool):
            return self.value

        if isinstance(self.value, list):
            return company_id in self.value if company_id else False

        return False

    def __repr__(self) -> str:
        return f"FeatureFlag({self.value})"


class FeatureFlags(BaseSettings):
    """Feature flags loaded from environment variables.

    Environment variables are automatically loaded based on field names.
    For example, `enable_new_answers_ui_un_14411` will be loaded from
    `FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411` (with the env_prefix).

    Usage:
        >>> flags = FeatureFlags()
        >>> # Check if feature is enabled for a company
        >>> flags.enable_new_answers_ui_un_14411.is_enabled("company123")
        >>> # Check global enablement
        >>> bool(flags.enable_elicitation_un_15809)
    """

    enable_new_answers_ui_un_14411: FeatureFlag = Field(
        default=FeatureFlag([]),
        description="Enable new answers UI (UN-14411)",
    )

    enable_elicitation_un_15809: FeatureFlag = Field(
        default=FeatureFlag(False),
        description="Enable elicitation (UN-15809)",
    )

    feature_flag_enable_html_rendering_un_15131: str = Field(
        default="",
        description="Enable HTML rendering for code interpreter files (UN-15131). Can be 'true' or comma-separated company IDs.",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="FEATURE_FLAG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator(
        "enable_new_answers_ui_un_14411", "enable_elicitation_un_15809", mode="before"
    )
    @classmethod
    def parse_feature_flag(cls, v: Any) -> FeatureFlag:
        """Parse all feature flag fields from environment variables.

        Args:
            v: Can be a string ("true", "false", or comma-separated IDs),
               a boolean, a list of IDs, or already a FeatureFlag instance.

        Returns:
            A FeatureFlag instance.
        """
        if isinstance(v, FeatureFlag):
            return v

        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in ("true", "1", "yes"):
                return FeatureFlag(True)
            elif v_lower in ("false", "0", "no", ""):
                return FeatureFlag(False)
            else:
                # Comma-separated company IDs
                return FeatureFlag([id.strip() for id in v.split(",") if id.strip()])

        if isinstance(v, bool):
            return FeatureFlag(v)

        if isinstance(v, list):
            return FeatureFlag(v)

        # Default to disabled (this handles default factory functions too)
        return FeatureFlag(False)

    def is_html_rendering_enabled(self, company_id: str | None = None) -> bool:
        """Check if HTML rendering is enabled for the given company."""
        value = self.feature_flag_enable_html_rendering_un_15131
        return value.lower() == "true" or bool(
            company_id and company_id in [id.strip() for id in value.split(",")]
        )


# Initialize once at module load - import this where needed
feature_flags = FeatureFlags()
