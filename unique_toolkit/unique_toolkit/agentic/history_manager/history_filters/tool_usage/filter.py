import logging
from collections.abc import Iterable

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    ChatMessageFilter,
)
from unique_toolkit.agentic.history_manager.history_filters.tool_usage.postprocessor import (
    SaveToolCallsPostprocessor,
)
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole

logger = logging.getLogger(__name__)


def get_safe_tool_usage_history_filter(
    user_id: str,
    company_id: str,
    safe_tool_names: Iterable[str] | None = None,
) -> ChatMessageFilter:
    """
    Filter out user-assistant message pairs where other tools than the safe tools were called.
    """
    if safe_tool_names is None:
        safe_tool_names = []

    safe_tool_names = set(safe_tool_names)

    async def filter(messages: Iterable[ChatMessage]) -> Iterable[ChatMessage]:
        """
        Filter for private tool usage history.
        It filters out messages that are not part of the private tool usage history.
        """
        last_user_message = None
        filtered_messages = []
        for message in messages:
            if message.role == ChatRole.USER:
                last_user_message = message

            elif message.role == ChatRole.ASSISTANT:
                if message.id is None:  # Can't know which tool calls were used
                    logger.info("Filtering assistant message with null id")
                    last_user_message = None  # Ignore last user message
                    continue

                tools_called = await SaveToolCallsPostprocessor.get_assistant_message_used_tool_calls(
                    company_id=company_id,
                    user_id=user_id,
                    assistant_message_id=message.id,
                )

                if (
                    tools_called is None
                ):  # Unknown tool calls, message should be ignored
                    logger.info(
                        "Filtering assistant message %s with unknown tool calls",
                        message.id,
                    )
                    last_user_message = None
                    continue

                other_tool_calls = tools_called - safe_tool_names
                if len(other_tool_calls) > 0:  # Other tools were called
                    logger.info(
                        "Filtering assistant message %s with other tool calls (%s)",
                        message.id,
                        other_tool_calls,
                    )
                    last_user_message = None
                    continue

                if last_user_message is not None:
                    filtered_messages.append(last_user_message)
                    last_user_message = None

                filtered_messages.append(message)

        return filtered_messages

    return filter
