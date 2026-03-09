"""Configuration classes for the OpenAI Hosted Shell tool.

Defines :class:`OpenAIHostedShellConfig` (tool-level settings such as
skills, container mode, and prompt templates) and
:class:`HostedShellExtendedConfig` (the full configuration exposed in
the Unique platform UI, including postprocessor settings).

Skill attachment is configured via two list fields:

* :class:`SkillReferenceConfig` — references a skill previously uploaded
  via the ``/v1/skills`` API.
* :class:`InlineSkillConfig` — embeds a base64-encoded zip bundle that
  is sent inline with each API request (no prior upload needed).
"""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessorConfig,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class SkillReferenceConfig(BaseModel):
    """Reference to a skill previously uploaded via the OpenAI Skills API."""

    model_config = get_configuration_dict()

    skill_id: str = Field(
        description="The ID of the skill to reference (from the OpenAI /v1/skills API).",
    )
    version: str | None = Field(
        default=None,
        description="The version of the skill to use. If None, uses the default version. Can be a positive integer or 'latest'.",
    )


class InlineSkillConfig(BaseModel):
    """An inline skill embedded as a base64-encoded zip bundle.

    The zip must contain a top-level directory with a ``SKILL.md``
    manifest file that includes YAML front matter (delimited by ``---``)
    specifying ``name`` and ``description`` matching the values here.
    """

    model_config = get_configuration_dict()

    name: str = Field(
        description="The name of the inline skill.",
    )
    description: str = Field(
        description="A human-readable description of what the skill does.",
    )
    base64_zip: str = Field(
        description="The base64-encoded zip archive containing the skill files (must include a SKILL.md).",
    )


DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = """
Use this tool to run shell commands in a sandboxed environment with pre-configured skills.

Instructions:

Uploaded and generated files:
- All files uploaded to the chat are available at the path `/mnt/data/<filename>`.
- All files generated through shell commands MUST be saved in the `/mnt/data` folder.

CRUCIAL Instructions for displaying images and files in the chat:
- Once files are generated in the `/mnt/data` folder you MUST reference them in the chat using markdown syntax in order to display them in the chat.
WHENEVER you reference a generated file, you MUST use the following format:
```
**Descriptive Title of Graph/Chart/File**  (linebreak is important. You must choose a good user friendly title, Other markdown syntax such as `#` can be used too)
[*Generating your {Graph/Chart/File}…*](sandbox:/mnt/data/<filename>)
```
IMPORTANT: Do NOT append a leading `!` even when displaying an image.
Always use a line break between the title and the markdown!
- Files with image file extensions are displayed directly in the chat, while other file extensions are shown as download links.
- Not using syntax above will FAIL to show images to the user.
- YOU MUST use the syntax above to display images, otherwise the image will not be displayed in the chat.
- Only the following file types are allowed to be uploaded to the platform, anything else will FAIL: PDF, DOCX, XLSX, PPTX, CSV, HTML, MD, TXT, PNG, JPG, JPEG.
- You MUST always use this syntax, otherwise the files will not be displayed in the chat.

# Displaying Dataframes/Tables:
- Whenever asked to display a dataframe/table, it is CRITICAL to represent it faithfully as a markdown table in your response.

Handling User Queries:
- Whenever the user query requires using the shell tool, you must always think first about the steps required.
- Use the tool multiple times:
    - You MUST NOT guess anything about the structure of the data / files uploaded. Rather, you MUST perform some data exploration first.
        - Example: User uploads an excel files and asks a question about it. First Read the data, explore the columns, columns types, etc. Then use the tool to answer the user's query.
        In this case, you can simply call the tool multiple times.
        - REMEMBER that you can always read the content of text, csv files if needed. In this case, you MUST always limit the amount of data displayed.
- If a tool step fails, you must recover as much as possible.
- After exhausting all possible solutions without success, inform the user of what was tried and request clarification/help.

Skills:
- You have access to pre-configured skills in the shell environment.
- Skills provide specialized instructions and scripts for solving specific types of problems.
- The skill instructions are available in the container. Use them when the user's request matches a skill's purpose.
""".strip()

DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT = ""
DEFAULT_TOOL_DESCRIPTION = "Use this tool to run shell commands with pre-configured skills for specialized data processing and problem solving."


@register_config()
class OpenAIHostedShellConfig(BaseToolConfig):
    """Core configuration for the hosted shell tool.

    Controls container mode (auto vs persistent), attached skills,
    file upload behaviour, and the prompt templates shown to the model.
    """
    skill_references: list[SkillReferenceConfig] = Field(
        default=[],
        description="List of pre-uploaded skills to attach to the shell environment.",
    )
    inline_skills: list[InlineSkillConfig] = Field(
        default=[],
        description="List of inline skills (base64-encoded zip bundles) to attach to the shell environment.",
    )
    upload_files_in_chat_to_container: bool = Field(
        default=True,
        description="If set, the files uploaded to the chat will be made available in the shell environment. "
        "With `container_auto`, files are uploaded via the files API and passed as `file_ids` in the environment. "
        "With persistent containers, files are uploaded directly to the container.",
    )
    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="The description of the tool.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT.split("\n")) / 2)
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="The description of the tool that will be included in the system prompt.",
    )
    tool_description_for_user_prompt: SkipJsonSchema[str] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT,
        description="The description of the tool that will be included in the user prompt.",
    )
    expires_after_minutes: int = Field(
        default=20,
        description="The number of minutes after which the container will be deleted.",
    )
    use_auto_container: bool = Field(
        default=True,
        description="If set, use the `container_auto` environment. When False, a persistent container is created and reused. "
        "Note: Skills (both skill_references and inline_skills) require `container_auto` — they are not supported with persistent containers. "
        "The shell tool currently requires the `gpt-5.4` model.",
    )


@register_config()
class HostedShellExtendedConfig(BaseToolConfig):
    """Full configuration for the hosted shell, including postprocessors.

    This is the top-level config exposed in the Unique platform UI.
    It bundles :class:`OpenAIHostedShellConfig` with display settings
    for generated files and executed commands.
    """
    generated_files_config: DisplayCodeInterpreterFilesPostProcessorConfig = Field(
        default=DisplayCodeInterpreterFilesPostProcessorConfig(),
        title="Generated files",
    )

    executed_command_display_config: ShowExecutedCodePostprocessorConfig = Field(
        default=ShowExecutedCodePostprocessorConfig(),
        title="Command display",
    )

    @field_validator("executed_command_display_config", mode="before")
    @classmethod
    def _default_executed_command_display_config(cls, v):
        if v is None:
            return ShowExecutedCodePostprocessorConfig()
        return v

    tool_config: OpenAIHostedShellConfig = Field(
        default=OpenAIHostedShellConfig(),
        title="Tool",
    )


ToolFactory.register_tool_config(
    OpenAIBuiltInToolName.HOSTED_SHELL, HostedShellExtendedConfig
)
