"""Tests for ``inject_tool_reminders_into_user_message``.

Verifies that per-turn tool reminders (e.g. the Skill tool's
``<system-reminder>`` block) are appended as leading
``{"type": "text"}`` parts on the latest user-role message.
"""

from __future__ import annotations

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

from unique_orchestrator._builders.inject_tool_reminders import (
    inject_tool_reminders_into_user_message,
)


def _user(content: object) -> LanguageModelUserMessage:
    return LanguageModelUserMessage(content=content)  # type: ignore[arg-type]


class TestInjectToolReminders:
    def test_no_reminders_is_noop(self) -> None:
        msgs = LanguageModelMessages([_user("commit my staged changes")])

        out = inject_tool_reminders_into_user_message(msgs, [])

        assert out.root[0].content == "commit my staged changes"

    def test_empty_strings_are_skipped(self) -> None:
        msgs = LanguageModelMessages([_user("hello")])

        out = inject_tool_reminders_into_user_message(msgs, ["", ""])

        assert out.root[0].content == "hello"

    def test_single_reminder_prepends_to_string_user_content(self) -> None:
        msgs = LanguageModelMessages([_user("commit my staged changes as a fix")])

        reminder = "<system-reminder>skills: /commit</system-reminder>"
        out = inject_tool_reminders_into_user_message(msgs, [reminder])

        content = out.root[0].content
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0] == {"type": "text", "text": reminder}  # type: ignore[comparison-overlap]
        assert content[1] == {
            "type": "text",
            "text": "commit my staged changes as a fix",
        }  # type: ignore[comparison-overlap]

    def test_multiple_reminders_preserved_in_order(self) -> None:
        msgs = LanguageModelMessages([_user("query text")])

        out = inject_tool_reminders_into_user_message(
            msgs,
            [
                "<system-reminder>first</system-reminder>",
                "<system-reminder>second</system-reminder>",
            ],
        )

        content = out.root[0].content
        assert isinstance(content, list)
        assert len(content) == 3
        assert content[0]["text"] == "<system-reminder>first</system-reminder>"  # type: ignore[index]
        assert content[1]["text"] == "<system-reminder>second</system-reminder>"  # type: ignore[index]
        assert content[2]["text"] == "query text"  # type: ignore[index]

    def test_preserves_existing_multi_part_content(self) -> None:
        """Parts injected by upstream steps (e.g. open-file tool) are kept."""
        parts: list[dict[str, object]] = [
            {"type": "text", "text": "query"},
            {"type": "image_url", "imageUrl": {"url": "data:image/png;base64,..."}},
        ]
        msgs = LanguageModelMessages([_user(parts)])

        out = inject_tool_reminders_into_user_message(
            msgs, ["<system-reminder>r1</system-reminder>"]
        )

        content = out.root[0].content
        assert isinstance(content, list)
        assert len(content) == 3
        assert content[0]["text"] == "<system-reminder>r1</system-reminder>"  # type: ignore[index]
        assert content[1]["text"] == "query"  # type: ignore[index]
        assert content[2]["type"] == "image_url"  # type: ignore[index]

    def test_only_latest_user_message_is_processed(self) -> None:
        older = _user("old query")
        assistant = LanguageModelAssistantMessage(content="ok")
        latest = _user("new query")

        msgs = LanguageModelMessages([older, assistant, latest])

        out = inject_tool_reminders_into_user_message(
            msgs, ["<system-reminder>fresh</system-reminder>"]
        )

        assert out.root[0].content == "old query"

        latest_content = out.root[2].content
        assert isinstance(latest_content, list)
        assert latest_content[0]["text"] == "<system-reminder>fresh</system-reminder>"  # type: ignore[index]
        assert latest_content[1]["text"] == "new query"  # type: ignore[index]

    def test_injects_on_latest_user_when_tool_messages_follow(self) -> None:
        """After a tool call, the reminder must still land on the latest USER message.

        This is the iteration-2+ case: the message list ends with a
        tool response, but the reminder belongs on the preceding user
        turn so the model sees it in the next call.
        """
        user_msg = _user("commit the change")
        assistant = LanguageModelAssistantMessage(content="calling tool")
        tool_response = LanguageModelToolMessage(
            content="tool ran",
            tool_call_id="call_1",
            name="Skill",
        )

        msgs = LanguageModelMessages([user_msg, assistant, tool_response])

        out = inject_tool_reminders_into_user_message(
            msgs, ["<system-reminder>skills: /commit</system-reminder>"]
        )

        assert len(out.root) == 3

        rewritten_user = out.root[0]
        assert rewritten_user.role == LanguageModelMessageRole.USER
        assert isinstance(rewritten_user.content, list)
        assert len(rewritten_user.content) == 2
        assert (
            rewritten_user.content[0]["text"]  # type: ignore[index]
            == "<system-reminder>skills: /commit</system-reminder>"
        )
        assert rewritten_user.content[1]["text"] == "commit the change"  # type: ignore[index]

        assert out.root[1] is assistant
        assert out.root[2] is tool_response

    def test_empty_messages_is_noop(self) -> None:
        msgs = LanguageModelMessages([])
        out = inject_tool_reminders_into_user_message(
            msgs, ["<system-reminder>x</system-reminder>"]
        )
        assert out.root == []

    def test_messages_without_user_message_is_noop(self) -> None:
        msgs = LanguageModelMessages(
            [LanguageModelAssistantMessage(content="assistant only")]
        )
        out = inject_tool_reminders_into_user_message(
            msgs, ["<system-reminder>x</system-reminder>"]
        )
        assert len(out.root) == 1
        assert out.root[0].content == "assistant only"
