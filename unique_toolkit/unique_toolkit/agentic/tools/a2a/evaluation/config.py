from pathlib import Path

from pydantic import BaseModel, Field

from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentType,
)

DEFAULT_EVALUATION_SYSTEM_MESSAGE_TEMPLATE = """
You are a through and precise summarization model.
You will receive a list of "assessments" of one or more agent(s) response(s).
Your task is to give a brief summary (1-10 sentences) of the received assessments, following the following guidelines:
1. You must NOT in ANY case state a fact that is not stated in the given assessments.
2. You must focus first and foremost on the failing assessments, labeled `RED` below.
3. You must mention each agent's name when summarizing its list of assessments.
4. You must NOT use any markdown formatting in your response as this will FAIL to render in the chat frontend.
""".strip()

with open(Path(__file__).parent / "summarization_user_message.j2", "r") as file:
    DEFAULT_SUMMARIZATION_USER_MESSAGE_TEMPLATE = file.read().strip()


class SubAgentEvaluationServiceConfig(BaseModel):
    model_config = get_configuration_dict()

    assessment_type: ChatMessageAssessmentType = Field(
        default=ChatMessageAssessmentType.COMPLIANCE,
        description="The type of assessment to use in the display.",
    )
    summarization_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)
    summarization_system_message: str = Field(
        default=DEFAULT_EVALUATION_SYSTEM_MESSAGE_TEMPLATE,
        description="The system message template for the summarization model.",
    )
    summarization_user_message_template: str = Field(
        default=DEFAULT_SUMMARIZATION_USER_MESSAGE_TEMPLATE,
        description="The user message template for the summarization model.",
    )


class SubAgentEvaluationConfig(BaseModel):
    model_config = get_configuration_dict()

    include_evaluation: bool = Field(
        default=True,
        description="Whether to include the evaluation in the response.",
    )
