"""Configuration of the ProjectChatSearch tool."""

from __future__ import annotations

from pydantic import Field
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_project_chat_search.prompts import SYSTEM_PROMPT, TOOL_DESCRIPTION


class ProjectChatSearchConfig(BaseToolConfig):
    """Settings of the ProjectChatSearch tool."""

    tool_description: str = Field(
        default=TOOL_DESCRIPTION,
        description="Description of the tool shown to the model.",
    )
    tool_description_for_system_prompt: str = Field(
        default=SYSTEM_PROMPT,
        description="Guidance added to the system prompt when the tool is available.",
    )
    search_limit: int = Field(
        default=10, ge=1, le=50, description="Excerpts returned by one search."
    )
    chunks_per_page: int = Field(
        default=10, ge=1, le=50, description="Excerpts per page when reading a chat."
    )
    recent_limit: int = Field(
        default=10, ge=1, le=20, description="Chats per page when listing recent chats."
    )
    max_page: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Highest page the model may ask for; each page is one more API call.",
    )
    max_tokens: int = Field(
        default=4000,
        ge=200,
        description="Token budget of one tool response; whole excerpts beyond it are left out.",
    )
    chat_url_template: str = Field(
        default="/chat/{chat_id}",
        description=(
            "Link of a cited chat. The relative default opens on the current app "
            "host; use an absolute URL for surfaces on another host."
        ),
    )
