"""Tests for OpenFileToolRuntime.

Covers the runtime helper that manages the experimental OpenFile payload flow,
including content-file injection, retry logic, message stripping, evaluation
filtering, and the system-reminder injection for InternalSearch results.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.experimental.open_file_tool.runtime import (
    OpenFileToolRuntime,
    OpenFileToolRuntimeConfig,
)
from unique_toolkit.content.schemas import Content
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_content(
    *,
    id: str = "cont_abc",
    key: str = "report.pdf",
    expired_at: datetime | None = None,
    created_at: datetime | None = None,
) -> Content:
    return Content(
        id=id,
        key=key,
        expired_at=expired_at,
        created_at=created_at,
    )


def _make_config(
    *,
    enabled: bool = True,
    send_files_in_payload: bool = False,
    send_uploaded_files_in_payload: bool = False,
    use_responses_api: bool = True,
) -> OpenFileToolRuntimeConfig:
    return OpenFileToolRuntimeConfig(
        enabled=enabled,
        send_files_in_payload=send_files_in_payload,
        send_uploaded_files_in_payload=send_uploaded_files_in_payload,
        use_responses_api=use_responses_api,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def logger():
    return logging.getLogger("test_open_file_runtime")


@pytest.fixture
def content_service():
    svc = Mock()
    svc.get_documents_uploaded_to_chat.return_value = []
    return svc


@pytest.fixture
def tool_manager():
    mgr = Mock()
    mgr.get_tool_by_name.return_value = None
    mgr.exclude_tool.return_value = True
    return mgr


@pytest.fixture
def message_step_logger():
    mock = Mock()
    mock.create_message_log_entry_async = AsyncMock()
    return mock


@pytest.fixture
def agent_file_registry() -> list[str]:
    return []


@pytest.fixture
def runtime(
    logger, content_service, tool_manager, message_step_logger, agent_file_registry
):
    """Runtime with the feature fully enabled but no payload flags set."""
    return OpenFileToolRuntime(
        logger=logger,
        config=_make_config(),
        content_service=content_service,
        tool_manager=tool_manager,
        message_step_logger=message_step_logger,
        agent_file_registry=agent_file_registry,
    )


# ===================================================================
# OpenFileToolRuntimeConfig
# ===================================================================


@pytest.mark.ai
class TestOpenFileToolRuntimeConfig:
    def test__defaults__all_disabled(self):
        """
        Purpose: Verify the default config has every flag disabled.
        Why this matters: A safe default prevents accidental payload injection.
        Setup summary: Instantiate with no arguments, assert all flags are False.
        """
        cfg = OpenFileToolRuntimeConfig()

        assert cfg.enabled is False
        assert cfg.send_files_in_payload is False
        assert cfg.send_uploaded_files_in_payload is False
        assert cfg.use_responses_api is False

    def test__frozen__cannot_mutate(self):
        """
        Purpose: Verify the config dataclass is immutable.
        Why this matters: Runtime config should not change after construction.
        Setup summary: Try to set a field, expect FrozenInstanceError.
        """
        cfg = OpenFileToolRuntimeConfig(enabled=True)

        with pytest.raises(AttributeError):
            cfg.enabled = False  # type: ignore[misc]


# ===================================================================
# should_attach_content_files
# ===================================================================


@pytest.mark.ai
class TestShouldAttachContentFiles:
    def test__returns_false__when_feature_disabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: No files attached when the feature is disabled.
        Why this matters: Guard against unintended payload injection.
        Setup summary: Create runtime with enabled=False, verify returns False.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(enabled=False),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        assert rt.should_attach_content_files() is False

    def test__returns_false__when_responses_api_off(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: No files when responses API is not used.
        Why this matters: File payload injection only works with the responses API.
        Setup summary: Create runtime with use_responses_api=False, verify returns False.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(use_responses_api=False),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        assert rt.should_attach_content_files() is False

    def test__returns_false__when_no_payload_flags(self, runtime):
        """
        Purpose: No files when neither KB nor uploaded file flags are on.
        Why this matters: Both payload flags default to False.
        Setup summary: Default runtime fixture has no payload flags, verify False.
        """
        assert runtime.should_attach_content_files() is False

    def test__returns_true__when_kb_payload_enabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Files should attach when KB file payload is enabled.
        Why this matters: KB file injection is a key feature path.
        Setup summary: Enable send_files_in_payload, verify True.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        assert rt.should_attach_content_files() is True

    def test__returns_true__when_uploaded_payload_enabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Files should attach when uploaded file payload is enabled.
        Why this matters: Uploaded file injection is a key feature path.
        Setup summary: Enable send_uploaded_files_in_payload, verify True.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_uploaded_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        assert rt.should_attach_content_files() is True

    def test__returns_false__after_payload_disabled_by_retry(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: After a retry disables payloads, should_attach returns False.
        Why this matters: Retry logic must prevent further file injection.
        Setup summary: Enable KB payload, register a file, trigger prepare_retry_messages,
        then verify should_attach_content_files returns False.
        """
        registry: list[str] = ["cont_abc"]
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(root=[LanguageModelUserMessage(content="hi")])
        rt.prepare_retry_messages(messages)

        assert rt.should_attach_content_files() is False


