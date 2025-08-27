from enum import StrEnum
from typing import TYPE_CHECKING, Any

import humps
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    model_validator,
)
from pydantic.alias_generators import to_camel
from pydantic.fields import ComputedFieldInfo, FieldInfo

if TYPE_CHECKING:
    # Import BaseToolConfig after model definition to avoid circular imports
    from unique_toolkit.tools.mcp.models import MCPToolConfig
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
    configuration: "BaseToolConfig"
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

        is_mcp_tool = value.get("mcp_source_id", "") != ""
        mcp_configuration = value.get("configuration", {})
        if (
            isinstance(mcp_configuration, MCPToolConfig)
            and mcp_configuration.mcp_source_id
        ):
            return value
        if is_mcp_tool:
            # For MCP tools, skip ToolFactory validation
            # Configuration can remain as a dict
            return value

        configuration = value.get("configuration", {})
        if isinstance(configuration, dict):
            # Local import to avoid circular import at module import time
            from unique_toolkit.tools.factory import ToolFactory

            config = ToolFactory.build_tool_config(
                value["name"],
                **configuration,
            )
        else:
            # Check that the type of config matches the tool name
            from unique_toolkit.tools.factory import ToolFactory

            assert isinstance(
                configuration,
                ToolFactory.tool_config_map[value["name"]],  # type: ignore
            )
            config = configuration
        value["configuration"] = config
        return value


# Import BaseToolConfig after model definition to avoid circular imports
from unique_toolkit.tools.mcp.models import MCPToolConfig
from unique_toolkit.tools.schemas import BaseToolConfig

# Update the forward references
ToolBuildConfig.model_rebuild()
