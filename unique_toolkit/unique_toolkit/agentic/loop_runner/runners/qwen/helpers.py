from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
)


def is_qwen_model(*, model: str | LanguageModelInfo | None) -> bool:
    """Check if the model is a Qwen model."""
    if isinstance(model, LanguageModelInfo):
        name = model.name
        # name is an Enum with a .value attribute
        return "qwen" in str(getattr(name, "value", name)).lower()
    elif isinstance(model, str):
        return "qwen" in model.lower()
    return False


def append_qwen_forced_tool_call_instruction(
    *,
    messages: LanguageModelMessages,
    forced_tool_call_instruction: str,
) -> LanguageModelMessages:
    """Append tool call instruction to the last user message for Qwen models."""
    messages_list = list(messages)
    for i in range(len(messages_list) - 1, -1, -1):
        msg = messages_list[i]
        if msg.role == LanguageModelMessageRole.USER and isinstance(msg.content, str):
            messages_list[i] = msg.model_copy(
                update={"content": msg.content + "\n" + forced_tool_call_instruction}
            )
            break
    return LanguageModelMessages(root=messages_list)


def append_qwen_last_iteration_assistant_message(
    *,
    messages: LanguageModelMessages,
    last_iteration_instruction: str,
) -> LanguageModelMessages:
    """Append an assistant message at the end to indicate no further tool calls are allowed."""
    messages_list = list(messages)
    assistant_message = LanguageModelAssistantMessage(
        content=last_iteration_instruction,
    )
    messages_list.append(assistant_message)
    return LanguageModelMessages(root=messages_list)
