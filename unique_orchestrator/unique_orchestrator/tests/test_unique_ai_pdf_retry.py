"""Tests for the PDF retry / fallback logic in UniqueAI.

Covers:
- _strip_file_parts_from_messages (static method)
- _strip_open_pdf_messages (KB path: removes tool call + response)
- _inject_uploaded_pdf_fallback_messages (upload path: injects synthetic error)
- _should_retry_without_pdf_files (decision logic)
- _inject_open_pdf_reminder (system reminder on InternalSearch)
- _collect_content_file_parts (gated per flag)
- Full message state before/after retry for both paths
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock

import pytest

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI


def _make_messages(*msgs):
    """Build a LanguageModelMessages from a list of message objects."""
    from unique_toolkit.language_model.schemas import LanguageModelMessages

    return LanguageModelMessages(root=list(msgs))


def _user_msg(content):
    from unique_toolkit.language_model.schemas import LanguageModelUserMessage

    return LanguageModelUserMessage(content=content)


def _assistant_msg_with_tool_calls(tool_calls):
    from unique_toolkit.language_model.schemas import LanguageModelAssistantMessage

    return LanguageModelAssistantMessage.from_functions(tool_calls)


def _tool_msg(name, tool_call_id, content="result"):
    from unique_toolkit.language_model.schemas import LanguageModelToolMessage

    return LanguageModelToolMessage(
        content=content, name=name, tool_call_id=tool_call_id
    )


def _function(name, arguments=None, id=None):
    from unique_toolkit.language_model.schemas import LanguageModelFunction

    kwargs = {"name": name, "arguments": arguments or {}}
    if id:
        kwargs["id"] = id
    return LanguageModelFunction(**kwargs)


@pytest.fixture
def mock_unique_ai(monkeypatch):
    """Create a minimal UniqueAI with mocked dependencies."""
    mock_service_module = MagicMock()
    import sys

    monkeypatch.setitem(
        sys.modules,
        "unique_toolkit.agentic.message_log_manager.service",
        mock_service_module,
    )

    from unique_orchestrator.unique_ai import UniqueAI

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []
    mock_config.agent.experimental.responses_api_config.send_pdf_files_in_payload = False
    mock_config.agent.experimental.responses_api_config.send_uploaded_pdf_in_payload = False
    mock_config.agent.experimental.responses_api_config.use_responses_api = True

    mock_content_service = MagicMock()
    mock_content_service.get_documents_uploaded_to_chat.return_value = []

    ua = UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=MagicMock(),
        content_service=mock_content_service,
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=MagicMock(),
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=MagicMock(),
        agent_file_registry=["cont_kb1"],
    )

    return ua


# ---- _strip_file_parts_from_messages (static) ----


class TestStripFilePartsFromMessages:
    def test_strips_file_parts_keeps_text(self):
        from unique_orchestrator.unique_ai import UniqueAI

        messages = _make_messages(
            _user_msg([
                {"type": "text", "text": "Summarize this"},
                {"type": "file", "file": {"filename": "doc.pdf", "file_data": "unique://content/cont_1"}},
            ])
        )

        result = UniqueAI._strip_file_parts_from_messages(messages)

        assert len(result.root) == 1
        assert result.root[0].content == "Summarize this"

    def test_leaves_string_content_untouched(self):
        from unique_orchestrator.unique_ai import UniqueAI

        messages = _make_messages(_user_msg("plain text"))

        result = UniqueAI._strip_file_parts_from_messages(messages)

        assert result.root[0].content == "plain text"

    def test_preserves_non_user_messages(self):
        from unique_orchestrator.unique_ai import UniqueAI
        from unique_toolkit.language_model.schemas import LanguageModelSystemMessage

        sys_msg = LanguageModelSystemMessage(content="system prompt")
        messages = _make_messages(
            sys_msg,
            _user_msg([
                {"type": "text", "text": "hello"},
                {"type": "file", "file": {"filename": "x.pdf", "file_data": "..."}},
            ]),
        )

        result = UniqueAI._strip_file_parts_from_messages(messages)

        assert result.root[0].content == "system prompt"
        assert result.root[1].content == "hello"

    def test_joins_multiple_text_parts(self):
        from unique_orchestrator.unique_ai import UniqueAI

        messages = _make_messages(
            _user_msg([
                {"type": "text", "text": "Part A"},
                {"type": "file", "file": {"filename": "f.pdf", "file_data": "..."}},
                {"type": "text", "text": "Part B"},
            ])
        )

        result = UniqueAI._strip_file_parts_from_messages(messages)

        assert result.root[0].content == "Part A Part B"


# ---- _strip_open_pdf_messages (KB path) ----


class TestStripOpenPdfMessages:
    def test_removes_open_pdf_tool_call_and_response(self, mock_unique_ai):
        func = _function("OpenPdf", {"content_ids": ["cont_1"]}, id="call_pdf_1")
        messages = _make_messages(
            _user_msg("tell me about the doc"),
            _assistant_msg_with_tool_calls([func]),
            _tool_msg("OpenPdf", "call_pdf_1", "Files included"),
        )

        mock_unique_ai._strip_open_pdf_messages(messages)

        assert len(messages.root) == 2
        assert messages.root[0].content == "tell me about the doc"
        assistant = messages.root[1]
        assert assistant.tool_calls == []

    def test_preserves_non_open_pdf_tool_calls(self, mock_unique_ai):
        search_func = _function("InternalSearch", {"query": "test"}, id="call_search")
        pdf_func = _function("OpenPdf", {"content_ids": ["cont_1"]}, id="call_pdf")
        messages = _make_messages(
            _assistant_msg_with_tool_calls([search_func, pdf_func]),
            _tool_msg("InternalSearch", "call_search", "results"),
            _tool_msg("OpenPdf", "call_pdf", "included"),
        )

        mock_unique_ai._strip_open_pdf_messages(messages)

        assert len(messages.root) == 2
        assistant = messages.root[0]
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].function.name == "InternalSearch"
        assert messages.root[1].name == "InternalSearch"

    def test_no_op_when_no_open_pdf_calls(self, mock_unique_ai):
        messages = _make_messages(
            _user_msg("hello"),
            _assistant_msg_with_tool_calls([_function("InternalSearch", id="c1")]),
            _tool_msg("InternalSearch", "c1"),
        )
        original_len = len(messages.root)

        mock_unique_ai._strip_open_pdf_messages(messages)

        assert len(messages.root) == original_len


# ---- _inject_uploaded_pdf_fallback_messages (upload path) ----


class TestInjectUploadedPdfFallbackMessages:
    def test_injects_synthetic_tool_call_and_error_response(self, mock_unique_ai):
        mock_doc = MagicMock()
        mock_doc.id = "cont_upload1"
        mock_doc.key = "report.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]

        messages = _make_messages(_user_msg("summarize"))

        mock_unique_ai._inject_uploaded_pdf_fallback_messages(messages)

        assert len(messages.root) == 3
        assistant = messages.root[1]
        assert assistant.tool_calls is not None
        assert len(assistant.tool_calls) == 1
        assert assistant.tool_calls[0].function.name == "OpenPdf"
        assert assistant.tool_calls[0].function.arguments == {"content_ids": ["cont_upload1"]}

        tool_response = messages.root[2]
        assert tool_response.name == "OpenPdf"
        assert "too large" in tool_response.content.lower()
        assert tool_response.tool_call_id == assistant.tool_calls[0].id

    def test_no_op_when_no_uploaded_docs(self, mock_unique_ai):
        mock_unique_ai._cached_uploaded_documents = []
        messages = _make_messages(_user_msg("hello"))

        mock_unique_ai._inject_uploaded_pdf_fallback_messages(messages)

        assert len(messages.root) == 1

    def test_skips_docs_without_id(self, mock_unique_ai):
        mock_doc = MagicMock()
        mock_doc.id = ""
        mock_doc.key = "file.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]

        messages = _make_messages(_user_msg("hello"))

        mock_unique_ai._inject_uploaded_pdf_fallback_messages(messages)

        assert len(messages.root) == 1


# ---- _should_retry_without_pdf_files ----


class TestShouldRetryWithoutPdfFiles:
    def test_returns_false_when_both_flags_off(self, mock_unique_ai):
        exc = Exception("413 Request Entity Too Large")
        assert mock_unique_ai._should_retry_without_pdf_files(exc) is False

    def test_returns_true_for_kb_flag_with_registry(self, mock_unique_ai):
        mock_unique_ai._config.agent.experimental.responses_api_config.send_pdf_files_in_payload = True
        exc = Exception("413 Request Entity Too Large")
        assert mock_unique_ai._should_retry_without_pdf_files(exc) is True

    def test_returns_true_for_upload_flag_with_docs(self, mock_unique_ai):
        mock_unique_ai._config.agent.experimental.responses_api_config.send_uploaded_pdf_in_payload = True
        mock_doc = MagicMock()
        mock_doc.id = "cont_up1"
        mock_doc.key = "report.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]
        mock_unique_ai._agent_file_registry = []

        exc = Exception("403 Forbidden from application-gateway")
        assert mock_unique_ai._should_retry_without_pdf_files(exc) is True

    def test_returns_false_when_no_pdfs_in_payload(self, mock_unique_ai):
        mock_unique_ai._config.agent.experimental.responses_api_config.send_pdf_files_in_payload = True
        mock_unique_ai._agent_file_registry = []
        mock_unique_ai._cached_uploaded_documents = []

        exc = Exception("413 Request Entity Too Large")
        assert mock_unique_ai._should_retry_without_pdf_files(exc) is False

    def test_returns_false_for_unrelated_error(self, mock_unique_ai):
        mock_unique_ai._config.agent.experimental.responses_api_config.send_pdf_files_in_payload = True

        exc = Exception("Connection timeout after 30 seconds")
        assert mock_unique_ai._should_retry_without_pdf_files(exc) is False

    @pytest.mark.parametrize(
        "error_text",
        [
            "payload too large",
            "request entity too large",
            "content_length_exceeded",
            "context_length_exceeded",
            "413 error",
            "403 forbidden",
            "application-gateway rejected",
            "max_tokens exceeded",
        ],
    )
    def test_matches_various_error_signals(self, mock_unique_ai, error_text):
        mock_unique_ai._config.agent.experimental.responses_api_config.send_pdf_files_in_payload = True

        exc = Exception(error_text)
        assert mock_unique_ai._should_retry_without_pdf_files(exc) is True


# ---- _inject_open_pdf_reminder ----


class TestInjectOpenPdfReminder:
    def test_appends_reminder_when_pdf_chunks_found(self, mock_unique_ai):
        mock_unique_ai._tool_manager.get_tool_by_name.return_value = MagicMock()

        chunk = MagicMock()
        chunk.key = "report.pdf"
        resp = MagicMock()
        resp.name = "InternalSearch"
        resp.content_chunks = [chunk]
        resp.system_reminder = None

        mock_unique_ai._inject_open_pdf_reminder([resp])

        assert resp.system_reminder is not None
        assert "OpenPdf" in resp.system_reminder

    def test_no_op_when_open_pdf_not_available(self, mock_unique_ai):
        mock_unique_ai._tool_manager.get_tool_by_name.return_value = None

        resp = MagicMock()
        resp.name = "InternalSearch"
        original_reminder = resp.system_reminder

        mock_unique_ai._inject_open_pdf_reminder([resp])

        assert resp.system_reminder == original_reminder

    def test_no_op_for_non_pdf_chunks(self, mock_unique_ai):
        mock_unique_ai._tool_manager.get_tool_by_name.return_value = MagicMock()

        chunk = MagicMock()
        chunk.key = "document.docx"
        resp = MagicMock()
        resp.name = "InternalSearch"
        resp.content_chunks = [chunk]
        resp.system_reminder = None

        mock_unique_ai._inject_open_pdf_reminder([resp])

        assert resp.system_reminder is None

    def test_skips_non_internal_search_responses(self, mock_unique_ai):
        mock_unique_ai._tool_manager.get_tool_by_name.return_value = MagicMock()

        resp = MagicMock()
        resp.name = "UploadedSearch"
        original_reminder = resp.system_reminder

        mock_unique_ai._inject_open_pdf_reminder([resp])

        assert resp.system_reminder == original_reminder


# ---- _collect_content_file_parts ----


class TestCollectContentFileParts:
    def test_returns_uploaded_pdfs_when_upload_flag_on(self, mock_unique_ai):
        cfg = mock_unique_ai._config.agent.experimental.responses_api_config
        cfg.send_uploaded_pdf_in_payload = True
        cfg.send_pdf_files_in_payload = False

        mock_doc = MagicMock()
        mock_doc.id = "cont_up1"
        mock_doc.key = "report.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]
        mock_unique_ai._agent_file_registry = ["cont_kb1"]

        parts = mock_unique_ai._collect_content_file_parts()

        assert len(parts) == 1
        assert parts[0]["file"]["file_data"] == "unique://content/cont_up1"

    def test_returns_kb_pdfs_when_kb_flag_on(self, mock_unique_ai):
        cfg = mock_unique_ai._config.agent.experimental.responses_api_config
        cfg.send_uploaded_pdf_in_payload = False
        cfg.send_pdf_files_in_payload = True

        mock_unique_ai._cached_uploaded_documents = []
        mock_unique_ai._agent_file_registry = ["cont_kb1", "cont_kb2"]

        parts = mock_unique_ai._collect_content_file_parts()

        assert len(parts) == 2
        assert parts[0]["file"]["file_data"] == "unique://content/cont_kb1"
        assert parts[1]["file"]["file_data"] == "unique://content/cont_kb2"

    def test_returns_both_when_both_flags_on(self, mock_unique_ai):
        cfg = mock_unique_ai._config.agent.experimental.responses_api_config
        cfg.send_uploaded_pdf_in_payload = True
        cfg.send_pdf_files_in_payload = True

        mock_doc = MagicMock()
        mock_doc.id = "cont_up1"
        mock_doc.key = "upload.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]
        mock_unique_ai._agent_file_registry = ["cont_kb1"]

        parts = mock_unique_ai._collect_content_file_parts()

        assert len(parts) == 2
        ids = {p["file"]["file_data"] for p in parts}
        assert "unique://content/cont_up1" in ids
        assert "unique://content/cont_kb1" in ids

    def test_deduplicates_across_sources(self, mock_unique_ai):
        cfg = mock_unique_ai._config.agent.experimental.responses_api_config
        cfg.send_uploaded_pdf_in_payload = True
        cfg.send_pdf_files_in_payload = True

        mock_doc = MagicMock()
        mock_doc.id = "cont_same"
        mock_doc.key = "same.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]
        mock_unique_ai._agent_file_registry = ["cont_same"]

        parts = mock_unique_ai._collect_content_file_parts()

        assert len(parts) == 1

    def test_returns_empty_when_both_flags_off(self, mock_unique_ai):
        cfg = mock_unique_ai._config.agent.experimental.responses_api_config
        cfg.send_uploaded_pdf_in_payload = False
        cfg.send_pdf_files_in_payload = False

        mock_unique_ai._agent_file_registry = ["cont_kb1"]

        parts = mock_unique_ai._collect_content_file_parts()

        assert parts == []


# ---- Full message state: before and after retry ----


class TestFullRetryMessageState:
    """End-to-end tests verifying message arrays before and after
    the retry transformations for both KB and upload paths."""

    def test_kb_path__messages_before_and_after(self, mock_unique_ai):
        """KB PDFs: OpenPdf tool call + response stripped entirely.
        LLM falls back to InternalSearch chunks."""
        search_func = _function("InternalSearch", {"query": "q"}, id="c_search")
        pdf_func = _function("OpenPdf", {"content_ids": ["cont_kb1"]}, id="c_pdf")

        messages = _make_messages(
            _user_msg([
                {"type": "text", "text": "Analyze the PDF"},
                {"type": "file", "file": {"filename": "cont_kb1", "file_data": "unique://content/cont_kb1"}},
            ]),
            _assistant_msg_with_tool_calls([search_func]),
            _tool_msg("InternalSearch", "c_search", '[{"source_number": 0, "content": "chunk"}]'),
            _assistant_msg_with_tool_calls([pdf_func]),
            _tool_msg("OpenPdf", "c_pdf", "Files included"),
        )

        assert len(messages.root) == 5

        from unique_orchestrator.unique_ai import UniqueAI

        messages = UniqueAI._strip_file_parts_from_messages(messages)
        mock_unique_ai._strip_open_pdf_messages(messages)
        mock_unique_ai._cached_uploaded_documents = []
        mock_unique_ai._inject_uploaded_pdf_fallback_messages(messages)

        assert messages.root[0].content == "Analyze the PDF"
        assert messages.root[1].tool_calls[0].function.name == "InternalSearch"
        assert messages.root[2].name == "InternalSearch"
        assistant_after = messages.root[3]
        assert assistant_after.tool_calls == []
        assert len(messages.root) == 4

    def test_upload_path__messages_before_and_after(self, mock_unique_ai):
        """Uploaded PDFs: file parts stripped, synthetic OpenPdf error injected."""
        messages = _make_messages(
            _user_msg([
                {"type": "text", "text": "Summarize"},
                {"type": "file", "file": {"filename": "report.pdf", "file_data": "unique://content/cont_up1"}},
            ]),
        )

        assert len(messages.root) == 1

        mock_doc = MagicMock()
        mock_doc.id = "cont_up1"
        mock_doc.key = "report.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]

        from unique_orchestrator.unique_ai import UniqueAI

        messages = UniqueAI._strip_file_parts_from_messages(messages)
        mock_unique_ai._strip_open_pdf_messages(messages)
        mock_unique_ai._inject_uploaded_pdf_fallback_messages(messages)

        assert messages.root[0].content == "Summarize"

        assistant = messages.root[1]
        assert assistant.tool_calls[0].function.name == "OpenPdf"
        assert assistant.tool_calls[0].function.arguments == {"content_ids": ["cont_up1"]}

        tool_resp = messages.root[2]
        assert tool_resp.name == "OpenPdf"
        assert "too large" in tool_resp.content.lower()
        assert tool_resp.tool_call_id == assistant.tool_calls[0].id

        assert len(messages.root) == 3

    def test_both_paths__messages_before_and_after(self, mock_unique_ai):
        """Both KB and uploaded PDFs present: KB stripped, upload error injected."""
        pdf_func = _function("OpenPdf", {"content_ids": ["cont_kb1"]}, id="c_pdf")

        messages = _make_messages(
            _user_msg([
                {"type": "text", "text": "Compare docs"},
                {"type": "file", "file": {"filename": "upload.pdf", "file_data": "unique://content/cont_up1"}},
                {"type": "file", "file": {"filename": "cont_kb1", "file_data": "unique://content/cont_kb1"}},
            ]),
            _assistant_msg_with_tool_calls([pdf_func]),
            _tool_msg("OpenPdf", "c_pdf", "Files included"),
        )

        assert len(messages.root) == 3

        mock_doc = MagicMock()
        mock_doc.id = "cont_up1"
        mock_doc.key = "upload.pdf"
        mock_doc.expired_at = None
        mock_unique_ai._cached_uploaded_documents = [mock_doc]

        from unique_orchestrator.unique_ai import UniqueAI

        messages = UniqueAI._strip_file_parts_from_messages(messages)
        mock_unique_ai._strip_open_pdf_messages(messages)
        mock_unique_ai._inject_uploaded_pdf_fallback_messages(messages)

        assert messages.root[0].content == "Compare docs"

        kb_assistant = messages.root[1]
        assert kb_assistant.tool_calls == []

        upload_assistant = messages.root[2]
        assert upload_assistant.tool_calls[0].function.name == "OpenPdf"
        assert upload_assistant.tool_calls[0].function.arguments == {"content_ids": ["cont_up1"]}

        upload_tool = messages.root[3]
        assert "too large" in upload_tool.content.lower()
        assert upload_tool.tool_call_id == upload_assistant.tool_calls[0].id

        assert len(messages.root) == 4
