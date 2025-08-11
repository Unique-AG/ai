from enum import StrEnum
import humps 
from typing import Any
from pydantic.fields import ComputedFieldInfo, FieldInfo
from pydantic.alias_generators import to_camel
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    model_validator,
)

from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import BaseToolConfig


def field_title_generator(
    title: str,
    info: FieldInfo | ComputedFieldInfo,
) -> str:
    return humps.decamelize(title).replace("_", " ").title()


def model_title_generator(model: type) -> str:
    return humps.decamelize(model.__name__).replace("_", " ").title()


def get_configuration_dict(**kwargs) -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        field_title_generator=field_title_generator,
        model_title_generator=model_title_generator,
        populate_by_name=True,
        protected_namespaces=(),
        **kwargs,
    )


class ToolIcon(StrEnum):
    ANALYTICS = "IconAnalytics"
    BOOK = "IconBook"
    FOLDERDATA = "IconFolderData"
    INTEGRATION = "IconIntegration"
    TEXT_COMPARE = "IconTextCompare"
    WORLD = "IconWorld"
    QUICK_REPLY = "IconQuickReply"
    CHAT_PLUS = "IconChatPlus"


class ToolSelectionPolicy(StrEnum):
    """Determine the usage policy of tools."""

    FORCED_BY_DEFAULT = "ForcedByDefault"
    ON_BY_DEFAULT = "OnByDefault"
    BY_USER = "ByUser"


class ToolBuildConfig(BaseModel):
    model_config = get_configuration_dict()
    """Main tool configuration"""

    name: str
    configuration: BaseToolConfig
    display_name: str = ""
    icon: ToolIcon = ToolIcon.BOOK
    selection_policy: ToolSelectionPolicy = Field(
        default=ToolSelectionPolicy.BY_USER,
    )
    is_exclusive: bool = Field(
        default=False,
        description="This tool must be chosen by the user and no other tools are used for this iteration.",
    )

    is_enabled: bool = Field(default=True)

    @model_validator(mode="before")
    def initialize_config_based_on_tool_name(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> Any:
        """Check the given values for."""
        if not isinstance(value, dict):
            return value

        configuration = value.get("configuration", {})
        if isinstance(configuration, dict):
            config = ToolFactory.build_tool_config(
                value["name"],
                **configuration,
            )
        else:
            # Check that the type of config matches the tool name
            assert isinstance(
                configuration,
                ToolFactory.tool_config_map[value["name"]],  # type: ignore
            )
            config = configuration
        value["configuration"] = config
        return value
