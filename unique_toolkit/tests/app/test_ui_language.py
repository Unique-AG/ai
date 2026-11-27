import pytest

from unique_toolkit.agentic_table.schemas import MagicTableEvent
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.ui_language import UiLanguage, ui_language


def _chat_event(payload_extra: dict[str, str | None]) -> ChatEvent:
    return ChatEvent.model_validate(
        {
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": "user1",
            "companyId": "company1",
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "chat1",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {
                    "id": "msg2",
                    "createdAt": "2023-01-01T00:01:00Z",
                },
                **payload_extra,
            },
        }
    )


def _magic_table_event(payload_extra: dict[str, str | None]) -> MagicTableEvent:
    return MagicTableEvent.model_validate(
        {
            "id": "event1",
            "event": "unique.magic-table.sheet-completed",
            "userId": "user1",
            "companyId": "company1",
            "payload": {
                "name": "AgenticTable",
                "sheetName": "RFP 2026",
                "action": "SheetCompleted",
                "chatId": "chat1",
                "assistantId": "assistant1",
                "tableId": "sheet1",
                "metadata": {"sheetId": "sheet1", "librarySheetId": "lib1"},
                **payload_extra,
            },
        }
    )


@pytest.mark.ai
@pytest.mark.parametrize(
    ("wire_value", "expected"),
    [
        ("en", UiLanguage.EN),
        ("de", UiLanguage.DE),
        ("fr", UiLanguage.FR),
    ],
)
def test_ui_language__returns_the_sent_language__chat_event(
    wire_value: str, expected: UiLanguage
) -> None:
    """
    Purpose: Verify the ``uiLanguage`` of a chat event is read back as a ``UiLanguage``.
    Why this matters: Modules pick the translation of the text they write to the chat from it.
    Setup summary: Parse a chat event with ``uiLanguage`` set; assert the matching member.
    """
    # Arrange
    event = _chat_event({"uiLanguage": wire_value})

    # Act
    language = ui_language(event)

    # Assert
    assert language is expected


@pytest.mark.ai
def test_ui_language__returns_the_sent_language__magic_table_event() -> None:
    """
    Purpose: Verify Agentic Table events carry ``uiLanguage`` like chat events do.
    Why this matters: Agentic Table notices would stay English if the payload dropped the field.
    Setup summary: Parse a sheet-completed event with ``uiLanguage`` set; assert German.
    """
    # Arrange
    event = _magic_table_event({"uiLanguage": "de"})

    # Act
    language = ui_language(event)

    # Assert
    assert language is UiLanguage.DE


@pytest.mark.ai
@pytest.mark.parametrize(
    "payload_extra",
    [
        {},
        {"uiLanguage": None},
        {"uiLanguage": "xx"},
        {"uiLanguage": "de-CH"},
    ],
)
def test_ui_language__falls_back_to_english__missing_or_unsupported_value(
    payload_extra: dict[str, str | None],
) -> None:
    """
    Purpose: Verify a missing or unsupported ``uiLanguage`` resolves to English.
    Why this matters: Events from older senders or with an unexpected tag must still be handled.
    Setup summary: Parse a chat event without a supported ``uiLanguage``; assert English.
    """
    # Arrange
    event = _chat_event(payload_extra)

    # Act
    language = ui_language(event)

    # Assert
    assert language is UiLanguage.EN
