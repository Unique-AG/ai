"""The module configuration that assigns MCP servers to a space.

The platform looks for `mcpTool` and `mcpServerId` on each stored tool entry
when the space is saved, and creates the space's MCP server assignments from
them. `ToolBuildConfig` has neither field and drops both, so these models are
deliberately separate from it.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class McpToolMarker(BaseModel):
    """The nested `configuration` of one MCP tool entry."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mcp_tool: Literal[True] = True
    mcp_server_id: str


class ModuleTool(BaseModel):
    """One tool entry. `name` is the tool's name on the MCP server."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    is_enabled: bool = True
    configuration: McpToolMarker


class ModuleConfiguration(BaseModel):
    """Flat module configuration.

    Keep it flat. When the stored object carries both `space` and `agent`, the
    platform reads `space.tools` instead of `tools`.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    language_model: str
    tools: list[ModuleTool] = Field(default_factory=list)


def example_configuration() -> ModuleConfiguration:
    """The configuration shipped as `module_configuration.example.json`.

    Replace the server ids with the ids of your own MCP servers, and the tool
    names with names those servers advertise.
    """
    return ModuleConfiguration(
        language_model="AZURE_GPT_4o_2024_1120",
        tools=[
            ModuleTool(
                name="jira_search",
                configuration=McpToolMarker(mcp_server_id="<atlassian-mcp-server-id>"),
            ),
            ModuleTool(
                name="search_repositories",
                configuration=McpToolMarker(mcp_server_id="<github-mcp-server-id>"),
            ),
        ],
    )


if __name__ == "__main__":
    import json

    # Dump with `by_alias=True`: the platform reads the camelCase keys.
    print(json.dumps(example_configuration().model_dump(by_alias=True), indent=2))
