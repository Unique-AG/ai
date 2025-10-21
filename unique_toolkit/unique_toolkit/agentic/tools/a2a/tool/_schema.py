from pydantic import BaseModel


class SubAgentToolInput(BaseModel):
    user_message: str


class SubAgentShortTermMemorySchema(BaseModel):
    chat_id: str
