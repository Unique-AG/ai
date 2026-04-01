from typing import Annotated

from pydantic import BeforeValidator, Field
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

    def __init__(self, *, value: list[str] | bool):
        self._value = value

    def is_enabled(self, *, company_id: str | None = None) -> bool:
        """Check if the feature is enabled for the given company.

        Args:
            company_id: The company ID to check. Required if flag is a list.

        Returns:
            True if the feature is enabled, False otherwise.
        """

        if isinstance(self._value, bool):
            return self._value

        if isinstance(self._value, list):
            return company_id in self._value if company_id else False

        return False

    def __repr__(self) -> str:
        return f"FeatureFlag({self._value})"


def parse_feature_flag(v: FeatureFlag | str | bool | list[str]) -> FeatureFlag:
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
            return FeatureFlag(value=True)
        elif v_lower in ("false", "0", "no", ""):
            return FeatureFlag(value=False)
        else:
            # Comma-separated company IDs
            return FeatureFlag(value=[id.strip() for id in v.split(",") if id.strip()])

    if isinstance(v, bool):
        return FeatureFlag(value=v)

    if isinstance(v, list):
        return FeatureFlag(value=v)

    # Default to disabled (this handles default factory functions too)
    return FeatureFlag(value=False)


ValidatedFeatureFlag = Annotated[FeatureFlag, BeforeValidator(parse_feature_flag)]


class _UniqueToolkitFeatureFlags(BaseSettings):
    un_18894_freeze_unique_settings: ValidatedFeatureFlag = Field(
        default=FeatureFlag(value=False),
        frozen=True,
        description="Freeze unique settings (UN-18894)",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="FEATURE_FLAG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
    )


UNIQUE_TOOLKIT_FEATURE_FLAGS = _UniqueToolkitFeatureFlags()
