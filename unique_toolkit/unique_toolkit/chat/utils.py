from unique_toolkit._common.token import count_tokens
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.language_model.infos import LanguageModelInfo


def convert_chat_history_to_injectable_string(
    history: list[ChatMessage],
    model_info: LanguageModelInfo | None = None,
) -> tuple[list[str], int]:
    """
    Converts chat history to a string that can be injected into the model.

    Args:
        history (list[ChatMessage]): The chat history.
        model_info (LanguageModelInfo | None): The language model to use for token counting.

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
    chatContextTokenLength = count_tokens(chatContext, model=model_info)
    return chatHistory, chatContextTokenLength
