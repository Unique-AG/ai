from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_TOOL_DESCRIPTION = "Use this tool to run python code, e.g to generate plots, process excel files, perform calculations, etc."

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = """
Use this tool to run python code, e.g to generate plots, process excel files, perform calculations, etc.
Instructions:
- All files uploaded to the chat are available in the code interpreter under the path `/mnt/data/<filename>
- All files generated through code should be saved in the `/mnt/data` folder

CRUCIAL Instructions for displaying images and files in the chat:
Once files are generated in the `/mnt/data` folder you MUST reference them in the chat using markdown syntax in order to display them in the chat.

WHENEVER you reference a generated file, you MUST use the following format:
```
**Descriptive Title of Graph/Chart/File** (<- linebreak is important) (You must choose a good user friendly title, Other markdown syntax such as `#` can be used too)
[*Generating your {Graph/Chart/File}…*](sandbox:/mnt/data/<filename>)
```
IMPORTANT: Do NOT append a leading `!` even when displaying an image.
Always use a line break between the title and the markdown!

- Files with image file extensions are displayed directly in the chat, while other file extensions are shown as download links.
- Not using syntax above will FAIL to show images to the user. 
- YOU MUST use the syntax above to display images, otherwise the image will not be displayed in the chat.
- Only the following file types are allowed to be uploaded to the platform, anything else will FAIL: PDF, DOCX, XLSX, PPTX, CSV, HTML, MD, TXT, PNG, JPG, JPEG.

You MUST always use this syntax, otherwise the files will not be displayed in the chat.
""".strip()

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT = ""

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_USER_PROMPT = ""

DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT = ""


class OpenAICodeInterpreterConfig(BaseToolConfig):
    upload_files_in_chat_to_container: bool = Field(
        default=True,
        description="If set, the files uploaded to the chat will be uploaded to the container where code is executed.",
    )

    tool_description: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="The description of the tool that will be sent to the model.",
    )
    tool_description_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="The description of the tool that will be included in the system prompt.",
    )
    tool_format_information_for_system_prompt: SkipJsonSchema[str] = Field(
        # Since the tool is executed in Azure, it's not always possible to have dynamic format information
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
        description="The format information of the tool that will be included in the system prompt.",
    )
    tool_description_for_user_prompt: SkipJsonSchema[str] = (
        Field(  # At the moment, this is not appended to the user prompt
            default=DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT,
            description="The description of the tool that will be included in the user prompt.",
        )
    )
    tool_format_information_for_user_prompt: SkipJsonSchema[str] = (
        Field(  # At the moment, this is not appended to the user prompt
            default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_USER_PROMPT,
            description="The format information of the tool that will be included in the user prompt.",
        )
    )

    expires_after_minutes: int = Field(
        default=20,
        description="The number of minutes after which the container will be deleted.",
    )
    use_auto_container: bool = Field(
        default=False,
        description="If set, use the `auto` container setting from OpenAI. Note that this will recreate the container on each call.",
    )


ToolFactory.register_tool_config(
    OpenAIBuiltInToolName.CODE_INTERPRETER, OpenAICodeInterpreterConfig
)
