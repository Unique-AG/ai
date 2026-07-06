"""Unit tests for the DocGenerator service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from unique_document_generator.service import (
    DOCX_MIME,
    DocGeneratorTool,
    DocGeneratorToolInput,
)


class TestDocGeneratorToolInput:
    @pytest.mark.ai
    def test_doc_generator_tool_input__stores_explicit_filename__when_provided(self) -> (
        None
    ):
        """
        Purpose: Verify the tool input keeps an explicitly provided filename.
        Why this matters: The generated document should use the caller-selected output name.
        Setup summary: Build the input with markdown and filename, then assert both fields persist.
        """
        # Arrange
        tool_input = DocGeneratorToolInput(
            markdown_content="# Hello",
            filename="test.docx",
        )

        # Act
        result = tool_input

        # Assert
        assert result.markdown_content == "# Hello"
        assert result.filename == "test.docx"

    @pytest.mark.ai
    def test_doc_generator_tool_input__uses_default_filename__when_missing(self) -> None:
        """
        Purpose: Verify the tool input falls back to the default output filename.
        Why this matters: Tool calls without a filename still need a valid DOCX name.
        Setup summary: Build the input with only markdown content and assert the default filename is used.
        """
        # Arrange
        tool_input = DocGeneratorToolInput(markdown_content="# Hello")

        # Act
        result = tool_input.filename

        # Assert
        assert result == "document.docx"

    @pytest.mark.ai
    def test_doc_generator_tool_input__rejects_extra_fields__when_unexpected_data_present(
        self,
    ) -> None:
        """
        Purpose: Verify the tool input forbids unexpected fields.
        Why this matters: Strict validation prevents malformed tool payloads from silently passing through.
        Setup summary: Attempt to construct the input with an unsupported field and assert validation fails.
        """
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            DocGeneratorToolInput.model_validate(
                {
                    "markdown_content": "# Hello",
                    "unexpected_field": "value",
                }
            )


class TestDocGeneratorToolDescription:
    @pytest.mark.ai
    def test_doc_generator_tool__tool_description__returns_doc_generator_name(self) -> (
        None
    ):
        """
        Purpose: Verify the exposed tool description uses the registered tool name.
        Why this matters: The orchestrator and UI rely on the exact tool name for configuration and execution.
        Setup summary: Build the tool, request its language-model description, and assert the name matches.
        """
        # Arrange
        tool = _build_tool()

        # Act
        description = tool.tool_description()

        # Assert
        assert description.name == "DocGenerator"

    @pytest.mark.ai
    def test_doc_generator_tool__tool_description__uses_configured_description(self) -> (
        None
    ):
        """
        Purpose: Verify the tool description text comes from configuration.
        Why this matters: Space admins need prompt customization to reach the model unchanged.
        Setup summary: Build the tool with a custom description and assert it is returned verbatim.
        """
        # Arrange
        tool = _build_tool(tool_description="Custom desc")

        # Act
        description = tool.tool_description()

        # Assert
        assert description.description == "Custom desc"

    @pytest.mark.ai
    def test_doc_generator_tool__format_information_for_system_prompt__uses_configured_text(
        self,
    ) -> None:
        """
        Purpose: Verify the system-prompt formatting text comes from configuration.
        Why this matters: Extra formatting instructions should be appended exactly as configured.
        Setup summary: Build the tool with custom format guidance and assert the getter returns it unchanged.
        """
        # Arrange
        tool = _build_tool(
            tool_format_information_for_system_prompt="Use a title and summary."
        )

        # Act
        result = tool.tool_format_information_for_system_prompt()

        # Assert
        assert result == "Use a title and summary."


class TestDocGeneratorToolRun:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_doc_generator_tool__run__uploads_document_and_attaches_reference__with_valid_markdown(
        self, sample_markdown: str
    ) -> None:
        """
        Purpose: Verify a valid tool call renders DOCX bytes, uploads them, and attaches a download reference.
        Why this matters: This is the primary user flow for generating a downloadable Word document in chat.
        Setup summary: Mock pandoc conversion and chat upload calls, run the tool, and assert upload plus reference attachment behavior.
        """
        # Arrange
        tool = _build_tool()
        tool_call = _make_tool_call(
            markdown_content=sample_markdown,
            filename="Report.docx",
        )
        fake_docx = b"PK\x03\x04fake-docx-bytes"
        mock_content = MagicMock(id="cont_abc123")

        with patch(
            "unique_document_generator.service.pandoc_markdown_to_docx_async",
            new_callable=AsyncMock,
            return_value=fake_docx,
        ) as mock_pandoc:
            tool._chat_service.upload_to_chat_from_bytes_async = AsyncMock(
                return_value=mock_content
            )
            tool._chat_service.modify_assistant_message_async = AsyncMock()

            # Act
            result = await tool.run(tool_call)

        # Assert
        mock_pandoc.assert_awaited_once_with(
            source=sample_markdown,
            template=None,
        )
        tool._chat_service.upload_to_chat_from_bytes_async.assert_awaited_once_with(
            content=fake_docx,
            content_name="Report.docx",
            mime_type=DOCX_MIME,
            skip_ingestion=True,
            hide_in_chat=True,
        )
        tool._chat_service.modify_assistant_message_async.assert_awaited_once()
        assert result.successful
        assert "<sup>1</sup>" in result.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_doc_generator_tool__run__passes_template_to_pandoc__when_template_content_id_configured(
        self, sample_markdown: str
    ) -> None:
        """
        Purpose: Verify the tool loads and applies a configured DOCX template.
        Why this matters: Branded exports depend on passing the stored template bytes to pandoc.
        Setup summary: Mock template download and pandoc conversion, run the tool, and assert the downloaded template is forwarded.
        """
        # Arrange
        template_bytes = b"PK\x03\x04template"
        tool = _build_tool(template_content_id="cont_tmpl")
        tool._knowledge_base_service.download_content_to_bytes = MagicMock(
            return_value=template_bytes
        )
        tool_call = _make_tool_call(markdown_content=sample_markdown)

        with patch(
            "unique_document_generator.service.pandoc_markdown_to_docx_async",
            new_callable=AsyncMock,
            return_value=b"PK\x03\x04docx",
        ) as mock_pandoc:
            tool._chat_service.upload_to_chat_from_bytes_async = AsyncMock(
                return_value=MagicMock(id="cont_out")
            )
            tool._chat_service.modify_assistant_message_async = AsyncMock()

            # Act
            result = await tool.run(tool_call)

        # Assert
        mock_pandoc.assert_awaited_once_with(
            source=sample_markdown,
            template=template_bytes,
        )
        assert result.successful

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_doc_generator_tool__run__returns_error__when_markdown_is_blank(
        self,
    ) -> None:
        """
        Purpose: Verify the tool rejects blank markdown content.
        Why this matters: Empty documents create a poor UX and should fail fast with a clear validation message.
        Setup summary: Call the tool with whitespace-only markdown and assert an error response is returned.
        """
        # Arrange
        tool = _build_tool()
        tool_call = _make_tool_call(markdown_content="  ")

        # Act
        result = await tool.run(tool_call)

        # Assert
        assert not result.successful
        assert "markdown_content" in result.error_message

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_doc_generator_tool__run__appends_docx_extension__when_filename_has_no_suffix(
        self, sample_markdown: str
    ) -> None:
        """
        Purpose: Verify the tool normalizes filenames without a DOCX extension.
        Why this matters: Generated uploads need a valid `.docx` name even when the caller omits the suffix.
        Setup summary: Run the tool with a bare filename and assert the upload uses the normalized DOCX name.
        """
        # Arrange
        tool = _build_tool()
        tool_call = _make_tool_call(
            markdown_content=sample_markdown,
            filename="report",
        )

        with patch(
            "unique_document_generator.service.pandoc_markdown_to_docx_async",
            new_callable=AsyncMock,
            return_value=b"PK\x03\x04docx",
        ):
            tool._chat_service.upload_to_chat_from_bytes_async = AsyncMock(
                return_value=MagicMock(id="cont_x")
            )
            tool._chat_service.modify_assistant_message_async = AsyncMock()

            # Act
            result = await tool.run(tool_call)

        # Assert
        tool._chat_service.upload_to_chat_from_bytes_async.assert_awaited_once_with(
            content=b"PK\x03\x04docx",
            content_name="report.docx",
            mime_type=DOCX_MIME,
            skip_ingestion=True,
            hide_in_chat=True,
        )
        assert "<sup>1</sup>" in result.content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_doc_generator_tool__run__returns_error__when_arguments_are_not_a_dict(
        self,
    ) -> None:
        """
        Purpose: Verify the tool rejects malformed argument payloads.
        Why this matters: Guarding the entry point prevents runtime failures from invalid orchestrator payloads.
        Setup summary: Pass a non-dict arguments value and assert the tool returns an invalid-arguments error.
        """
        # Arrange
        tool = _build_tool()
        tool_call = MagicMock()
        tool_call.id = "call_bad"
        tool_call.arguments = "not a dict"

        # Act
        result = await tool.run(tool_call)

        # Assert
        assert not result.successful
        assert "Invalid" in result.error_message

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_doc_generator_tool__run__falls_back_to_default_styling__when_template_download_fails(
        self, sample_markdown: str
    ) -> None:
        """
        Purpose: Verify template download failures do not block document generation.
        Why this matters: A broken template reference should degrade gracefully instead of breaking the tool.
        Setup summary: Make template download raise, run the tool, and assert pandoc falls back to `None` for the template.
        """
        # Arrange
        tool = _build_tool(template_content_id="cont_broken")
        tool._knowledge_base_service.download_content_to_bytes = MagicMock(
            side_effect=RuntimeError("404")
        )
        tool_call = _make_tool_call(markdown_content=sample_markdown)

        with patch(
            "unique_document_generator.service.pandoc_markdown_to_docx_async",
            new_callable=AsyncMock,
            return_value=b"PK\x03\x04docx",
        ) as mock_pandoc:
            tool._chat_service.upload_to_chat_from_bytes_async = AsyncMock(
                return_value=MagicMock(id="cont_y")
            )
            tool._chat_service.modify_assistant_message_async = AsyncMock()

            # Act
            result = await tool.run(tool_call)

        # Assert
        mock_pandoc.assert_awaited_once_with(source=sample_markdown, template=None)
        assert result.successful


def _build_tool(**config_overrides: object) -> DocGeneratorTool:
    from unique_document_generator.config import DocGeneratorToolConfig

    config = DocGeneratorToolConfig(**config_overrides)
    event = MagicMock()
    event.company_id = "comp_test"
    event.user_id = "user_test"
    event.payload.chat_id = "chat_test"

    with patch.object(
        DocGeneratorTool, "__init__", lambda self, *a, **kw: None
    ):
        tool = DocGeneratorTool.__new__(DocGeneratorTool)

    tool.config = config
    tool.logger = MagicMock()
    tool.debug_info = {}
    tool._event = event
    tool._chat_service = MagicMock()
    tool._language_model_service = MagicMock()
    tool._message_step_logger = MagicMock()
    tool._tool_progress_reporter = None
    tool._knowledge_base_service = MagicMock()

    from unique_toolkit.agentic.tools.config import ToolBuildConfig

    tool.settings = ToolBuildConfig(name="DocGenerator", configuration=config)

    return tool


def _make_tool_call(
    markdown_content: str = "# Test",
    filename: str = "document.docx",
) -> MagicMock:
    call = MagicMock()
    call.id = "call_test_123"
    call.arguments = {
        "markdown_content": markdown_content,
        "filename": filename,
    }
    return call
