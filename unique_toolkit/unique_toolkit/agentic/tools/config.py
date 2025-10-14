import json
from enum import StrEnum
from typing import Annotated, Any, Dict

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    ValidationInfo,
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


class ToolSelectionPolicy(StrEnum):
    """Determine the usage policy of tools."""

    FORCED_BY_DEFAULT = "ForcedByDefault"
    ON_BY_DEFAULT = "OnByDefault"
    BY_USER = "ByUser"


def handle_undefinded_icon(value: Any) -> ToolIcon:
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
    icon: Annotated[ToolIcon, BeforeValidator(handle_undefinded_icon)] = Field(
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
    is_sub_agent: bool = False

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

        is_sub_agent_tool = (
            value.get("is_sub_agent") or value.get("isSubAgent") or False
        )

        configuration = value.get("configuration", {})

        if is_sub_agent_tool:
            from unique_toolkit.agentic.tools.a2a import ExtendedSubAgentToolConfig

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

    def model_dump(self) -> Dict[str, Any]:
        """
        Returns a dict representation of the tool config that preserves
        subclass fields from `configuration` by delegating to its own
        model_dump. This prevents `{}` when `configuration` is typed
        as `BaseToolConfig` but holds a subclass instance.
        """
        data: Dict[str, Any] = {
            "name": self.name,
            "configuration": self.configuration.model_dump()
            if self.configuration
            else None,
            "display_name": self.display_name,
            "icon": self.icon,
            "selection_policy": self.selection_policy,
            "is_exclusive": self.is_exclusive,
            "is_sub_agent": self.is_sub_agent,
            "is_enabled": self.is_enabled,
        }
        return data

    def model_dump_json(self) -> str:
        """
        Returns a JSON string representation of the tool config.
        Ensures `configuration` is fully serialized by using the
        subclass's `model_dump_json()` when available.
        """
        config_json = (
            self.configuration.model_dump_json() if self.configuration else None
        )
        config = json.loads(config_json) if config_json else None

        data: Dict[str, Any] = {
            "name": self.name,
            "configuration": config,
            "display_name": self.display_name,
            "icon": self.icon,
            "selection_policy": self.selection_policy,
            "is_exclusive": self.is_exclusive,
            "is_sub_agent": self.is_sub_agent,
            "is_enabled": self.is_enabled,
        }
        return json.dumps(data)
