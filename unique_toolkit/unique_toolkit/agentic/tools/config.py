from enum import StrEnum
from typing import Annotated, Any, Generic, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    Field,
    ValidationInfo,
    field_serializer,
    model_validator,
)
from typing_extensions import TypeVar

from unique_toolkit._common.pydantic.rjsf_tags import (
    RJSFMetaTag,
)
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool_build_payload import normalize_tool_build_payload

ToolConfigModel = TypeVar(
    "ToolConfigModel", bound=BaseToolConfig, default=BaseToolConfig
)
ToolTypeType = TypeVar("ToolTypeType", bound=str, default=str)


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


class ToolBuildConfig(BaseModel, Generic[ToolConfigModel, ToolTypeType]):
    model_config = get_configuration_dict()
    """Main tool configuration"""

    name: Annotated[str, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    tool_type: Annotated[ToolTypeType, RJSFMetaTag.SpecialWidget.hidden()]

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

    is_enabled: Annotated[bool, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default=True
    )

    is_sub_agent: Annotated[bool, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default=False,
        validation_alias=AliasChoices("is_sub_agent", "is_subagent", "isSubAgent"),
    )

    configuration: ToolConfigModel = Field(
        default_factory=lambda: ToolConfigModel(),
    )

    @model_validator(mode="before")
    def initialize_config_based_on_tool_name(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> Any:
        """Delegate wire-format normalization to ``tool_build_payload`` (factory lives there)."""
        if not isinstance(value, dict):
            return value
        return normalize_tool_build_payload(value)

    @field_serializer("configuration")
    def serialize_config(self, value: ToolConfigModel) -> dict[str, Any]:
        return value.__class__.model_dump(value)


if __name__ == "__main__":
    from unique_toolkit.agentic.tools.factory import ToolFactory
    from unique_toolkit.agentic.tools.tool import Tool

    class MyConfig(BaseToolConfig):
        a: int = 1

    class MyToolBuildConfig(ToolBuildConfig[MyConfig, Literal["MyTool"]]):
        name: str = Field(default="MyTool")
        tool_type: Literal["MyTool"] = Field(default="MyTool")

    class MyTool(Tool[MyConfig]):
        def __init__(self, name: str, settings: MyToolBuildConfig) -> None:
            super().__init__(name, settings)

        def execute(self, input: str) -> str:
            return "Hello, world!"

    ToolFactory.register_tool(MyTool, MyConfig)

    test = MyToolBuildConfig(configuration=MyConfig(a=1))
