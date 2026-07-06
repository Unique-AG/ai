import logging
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Any, Generic

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    SerializeAsAny,
    ValidationInfo,
    model_validator,
)
from typing_extensions import TypeVar

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseToolConfig, default=BaseToolConfig)


def _ensure_base_tool_config(value: dict[str, Any]) -> None:
    """Make configuration parseable; disabled/demoted tools are never built at runtime."""
    configuration = value.get("configuration")
    if not isinstance(configuration, BaseToolConfig):
        value["configuration"] = BaseToolConfig()


def _non_empty_str(value: dict[str, Any], snake_key: str, camel_key: str) -> str:
    raw = value.get(snake_key, value.get(camel_key, ""))
    if raw is None:
        return ""
    return str(raw)


def _is_mcp_tool_payload(value: dict[str, Any]) -> bool:
    if _non_empty_str(value, "mcp_source_id", "mcpSourceId"):
        return True

    configuration = value.get("configuration", {})
    if isinstance(configuration, dict):
        if _non_empty_str(configuration, "mcp_source_id", "mcpSourceId"):
            return True
    return False


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


class ToolBuildConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict()
    """Main tool configuration"""

    name: str
    configuration: SerializeAsAny[T]
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
    is_sub_agent: bool = False

    is_enabled: bool = Field(default=True)

    config_error: str | None = Field(
        default=None,
        exclude=True,
        description=(
            "Set when this tool's stored configuration failed to resolve and was "
            "demoted to a disabled BaseToolConfig fallback. None for tools that are "
            "valid, including tools that are deliberately disabled."
        ),
    )

    @model_validator(mode="before")
    def initialize_config_based_on_tool_name(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> Any:
        """Validate and resolve tool configuration based on tool type and name.

        Both enabled and disabled tools resolve to their concrete config type when
        the stored configuration is valid, so downstream consumers that key off the
        tool name keep seeing the expected config type regardless of the enabled
        flag. A tool whose configuration is invalid is demoted to disabled with a
        BaseToolConfig fallback instead of raising.
        """
        if not isinstance(value, dict):
            return value

        is_mcp_tool = _is_mcp_tool_payload(value)
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

        try:
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
                    ToolFactory.tool_config_map[value["name"]],  # pyright: ignore[reportArgumentType]
                )
                config = configuration
        except Exception:
            tool_name = value.get("name", "<unknown>")
            logger.warning(
                "Tool '%s' has invalid configuration and will be disabled.",
                tool_name,
                exc_info=True,
            )
            value["is_enabled"] = False
            value["isEnabled"] = False
            value["config_error"] = f"Tool '{tool_name}' has invalid configuration."
            _ensure_base_tool_config(value)
            return value

        value["configuration"] = config
        return value


def collect_tool_configuration_errors(
    tools: Sequence["ToolBuildConfig[Any]"],
) -> list[str]:
    """Return the config_error message for every tool demoted due to an invalid config.

    `initialize_config_based_on_tool_name` never raises: a tool whose stored
    configuration is invalid is silently disabled with a BaseToolConfig fallback so
    that one broken tool cannot take down the whole space. Callers that need to
    surface these failures instead of ignoring them (e.g. to fail a chat request the
    way an invalid configuration used to) can use this helper to recover the list.
    """
    return [tool.config_error for tool in tools if tool.config_error]