# ===================================================================
# inject_content_files_into_user_message
# ===================================================================


@pytest.mark.ai
class TestInjectContentFilesIntoUserMessage:
    def test__noop__when_no_files(self, runtime):
        """
        Purpose: Messages are returned unchanged when there are no file parts.
        Why this matters: Injection must be a no-op when nothing to inject.
        Setup summary: Call with no registry or uploaded docs, verify identity.
        """
        msg = LanguageModelUserMessage(content="hello")
        messages = LanguageModelMessages(root=[msg])

        result = runtime.inject_content_files_into_user_message(messages)

        assert result.root[0].content == "hello"

    def test__injects_kb_file_parts__into_last_user_message(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: KB file parts are appended to the last user message.
        Why this matters: The LLM must receive files alongside the user prompt.
        Setup summary: Enable KB payload, add a content_id to registry, verify file part added.
        """
        registry = ["cont_123"]
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="summarize this")]
        )

        result = rt.inject_content_files_into_user_message(messages)

        parts = result.root[0].content
        assert isinstance(parts, list)
        assert parts[0] == {"type": "text", "text": "summarize this"}
        assert parts[1]["type"] == "file"
        assert parts[1]["file"]["file_data"] == "unique://content/cont_123"

    def test__injects_uploaded_file_parts(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Uploaded PDF documents appear as file parts.
        Why this matters: Users upload PDFs that should be attached to the payload.
        Setup summary: Mock uploaded documents, enable flag, verify file parts.
        """
        doc = _make_content(id="cont_up1", key="upload.pdf")
        content_service.get_documents_uploaded_to_chat.return_value = [doc]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_uploaded_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="read this")]
        )

        result = rt.inject_content_files_into_user_message(messages)

        parts = result.root[0].content
        assert isinstance(parts, list)
        file_parts = [p for p in parts if p.get("type") == "file"]
        assert len(file_parts) == 1
        assert file_parts[0]["file"]["file_data"] == "unique://content/cont_up1"

    def test__deduplicates_ids_across_uploaded_and_kb(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Same content_id from both sources should appear only once.
        Why this matters: Prevents duplicate file parts in the payload.
        Setup summary: Add same ID in registry and uploaded docs, verify single file part.
        """
        doc = _make_content(id="cont_dup", key="dup.pdf")
        content_service.get_documents_uploaded_to_chat.return_value = [doc]
        registry = ["cont_dup"]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(
                send_files_in_payload=True,
                send_uploaded_files_in_payload=True,
            ),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="test")]
        )

        result = rt.inject_content_files_into_user_message(messages)

        parts = result.root[0].content
        assert isinstance(parts, list)
        file_parts = [
            p for p in parts if isinstance(p, dict) and p.get("type") == "file"
        ]
        assert len(file_parts) == 1

    def test__targets_last_user_message__not_first(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: File parts are injected into the last (most recent) user message.
        Why this matters: The LLM context window expects files near the latest prompt.
        Setup summary: Create messages with two user messages, verify only the last is modified.
        """
        registry = ["cont_last"]
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="first"),
                LanguageModelUserMessage(content="second"),
            ]
        )

        result = rt.inject_content_files_into_user_message(messages)

        assert result.root[0].content == "first"
        assert isinstance(result.root[1].content, list)

    def test__handles_list_content_user_message(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: If the user message already has list content, text parts are preserved.
        Why this matters: Multimodal messages may already be in list form.
        Setup summary: Create user message with list content, inject, verify text preserved.
        """
        registry = ["cont_list"]
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(
                    content=[{"type": "text", "text": "existing text"}]
                )
            ]
        )

        result = rt.inject_content_files_into_user_message(messages)

        parts = result.root[0].content
        assert isinstance(parts, list)
        text_parts = [p for p in parts if p.get("type") == "text"]
        assert any("existing text" in p["text"] for p in text_parts)


# ===================================================================
# should_retry_without_files
# ===================================================================


@pytest.mark.ai
class TestShouldRetryWithoutFiles:
    def test__returns_false__when_feature_disabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: No retry when the feature is off.
        Why this matters: Retry logic should not trigger for disabled features.
        Setup summary: Disabled runtime, any exception, verify False.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(enabled=False),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_1"],
        )

        assert rt.should_retry_without_files(Exception("too large")) is False

    def test__returns_false__when_no_payload_flags(self, runtime):
        """
        Purpose: No retry when neither payload flag is set.
        Why this matters: Nothing to strip on retry if no files were sent.
        Setup summary: Default runtime, verify False.
        """
        assert runtime.should_retry_without_files(Exception("too large")) is False

    def test__returns_false__when_no_files_registered(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: No retry when KB flag is on but registry is empty.
        Why this matters: No point retrying if we didn't send any files.
        Setup summary: Enable KB payload but empty registry, verify False.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        assert rt.should_retry_without_files(Exception("too large")) is False

    def test__returns_false__when_already_disabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: No retry when payloads were already disabled by a prior retry.
        Why this matters: Prevents infinite retry loops.
        Setup summary: Trigger prepare_retry, then check should_retry returns False.
        """
        registry: list[str] = ["cont_1"]
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(root=[LanguageModelUserMessage(content="hi")])
        rt.prepare_retry_messages(messages)

        assert rt.should_retry_without_files(Exception("too large")) is False

    @pytest.mark.parametrize(
        "error_text",
        [
            "too large",
            "payload too large",
            "request entity too large",
            "content_length_exceeded",
            "max_tokens",
            "context_length_exceeded",
            "413",
            "request too large",
            "403 forbidden",
            "application-gateway",
        ],
    )
    def test__returns_true__for_retry_signals(
        self, logger, content_service, tool_manager, message_step_logger, error_text
    ):
        """
        Purpose: Retry triggers for every known retry signal.
        Why this matters: All known error patterns must be caught for resilient file handling.
        Setup summary: Enable KB payload, register a file, verify True for each signal.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_file"],
        )

        assert rt.should_retry_without_files(Exception(error_text)) is True

    def test__returns_false__for_unrelated_error(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Unrelated errors should not trigger a file-stripping retry.
        Why this matters: Only specific signals indicate payload-size issues.
        Setup summary: Enable KB payload, register a file, check unrelated error.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_file"],
        )

        assert rt.should_retry_without_files(Exception("connection timeout")) is False

    def test__returns_true__for_uploaded_files_with_signal(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Retry also triggers for uploaded file payloads.
        Why this matters: Both file sources can cause payload-size errors.
        Setup summary: Enable uploaded payload, mock uploaded doc, verify True.
        """
        doc = _make_content(id="cont_up1", key="big.pdf")
        content_service.get_documents_uploaded_to_chat.return_value = [doc]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_uploaded_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        assert rt.should_retry_without_files(Exception("413 error")) is True


# ===================================================================
# prepare_retry_messages
# ===================================================================


@pytest.mark.ai
class TestPrepareRetryMessages:
    def test__excludes_open_file_tool(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Verify the OpenFile tool is excluded from the tool manager on retry.
        Why this matters: After a failed file injection, the tool should not be offered again.
        Setup summary: Trigger prepare_retry, verify exclude_tool called with "OpenFile".
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_1"],
        )
        messages = LanguageModelMessages(root=[LanguageModelUserMessage(content="hi")])

        rt.prepare_retry_messages(messages)

        tool_manager.exclude_tool.assert_called_once_with("OpenFile")

    def test__clears_agent_file_registry(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Verify the agent file registry is emptied on retry.
        Why this matters: Stale file IDs must not leak into subsequent iterations.
        Setup summary: Pre-fill registry, trigger retry, verify empty.
        """
        registry = ["cont_1", "cont_2"]
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=registry,
        )
        messages = LanguageModelMessages(root=[LanguageModelUserMessage(content="hi")])

        rt.prepare_retry_messages(messages)

        assert registry == []

    def test__strips_file_parts_from_user_messages(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: File parts in user messages are removed on retry.
        Why this matters: The retry must send a payload without the oversized files.
        Setup summary: Create user message with file parts, trigger retry, verify stripped.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_1"],
        )
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(
                    content=[
                        {"type": "text", "text": "hello"},
                        {
                            "type": "file",
                            "file": {
                                "filename": "cont_1",
                                "file_data": "unique://content/cont_1",
                            },
                        },
                    ]
                )
            ]
        )

        result = rt.prepare_retry_messages(messages)

        assert isinstance(result.root[0].content, str)
        assert "hello" in result.root[0].content

    def test__strips_open_file_tool_messages__when_kb_enabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: OpenFile assistant+tool message pairs are removed for KB payload.
        Why this matters: Leftover tool messages would confuse the LLM on retry.
        Setup summary: Build messages with an OpenFile tool call/response pair,
        trigger retry, verify both are removed.
        """
        func = LanguageModelFunction(
            name="OpenFile", arguments={"content_ids": ["cont_1"]}
        )
        assistant_msg = LanguageModelAssistantMessage.from_functions([func])
        assert assistant_msg.tool_calls is not None
        tool_call_id = assistant_msg.tool_calls[0].id
        tool_msg = LanguageModelToolMessage(
            content="Files opened",
            name="OpenFile",
            tool_call_id=tool_call_id,
        )
        user_msg = LanguageModelUserMessage(content="hi")
        messages = LanguageModelMessages(root=[user_msg, assistant_msg, tool_msg])

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_1"],
        )

        result = rt.prepare_retry_messages(messages)

        tool_messages = [
            m for m in result.root if isinstance(m, LanguageModelToolMessage)
        ]
        assert len(tool_messages) == 0
        remaining_assistant = [
            m
            for m in result.root
            if isinstance(m, LanguageModelAssistantMessage) and m.tool_calls
        ]
        for msg in remaining_assistant:
            assert msg.tool_calls is not None
            assert all(tc.function.name != "OpenFile" for tc in msg.tool_calls)

    def test__injects_uploaded_file_fallback__when_uploaded_enabled(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: A fallback OpenFile call + tool error message is injected for uploaded files.
        Why this matters: The LLM needs to know the uploaded file couldn't be processed.
        Setup summary: Enable uploaded payload, mock document, trigger retry,
        verify fallback messages appended.
        """
        doc = _make_content(id="cont_up1", key="big.pdf")
        content_service.get_documents_uploaded_to_chat.return_value = [doc]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(send_uploaded_files_in_payload=True),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="read file")]
        )

        result = rt.prepare_retry_messages(messages)

        tool_msgs = [m for m in result.root if isinstance(m, LanguageModelToolMessage)]
        assert any(
            isinstance(m.content, str) and "too large" in m.content.lower()
            for m in tool_msgs
        )


# ===================================================================
# strip_file_parts_from_messages (static)
# ===================================================================


@pytest.mark.ai
class TestStripFilePartsFromMessages:
    def test__converts_list_content_to_text(self):
        """
        Purpose: User messages with list content are collapsed to plain text.
        Why this matters: After stripping files the user message must be a simple string.
        Setup summary: Create user message with text+file parts, strip, verify string.
        """
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(
                    content=[
                        {"type": "text", "text": "hello"},
                        {"type": "file", "file": {"filename": "a.pdf"}},
                    ]
                )
            ]
        )

        result = OpenFileToolRuntime.strip_file_parts_from_messages(messages)

        assert isinstance(result.root[0].content, str)
        assert "hello" in result.root[0].content

    def test__preserves_string_content(self):
        """
        Purpose: User messages already as strings are unchanged.
        Why this matters: The method must be idempotent for string content.
        Setup summary: Create string-content user message, strip, verify unchanged.
        """
        messages = LanguageModelMessages(
            root=[LanguageModelUserMessage(content="plain text")]
        )

        result = OpenFileToolRuntime.strip_file_parts_from_messages(messages)

        assert result.root[0].content == "plain text"

    def test__preserves_non_user_messages(self):
        """
        Purpose: System and assistant messages are not modified.
        Why this matters: Only user messages carry file parts.
        Setup summary: Include system + assistant messages, strip, verify intact.
        """
        messages = LanguageModelMessages(
            root=[
                LanguageModelSystemMessage(content="system prompt"),
                LanguageModelAssistantMessage(content="response"),
                LanguageModelUserMessage(content=[{"type": "text", "text": "user"}]),
            ]
        )

        result = OpenFileToolRuntime.strip_file_parts_from_messages(messages)

        assert result.root[0].content == "system prompt"
        assert result.root[1].content == "response"
        assert isinstance(result.root[2].content, str)

    def test__handles_input_text_type(self):
        """
        Purpose: Parts with type 'input_text' are also preserved in the join.
        Why this matters: The responses API uses 'input_text' instead of 'text'.
        Setup summary: Create user message with input_text parts, strip, verify joined.
        """
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(
                    content=[
                        {"type": "input_text", "text": "part1"},
                        {"type": "input_text", "text": "part2"},
                    ]
                )
            ]
        )

        result = OpenFileToolRuntime.strip_file_parts_from_messages(messages)

        content = result.root[0].content
        assert isinstance(content, str)
        assert "part1" in content
        assert "part2" in content


# ===================================================================
# filter_evaluation_names
# ===================================================================


@pytest.mark.ai
class TestFilterEvaluationNames:
    def test__no_filter__when_registry_empty(self, runtime):
        """
        Purpose: All evaluations are returned when no files have been opened.
        Why this matters: Hallucination checks should only be skipped when files were used.
        Setup summary: Empty registry, pass all metric names, verify all returned.
        """
        names = [
            EvaluationMetricName.HALLUCINATION,
            EvaluationMetricName.CONTEXT_RELEVANCY,
        ]

        result = runtime.filter_evaluation_names(names)

        assert result == names

    def test__removes_hallucination__when_files_registered(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Hallucination check is removed when files were opened.
        Why this matters: LLM has full file content so hallucination eval is misleading.
        Setup summary: Pre-fill registry, filter, verify HALLUCINATION removed.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_1"],
        )
        names = [
            EvaluationMetricName.HALLUCINATION,
            EvaluationMetricName.CONTEXT_RELEVANCY,
        ]

        result = rt.filter_evaluation_names(names)

        assert EvaluationMetricName.HALLUCINATION not in result
        assert EvaluationMetricName.CONTEXT_RELEVANCY in result

    def test__keeps_all__when_no_hallucination_present(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: If HALLUCINATION isn't in the list, nothing is removed.
        Why this matters: The filter should not remove unrelated metrics.
        Setup summary: Registry has files but metric list has no HALLUCINATION.
        """
        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=["cont_1"],
        )
        names = [EvaluationMetricName.CONTEXT_RELEVANCY]

        result = rt.filter_evaluation_names(names)

        assert result == names


# ===================================================================
# inject_open_file_reminder
# ===================================================================


@pytest.mark.ai
class TestInjectOpenFileReminder:
    def test__noop__when_open_file_tool_not_available(self, runtime):
        """
        Purpose: No reminder injected when the OpenFile tool is not loaded.
        Why this matters: Without the tool the reminder would be confusing.
        Setup summary: tool_manager returns None for OpenFile, verify no change.
        """
        response = MagicMock()
        response.name = "InternalSearch"
        chunk = MagicMock()
        chunk.key = "doc.pdf : page 1"
        response.content_chunks = [chunk]
        response.system_reminder = None

        runtime.inject_open_file_reminder([response])

        assert response.system_reminder is None

    def test__injects_reminder__for_internal_search_with_pdf(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: A system reminder is added to InternalSearch results that have PDF chunks.
        Why this matters: Guides the LLM to use OpenFile for better document analysis.
        Setup summary: Mock tool_manager to return OpenFile tool, create InternalSearch
        response with PDF chunk, verify reminder injected.
        """
        tool_manager.get_tool_by_name.return_value = MagicMock()

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        response = MagicMock()
        response.name = "InternalSearch"
        chunk = MagicMock()
        chunk.key = "report.pdf : page 1"
        response.content_chunks = [chunk]
        response.system_reminder = None

        rt.inject_open_file_reminder([response])

        assert response.system_reminder is not None
        assert "OpenFile" in response.system_reminder

    def test__skips_non_internal_search_responses(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Non-InternalSearch responses are not touched.
        Why this matters: The reminder is specific to search results.
        Setup summary: Create response with name != InternalSearch, verify no change.
        """
        tool_manager.get_tool_by_name.return_value = MagicMock()

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        response = MagicMock()
        response.name = "WebSearch"
        response.system_reminder = None

        rt.inject_open_file_reminder([response])

        assert response.system_reminder is None

    def test__skips__when_no_pdf_chunks(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: No reminder when InternalSearch has no PDF chunks.
        Why this matters: Reminder is only relevant for PDF documents.
        Setup summary: Create InternalSearch response with .docx chunk, verify no change.
        """
        tool_manager.get_tool_by_name.return_value = MagicMock()

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        response = MagicMock()
        response.name = "InternalSearch"
        chunk = MagicMock()
        chunk.key = "report.docx : page 1"
        response.content_chunks = [chunk]
        response.system_reminder = None

        rt.inject_open_file_reminder([response])

        assert response.system_reminder is None

    def test__appends_to_existing_reminder(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Existing system_reminder content is preserved when appending.
        Why this matters: Multiple reminders may be set by different subsystems.
        Setup summary: Set an existing reminder, inject, verify both present.
        """
        tool_manager.get_tool_by_name.return_value = MagicMock()

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        response = MagicMock()
        response.name = "InternalSearch"
        chunk = MagicMock()
        chunk.key = "file.PDF : page 2"
        response.content_chunks = [chunk]
        response.system_reminder = "Existing reminder."

        rt.inject_open_file_reminder([response])

        assert "Existing reminder." in response.system_reminder
        assert "OpenFile" in response.system_reminder


# ===================================================================
# get_uploaded_documents
# ===================================================================


@pytest.mark.ai
class TestGetUploadedDocuments:
    def test__returns_empty_list__when_no_uploads(self, runtime, content_service):
        """
        Purpose: Returns empty when there are no uploaded documents.
        Why this matters: Baseline behavior without uploads.
        Setup summary: content_service returns empty, verify empty result.
        """
        result = runtime.get_uploaded_documents()

        assert result == []

    def test__filters_non_pdf(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Only PDF files are included.
        Why this matters: Only PDFs are supported for the file payload flow.
        Setup summary: Return mix of pdf and docx documents, verify only pdf returned.
        """
        pdf_doc = _make_content(id="cont_pdf", key="report.pdf")
        docx_doc = _make_content(id="cont_docx", key="notes.docx")
        content_service.get_documents_uploaded_to_chat.return_value = [
            pdf_doc,
            docx_doc,
        ]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        result = rt.get_uploaded_documents()

        assert len(result) == 1
        assert result[0].id == "cont_pdf"

    def test__filters_expired(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Expired documents are excluded.
        Why this matters: Serving expired content would fail downstream.
        Setup summary: One fresh, one expired PDF; verify only fresh one returned.
        """
        fresh = _make_content(id="cont_fresh", key="fresh.pdf")
        expired = _make_content(
            id="cont_expired",
            key="old.pdf",
            expired_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        content_service.get_documents_uploaded_to_chat.return_value = [fresh, expired]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        result = rt.get_uploaded_documents()

        assert len(result) == 1
        assert result[0].id == "cont_fresh"

    def test__caches_result(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Uploaded documents are fetched only once and then cached.
        Why this matters: Avoid redundant API calls on repeated access.
        Setup summary: Call get_uploaded_documents twice, verify single service call.
        """
        content_service.get_documents_uploaded_to_chat.return_value = []

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        rt.get_uploaded_documents()
        rt.get_uploaded_documents()

        content_service.get_documents_uploaded_to_chat.assert_called_once()

    def test__sorts_by_created_at(
        self, logger, content_service, tool_manager, message_step_logger
    ):
        """
        Purpose: Documents are sorted by created_at ascending.
        Why this matters: Consistent ordering for deterministic payload construction.
        Setup summary: Two PDFs with different created_at, verify sort order.
        """
        newer = _make_content(
            id="cont_new",
            key="new.pdf",
            created_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        older = _make_content(
            id="cont_old",
            key="old.pdf",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        content_service.get_documents_uploaded_to_chat.return_value = [newer, older]

        rt = OpenFileToolRuntime(
            logger=logger,
            config=_make_config(),
            content_service=content_service,
            tool_manager=tool_manager,
            message_step_logger=message_step_logger,
            agent_file_registry=[],
        )

        result = rt.get_uploaded_documents()

        assert result[0].id == "cont_old"
        assert result[1].id == "cont_new"


# ===================================================================
# report_file_fallback_step
# ===================================================================


@pytest.mark.ai
class TestReportFileFallbackStep:
    @pytest.mark.asyncio
    async def test__creates_log_entry(self, runtime, message_step_logger):
        """
        Purpose: Verify a fallback log entry is created.
        Why this matters: Users need to see a message when file opening fails.
        Setup summary: Call report_file_fallback_step, verify create_message_log_entry called.
        """
        await runtime.report_file_fallback_step()

        message_step_logger.create_message_log_entry_async.assert_called_once()
        call_kwargs = message_step_logger.create_message_log_entry_async.call_args
        assert (
            "too large"
            in call_kwargs.kwargs.get("text", call_kwargs[1].get("text", "")).lower()
            or "too large" in str(call_kwargs).lower()
        )
