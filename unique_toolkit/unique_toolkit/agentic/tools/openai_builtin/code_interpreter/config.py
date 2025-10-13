from pydantic import Field

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

Instructions for displaying images and files in the chat:
Once files are generated in the `/mnt/data` folder you MUST reference them in the chat using markdown syntax in order to display them in the chat.

- If you want to display an image, use the following syntax: `![Image Name](sandbox:/mnt/data/<filename>)`
    - Images will be converted and shown in the chat.
    - Do NOT display an extra download link for images a part from the markdown above.
    - Not using markdown syntax will FAIL to show images to the user. 
    - YOU MUST use the syntax above to display images, otherwise the image will not be displayed in the chat.
    - For displaying a link to a file, use the following syntax: `[filename](sandbox:/mnt/data/<filename>)`
        - Files are converted to references the user can click on to download the file

You MUST always use this syntax, otherwise the files will not be displayed in the chat.
""".strip()

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT = ""

DEFAULT_TOOL_FORMAT_INFORMATION_FOR_USER_PROMPT = ""

DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT = ""


class OpenAICodeInterpreterConfig(BaseToolConfig):
    upload_files_in_chat: bool = Field(default=True)

    tool_description: str = DEFAULT_TOOL_DESCRIPTION
    tool_description_for_system_prompt: str = DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT
    tool_format_information_for_system_prompt: str = (
        DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT
    )
    tool_description_for_user_prompt: str = DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT
    tool_format_information_for_user_prompt: str = (
        DEFAULT_TOOL_FORMAT_INFORMATION_FOR_USER_PROMPT
    )

    expires_after_minutes: int = 20
    use_auto_container: bool = False


ToolFactory.register_tool_config(
    OpenAIBuiltInToolName.CODE_INTERPRETER, OpenAICodeInterpreterConfig
)
