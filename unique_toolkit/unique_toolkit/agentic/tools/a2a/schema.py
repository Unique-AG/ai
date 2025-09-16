from agentic.tools.schemas import ToolCallResponse
from pydantic import BaseModel


class SubAgentToolInput(BaseModel):
    user_message: str


class SubAgentToolCallResponse(ToolCallResponse):
    assistant_message: str


class SubAgentShortTermMemorySchema(BaseModel):
    chat_id: str
