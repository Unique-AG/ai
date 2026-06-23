from unique_toolkit.agentic.tools.run_context import ToolRunContext
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)


def _chat_event(tool_choices: list[str], disabled_tools: list[str]) -> ChatEvent:
    return ChatEvent(
        id="evt-1",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id="user-1",
        company_id="company-1",
        payload=ChatEventPayload(
            name="module",
            description="desc",
            chat_id="chat-1",
            assistant_id="asst-1",
            configuration={},
            user_message=ChatEventUserMessage(
                id="umsg-1",
                text="hi",
                created_at="2021-01-01T00:00:00Z",
                language="EN",
                original_text="hi",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="amsg-1",
                created_at="2021-01-01T00:00:00Z",
            ),
            tool_choices=tool_choices,
            disabled_tools=disabled_tools,
        ),
    )


def test_from_chat_event__copies_tool_filter_fields() -> None:
    event = _chat_event(["search"], ["upload"])
    ctx = ToolRunContext.from_chat_event(event)
    assert ctx.tool_choices == ["search"]
    assert ctx.disabled_tools == ["upload"]
    assert ctx.tool_init_event is event


def test_run_context__defaults_to_empty_lists() -> None:
    ctx = ToolRunContext()
    assert ctx.tool_choices == []
    assert ctx.disabled_tools == []
    assert ctx.tool_init_event is None
