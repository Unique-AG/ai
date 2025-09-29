from enum import StrEnum

from pydantic import BaseModel

from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_PARAM_DESCRIPTION_SUB_AGENT_USER_MESSAGE = """
This is the message that will be sent to the sub-agent.
""".strip()


class ResponseDisplayMode(StrEnum):
    HIDDEN = "hidden"
    DETAILS_OPEN = "details_open"
    DETAILS_CLOSED = "details_closed"


class SubAgentToolDisplayConfig(BaseModel):
    model_config = get_configuration_dict()

    mode: ResponseDisplayMode = ResponseDisplayMode.HIDDEN
    remove_from_history: bool = True


class SubAgentEvaluationConfig(BaseModel):
    model_config = get_configuration_dict()
    display_evalution: bool = True


class SubAgentToolConfig(BaseToolConfig):
    model_config = get_configuration_dict()

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

    response_display_config: SubAgentToolDisplayConfig = SubAgentToolDisplayConfig()
    evaluation_config: SubAgentEvaluationConfig = SubAgentEvaluationConfig()
