from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.content.utils import count_tokens


def convert_chat_history_to_injectable_string(
    history: list[ChatMessage],
) -> tuple[list[str], int]:
    """
    Converts chat history to a string that can be injected into the model.

    Args:
        history (list[ChatMessage]): The chat history.

    Returns:
        tuple[list[str], int]: The chat history and the token length of the chat context.
    """
    chatHistory = []
    for msg in history:
        if msg.role.value == "assistant":
            chatHistory.append(f"previous_answer: {msg.content}")
        else:
            chatHistory.append(f"previous_question: {msg.content}")
    chatContext = "\n".join(chatHistory)
    chatContextTokenLength = count_tokens(chatContext)
    return chatHistory, chatContextTokenLength
