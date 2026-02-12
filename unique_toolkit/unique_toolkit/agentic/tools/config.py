from enum import StrEnum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    ValidationInfo,
    computed_field,
    field_serializer,
    model_validator,
)

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class ToolIcon(StrEnum):
    ANALYTICS = "IconAnalytics"
    BOOK = "IconBook"
    FOLDERDATA = "IconFolderData"
    INTEGRATION = "IconIntegration"
    TEXT_COMPARE = "IconTextCompare"
    WORLD = "IconWorld"
    QUICK_REPLY = "IconQuickReply"
    CHAT_PLUS = "IconChatPlus"
    TELESCOPE = "IconTelescope"
    CHART_BAR = "IconChartBar"


class ToolSelectionPolicy(StrEnum):
    """Determine the usage policy of tools."""

    FORCED_BY_DEFAULT = "ForcedByDefault"
    ON_BY_DEFAULT = "OnByDefault"
    BY_USER = "ByUser"


def handle_undefined_icon(value: Any) -> ToolIcon:
    try:
        if isinstance(value, str):
            return ToolIcon(value)
        else:
            return ToolIcon.BOOK
    except ValueError:
        return ToolIcon.BOOK


class ToolBuildConfig(BaseModel):
    model_config = get_configuration_dict()
    """Main tool configuration"""

    name: str
    configuration: BaseToolConfig
    display_name: str = ""
    icon: Annotated[ToolIcon, BeforeValidator(handle_undefined_icon)] = Field(
        default=ToolIcon.BOOK,
        description="The icon name that will be used to display the tool in the user interface.",
    )
    selection_policy: ToolSelectionPolicy = Field(
        default=ToolSelectionPolicy.BY_USER,
    )
    is_exclusive: bool = Field(
        default=False,
        description="This tool must be chosen by the user and no other tools are used for this iteration.",
    )

    is_enabled: bool = Field(default=True)

    @computed_field
    @property
    def is_sub_agent(self) -> bool:
        """Deprecated. Use name == 'SubAgentTool' instead."""
        return self.name == "SubAgentTool"

    @model_validator(mode="before")
    def initialize_config_based_on_tool_name(
        cls,
        value: dict[str, Any],
        info: ValidationInfo,
    ) -> Any:
        """Check the given values for."""
        if not isinstance(value, dict):
            return value

        is_mcp_tool = value.get("mcp_source_id", "") != ""
        mcp_configuration = value.get("configuration", {})

        # Import at runtime to avoid circular imports
        from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig

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

        if (
            value.get("isSubAgent") or value.get("is_sub_agent") or False
        ):  # TODO: This is an extra special case which we should avoid
            from unique_toolkit.agentic.tools.a2a import ExtendedSubAgentToolConfig

            value["name"] = "SubAgentTool"
            config = ExtendedSubAgentToolConfig.model_validate(configuration)
        elif isinstance(configuration, dict):
            # Local import to avoid circular import at module import time
            from unique_toolkit.agentic.tools.factory import ToolFactory

            config = ToolFactory.build_tool_config(
                value["name"],
                **configuration,
            )
        else:
            # Check that the type of config matches the tool name
            from unique_toolkit.agentic.tools.factory import ToolFactory

            assert isinstance(
                configuration,
                ToolFactory.tool_config_map[value["name"]],  # type: ignore
            )
            config = configuration
        value["configuration"] = config
        return value

    @field_serializer("configuration")
    def serialize_config(self, value: BaseToolConfig) -> dict[str, Any]:
        return value.__class__.model_dump(value)
