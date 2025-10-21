from pydantic import Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE = """
This is the message that will be sent to the sub-agent.
""".strip()


class SubAgentToolConfig(BaseToolConfig):
    model_config = get_configuration_dict()

    assistant_id: str = Field(
        default="",
        description="The unique identifier of the assistant to use for the sub-agent.",
    )
    chat_id: str | None = Field(
        default=None,
        description="The chat ID to use for the sub-agent conversation. If None, a new chat will be created.",
    )
    reuse_chat: bool = Field(
        default=True,
        description="Whether to reuse the existing chat or create a new one for each sub-agent call.",
    )
    use_sub_agent_references: bool = Field(
        default=True,
        description="Whether this sub agent's references should be used in the main agent's response.",
    )

    tool_description_for_system_prompt: str = Field(
        default="",
        description="Description of the tool that will be included in the system prompt.",
    )
    tool_description: str = Field(
        default="",
        description="Description of the tool that will be included in the tools sent to the model.",
    )
    param_description_sub_agent_user_message: str = Field(
        default=DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE,
        description="Description of the user message parameter that will be sent to the model.",
    )
    tool_format_information_for_system_prompt: str = Field(
        default="",
        description="Format information that will be included in the system prompt to guide response formatting.",
    )
    tool_description_for_user_prompt: str = Field(
        default="",
        description="Description of the tool that will be included in the user prompt.",
    )
    tool_format_information_for_user_prompt: str = Field(
        default="",
        description="Format information that will be included in the user prompt to guide response formatting.",
    )

    poll_interval: float = Field(
        default=1.0,
        description="Time interval in seconds between polling attempts when waiting for sub-agent response.",
    )
    max_wait: float = Field(
        default=120.0,
        description="Maximum time in seconds to wait for the sub-agent response before timing out.",
    )
