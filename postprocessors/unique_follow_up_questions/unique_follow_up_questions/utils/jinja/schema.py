from datetime import date, datetime
from typing import Annotated, Any

from jinja2 import Template
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    WrapSerializer,
)
from unique_toolkit.agentic.tools.tool import Tool


class Jinja2PromptParams(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    def render_template(self, template: str) -> str:
        params = self.model_dump(exclude_none=True, mode="json")

        return Template(template, lstrip_blocks=True).render(**params)


class ToolPromptParams(Jinja2PromptParams):
    name: str
    tool_description_for_system_prompt: str = ""
    tool_format_information_for_system_prompt: str = ""
    tool_format_reminder_for_user_prompt: str = ""

    @classmethod
    def from_tool(cls, tool: Tool) -> "ToolPromptParams":
        return cls(
            name=tool.name,
            tool_description_for_system_prompt=tool.tool_description_for_system_prompt(),
            tool_format_information_for_system_prompt=tool.tool_format_information_for_system_prompt(),
            tool_format_reminder_for_user_prompt=tool.tool_format_reminder_for_user_prompt(),
        )


def serialize_iso8601_date(v: Any, handler: SerializerFunctionWrapHandler) -> str:
    if isinstance(v, date):
        return v.isoformat()
    return handler(v)


ISO8601Date = Annotated[
    date,
    WrapSerializer(serialize_iso8601_date, return_type=str),
]


class AgentSystemPromptParams(Jinja2PromptParams):
    info_cutoff_at: ISO8601Date | None
    current_date: ISO8601Date = Field(default_factory=lambda: datetime.now().date())
    tools: list[ToolPromptParams]
    used_tools: list[ToolPromptParams]
    add_citation_appendix: bool = True
    max_tools_per_iteration: int
    max_loop_iterations: int
    current_iteration: int


class AgentUserPromptParams(Jinja2PromptParams):
    user_prompt: str
