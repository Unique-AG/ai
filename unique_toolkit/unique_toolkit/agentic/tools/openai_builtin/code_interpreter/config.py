from typing import Annotated

from pydantic import Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
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

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = """
Use this tool to run python code, e.g to generate plots, process excel files, perform calculations, etc.

Instructions:

Uploaded and generated files:
- All files uploaded to the chat are available at the path `/mnt/data/<filename>`.
- All files generated through code MUST be saved in the `/mnt/data` folder.

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
- Whenever the user query requires using the python tool, you must always think first about the steps required.
- Use the tool multiple times:
    - You MUST NOT guess anything about the structure of the data / files uploaded. Rather, you MUST perform some data exploration first.
        - Example: User uploads an excel files and asks a question about it. First Read the data, explore the columns, columns types, etc. Then use the tool to answer the user's query.
        In this case, you can simply call the tool multiple times.
        - REMEMBER that you can always read the content of text, csv files if needed. In this case, you MUST always limit the amount of data displayed.
- If a tool step fails, you must recover as much as possible.
- After exhausting all possible solutions without success, inform the user of what was tried and request clarification/help.
""".strip()

# Used when the code-execution fence feature flag (UN-17972) is enabled.
# The frontend derives the artifact title from the filename itself, so the
# LLM no longer needs to produce a markdown heading before the sandbox link.
DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE = """
Use this tool to run python code, e.g to generate plots, process excel files, perform calculations, etc.

Instructions:

Uploaded and generated files:
- All files uploaded to the chat are available at the path `/mnt/data/<filename>`.
- All files generated through code MUST be saved in the `/mnt/data` folder.

CRUCIAL Instructions for displaying images and files in the chat:
- Once files are generated in the `/mnt/data` folder you MUST reference them in the chat using markdown syntax in order to display them in the chat.
WHENEVER you reference a generated file, you MUST use the following format:
```

[*Generating your {Graph/Chart/File}…*](sandbox:/mnt/data/<filename>)

```
IMPORTANT: Do NOT append a leading `!` even when displaying an image.
IMPORTANT: ALWAYS place a blank line before AND after each file reference link so it stands on its own paragraph. Never place a file reference inline within a sentence or as part of a list item.
- Files are displayed as interactive components in the chat — images are shown inline, other files show the filename with an option to view the generating code and download the file.
- Not using syntax above will FAIL to show files to the user.
- YOU MUST use the syntax above to display files, otherwise the file will not be displayed in the chat.
- Only the following file types are allowed to be uploaded to the platform, anything else will FAIL: PDF, DOCX, XLSX, PPTX, CSV, HTML, MD, TXT, PNG, JPG, JPEG.
- You MUST always use this syntax, otherwise the files will not be displayed in the chat.


# Displaying Dataframes/Tables:
- Whenever asked to display a dataframe/table, it is CRITICAL to represent it faithfully as a markdown table in your response.

Handling User Queries:
- Whenever the user query requires using the python tool, you must always think first about the steps required.
- Use the tool multiple times:
    - You MUST NOT guess anything about the structure of the data / files uploaded. Rather, you MUST perform some data exploration first.
        - Example: User uploads an excel files and asks a question about it. First Read the data, explore the columns, columns types, etc. Then use the tool to answer the user's query.
        In this case, you can simply call the tool multiple times.
        - REMEMBER that you can always read the content of text, csv files if needed. In this case, you MUST always limit the amount of data displayed.
- If a tool step fails, you must recover as much as possible.
- After exhausting all possible solutions without success, inform the user of what was tried and request clarification/help.
""".strip()


DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT = ""
DEFAULT_TOOL_DESCRIPTION = "Use this tool to run python code, e.g to generate plots, process excel files, perform calculations, etc."


@register_config()
class OpenAICodeInterpreterConfig(BaseToolConfig):
    upload_files_in_chat_to_container: bool = Field(
        default=True,
        description="If set, the files uploaded to the chat will be uploaded to the container where code is executed.",
    )
    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="The description of the tool that will be included in the system prompt.",
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
    tool_description_for_user_prompt: SkipJsonSchema[str] = (
        Field(  # At the moment, this is not appended to the user prompt
            default=DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT,
            description="The description of the tool that will be included in the user prompt.",
        )
    )
    expires_after_minutes: Annotated[
        int,
        RJSFMetaTag.NumberWidget.updown(min=1, max=20),
    ] = Field(
        default=20,
        ge=1,
        le=20,
        description="Minutes of inactivity after which the container is deleted. Maximum allowed by OpenAI is 20.",
    )
    use_auto_container: bool = Field(
        default=False,
        description="If set, use the `auto` container setting from OpenAI. Note that this will recreate the container on each call.",
    )


@register_config()
class CodeInterpreterExtendedConfig(BaseToolConfig):
    generated_files_config: DisplayCodeInterpreterFilesPostProcessorConfig = Field(
        default=DisplayCodeInterpreterFilesPostProcessorConfig(),
        title="Generated files",
    )

    executed_code_display_config: ShowExecutedCodePostprocessorConfig = Field(
        default=ShowExecutedCodePostprocessorConfig(),
        title="Code display",
    )

    @field_validator("executed_code_display_config", mode="before")
    @classmethod
    def _default_executed_code_display_config(cls, v):
        if v is None:
            return ShowExecutedCodePostprocessorConfig()
        return v

    tool_config: OpenAICodeInterpreterConfig = Field(
        default=OpenAICodeInterpreterConfig(),
        title="Tool",
    )


ToolFactory.register_tool_config(
    OpenAIBuiltInToolName.CODE_INTERPRETER, CodeInterpreterExtendedConfig
)
