from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from unique_toolkit.chat import ChatMessage as UniqueMessage
from unique_toolkit.chat import ChatMessageRole as UniqueRole


def unique_history_to_langchain_history(
    unique_history: list[UniqueMessage],
) -> list[BaseMessage]:
    history = []
    for m in unique_history:
        if m.role == UniqueRole.ASSISTANT:
            history.append(AIMessage(content=m.content))
        elif m.role == UniqueRole.USER:
            history.append(HumanMessage(content=m.content))
        else:
            raise Exception("Unknown message role.")

    return history
