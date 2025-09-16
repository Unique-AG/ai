from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE = """
This is the message that will be sent to the sub-agent.
""".strip()


class SubAgentToolConfig(BaseToolConfig):
    model_config = get_configuration_dict()

    name: str = "default_name"
    assistant_id: str = ""
    chat_id: str | None = None
    reuse_chat: bool = True
    tool_description_for_system_prompt: str = ""
    tool_description: str = ""
    param_description_sub_agent_user_message: str = (
        DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE
    )
    tool_format_information_for_system_prompt: str = ""

    tool_description_for_user_prompt: str = ""
    tool_format_information_for_user_prompt: str = ""

    poll_interval: float = 1.0
    max_wait: float = 120.0
