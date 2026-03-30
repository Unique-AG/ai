"""Minimal LangChain Deep Agent with streaming to the Unique frontend.

This example shows how to wire a LangChain Deep Agent (backed by the
``deepagents`` library) so that every generated token is pushed to the
Unique chat UI via ``Message.create_event_async``.

The structure mirrors ``chat_app_minimal.py`` – it uses the SSE
development loop (``get_event_generator``) and the Unique OpenAI proxy
(``get_langchain_client``) as the underlying model.

Prerequisites:
    pip install deepagents  # or:  uv add deepagents
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import unique_sdk
from typing import Any
from unique_toolkit import LanguageModelName, get_langchain_client
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.streaming import ChatContext

from langchain_core.messages import AIMessageChunk

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph 
    from langgraph.types import StreamMode, Command

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Example tool – replace with your own domain-specific tools
# ---------------------------------------------------------------------------
def get_current_time() -> str:
    """Return the current UTC time as a string."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


async def messages_stream_handler(data: str | Any, 
                                  current_text: str, chat_context: ChatContext, 
                                  send_every_n_tokens: int) -> None:
    
    token, metadata = data
    if not isinstance(token, AIMessageChunk):
        return
    if not token.text:
        return

    current_text += token.text

    if len(current_text) % send_every_n_tokens != 0:
        return

    await unique_sdk.Message.create_event_async(
        user_id=chat_context.user_id,
        company_id=chat_context.company_id,
        **unique_sdk.Message.CreateEventParams(
            chatId=chat_context.chat_id,
            messageId=chat_context.assistant_message_id,
            text=current_text,
        ),
    )

# ---------------------------------------------------------------------------
# Core bridge: stream Deep Agent output to the Unique frontend
# ---------------------------------------------------------------------------
async def stream_deep_agent_to_chat_frontend(
    *,
    agent: CompiledStateGraph,
    user_input: str,
    chat_context: ChatContext,
    send_every_n_tokens: int = 5,
) -> str:
    """Run a Deep Agent and stream its output to the Unique frontend.

    Uses ``stream_mode=["messages", "updates"]`` so we get both
    token-level text (for live UI) and step-level progress (for logging).

    Args:
        agent: A compiled LangGraph agent returned by ``create_deep_agent``.
        user_input: The user's message text.
        chat_context: Identifies the chat / assistant message to update.
        send_every_n_tokens: Throttle – push an event every N tokens.

    Returns:
        The full text of the agent's final response.
    """

    await unique_sdk.Message.modify_async(
        id=chat_context.assistant_message_id,
        chatId=chat_context.chat_id,
        user_id=chat_context.user_id,
        company_id=chat_context.company_id,
        startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore[arg-type]
    )

    full_text = ""

    async for stream_mode, data in agent.astream(
        input={"messages": [{"role": "user", "content": user_input}]},
        stream_mode=["messages", "updates", 'values',  'checkpoints', 'tasks', 'debug', 'messages', 'custom'],
    ):
        if stream_mode == "messages":
            await messages_stream_handler(data, full_text, chat_context, send_every_n_tokens)
        elif stream_mode == "updates":
            logger.info(f"Stream mode: {stream_mode}, data: {data}")
        elif stream_mode == "values":
            logger.info(f"Stream mode: {stream_mode}, data: {data}")
        elif stream_mode == "checkpoints":
            logger.info(f"Stream mode: {stream_mode}, data: {data}")
        elif stream_mode == "tasks":
            logger.info(f"Stream mode: {stream_mode}, data: {data}")
        elif stream_mode == "debug":
            logger.info(f"Stream mode: {stream_mode}, data: {data}")
        elif stream_mode == "custom":
            logger.info(f"Stream mode: {stream_mode}, data: {data}")
        else:
            logger.info(f"Stream mode: {stream_mode}, data: {data}")

    # Persist the final message
    await unique_sdk.Message.modify_async(
        id=chat_context.assistant_message_id,
        chatId=chat_context.chat_id,
        user_id=chat_context.user_id,
        company_id=chat_context.company_id,
        text=full_text,
        completedAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore[arg-type]
    )

    return full_text


# ---------------------------------------------------------------------------
# Main – SSE development loop
# ---------------------------------------------------------------------------
async def main():
    from deepagents import create_deep_agent

    settings = UniqueSettings.from_env_auto_with_sdk_init()

    model = get_langchain_client(
        unique_settings=settings,
        model=LanguageModelName.AZURE_GPT_5_2025_0807,
    )

    agent = create_deep_agent(
        model=model,
        tools=[get_current_time],
        system_prompt="You are a helpful assistant.",
    )

    for event in get_event_generator(
        unique_settings=settings,
        event_type=ChatEvent,
    ):
        chat_context = ChatContext(
            user_id=settings.auth.user_id.get_secret_value(),
            company_id=settings.auth.company_id.get_secret_value(),
            chat_id=event.payload.chat_id,
            assistant_message_id=event.payload.assistant_message.id,
        )

        result = await stream_deep_agent_to_chat_frontend(
            agent=agent,
            user_input=event.payload.user_message.text,
            chat_context=chat_context,
            send_every_n_tokens=5,
        )

        logger.info("Agent finished. Response length: %d chars", len(result))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
