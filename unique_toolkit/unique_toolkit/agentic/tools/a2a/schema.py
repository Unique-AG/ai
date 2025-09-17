from pydantic import BaseModel

from unique_toolkit.agentic.tools.schemas import ToolCallResponse


class SubAgentToolInput(BaseModel):
    user_message: str


class SubAgentToolCallResponse(ToolCallResponse):
    assistant_message: str


class SubAgentShortTermMemorySchema(BaseModel):
    chat_id: str
