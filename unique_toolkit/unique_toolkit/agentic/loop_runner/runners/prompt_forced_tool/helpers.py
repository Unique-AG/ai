"""Message helpers for models that reject a forced tool_choice."""

from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
)


def append_prompt_forced_tool_instruction(
    *,
    messages: LanguageModelMessages,
    instruction: str,
) -> LanguageModelMessages:
    """Append a must-call instruction to the last user message.

    Args:
        messages (LanguageModelMessages): Conversation copied for this tool.
        instruction (str): Instruction that names the tool to call.

    Returns:
        LanguageModelMessages: A new message list with the instruction appended
        when the last user message has string content.
    """
    messages_list = list(messages)
    for i in range(len(messages_list) - 1, -1, -1):
        msg = messages_list[i]
        if msg.role == LanguageModelMessageRole.USER and isinstance(msg.content, str):
            messages_list[i] = msg.model_copy(
                update={"content": msg.content + "\n" + instruction}
            )
            break
    return LanguageModelMessages(root=messages_list)
