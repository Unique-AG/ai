from unique_toolkit.agentic.tools.run_context import ToolRunContext
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAdditionalParameters,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
    UploadedFileInfo,
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


def test_from_chat_event__copies_turn_snapshot_fields() -> None:
    event = _chat_event([], [])
    event.payload.name = "swot-module"
    event.payload.metadata_filter = {"scope": "x"}
    event.payload.message_execution_id = "exec-1"
    event.payload.session_config = {"swot_analysis": {"company_listing": {}}}
    event.payload.user_metadata = {"region": "eu"}
    event.payload.tool_parameters = {"mode": "full"}
    event.payload.additional_parameters = ChatEventAdditionalParameters(
        user_space_instructions="",
        selected_uploaded_files=[
            UploadedFileInfo(id="file-1", name="a.pdf", mime_type="application/pdf")
        ],
    )

    ctx = ToolRunContext.from_chat_event(event)

    assert ctx.module_name == "swot-module"
    assert ctx.metadata_filter == {"scope": "x"}
    assert ctx.message_execution_id == "exec-1"
    assert ctx.session_config == {"swot_analysis": {"company_listing": {}}}
    assert ctx.user_metadata == {"region": "eu"}
    assert ctx.tool_parameters == {"mode": "full"}
    assert ctx.selected_uploaded_file_ids == ["file-1"]
    assert ctx.user_message_text == "hi"


def test_run_context__defaults_to_empty_lists() -> None:
    ctx = ToolRunContext()
    assert ctx.tool_choices == []
    assert ctx.disabled_tools == []
    assert ctx.selected_uploaded_file_ids == []
    assert ctx.tool_parameters == {}
