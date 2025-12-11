from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
)

_QWEN__FORCED_TOOL_CALL_INSTRUCTION = (
    "\n\nTool Call Instruction:\nYou always have to return a tool call. "
    "You must start the response with <tool_call> and end with </tool_call>. "
    "Do NOT provide natural language explanations, summaries, or any text outside the <tool_call> block."
)


def is_qwen_model(model: str | LanguageModelInfo | None) -> bool:
    """Check if the model is a Qwen model."""
    if isinstance(model, LanguageModelInfo):
        name = model.name
        # name is an Enum with a .value attribute
        return "qwen" in str(getattr(name, "value", name)).lower()
    elif isinstance(model, str):
        return "qwen" in model.lower()
    return False


def append_qwen_forced_tool_call_instruction(
    messages: LanguageModelMessages,
) -> LanguageModelMessages:
    """Append tool call instruction to the last user message for Qwen models."""
    messages_list = list(messages)
    for i in range(len(messages_list) - 1, -1, -1):
        msg = messages_list[i]
        if msg.role == LanguageModelMessageRole.USER and isinstance(msg.content, str):
            messages_list[i] = msg.model_copy(
                update={"content": msg.content + _QWEN__FORCED_TOOL_CALL_INSTRUCTION}
            )
            break
    return LanguageModelMessages(root=messages_list)
