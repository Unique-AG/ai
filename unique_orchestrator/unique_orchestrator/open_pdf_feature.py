from __future__ import annotations

from datetime import datetime, timezone
from logging import Logger
from typing import TYPE_CHECKING, Any

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    ToolManager,
)
from unique_toolkit.content.schemas import Content
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

if TYPE_CHECKING:
    from unique_orchestrator.config import UniqueAIConfig


class OpenPdfFeatureRuntime:
    """Runtime helper for the experimental OpenPdf payload flow."""

    _OPEN_PDF_TOOL_NAME = "OpenPdf"
    _RETRY_SIGNALS = (
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
    )
    _PDF_TOO_LARGE_TOOL_RESPONSE = (
        "ERROR: The PDF file is too large to open. "
        "Could not include the document in the context. "
        "Please inform the user that the file is too large to process directly "
        "and suggest asking an admin to include the document in the knowledge base."
    )
    _OPEN_PDF_SYSTEM_REMINDER = (
        "<|system_reminder|>PDF documents were found in the search results. "
        "For any PDF you want to reference or reason over, call the OpenPdf tool "
        "with the content_id from the search results. The document name is shown "
        "inside <|document|>...<|/document|> tags in the content field. "
        "The full PDF provides far better information than the extracted text "
        "chunks (tables, charts, layout, and cross-page context are preserved)."
        "<|/system_reminder|>"
    )

    def __init__(
        self,
        logger: Logger,
        config: UniqueAIConfig,
        content_service: Any,
        tool_manager: ResponsesApiToolManager | ToolManager,
        message_step_logger: MessageStepLogger,
        agent_file_registry: list[str],
    ) -> None:
        self._logger = logger
        self._config = config
        self._content_service = content_service
        self._tool_manager = tool_manager
        self._message_step_logger = message_step_logger
        self._agent_file_registry = agent_file_registry
        self._cached_uploaded_documents: list[Content] | None = None
        self._pdf_payload_attachments_disabled = False

    def should_attach_content_files(self) -> bool:
        if self._pdf_payload_attachments_disabled:
            return False

        return self._is_feature_enabled() and (
            self._kb_pdf_payload_enabled() or self._uploaded_pdf_payload_enabled()
        )

    def inject_content_files_into_user_message(
        self, messages: LanguageModelMessages
    ) -> LanguageModelMessages:
        file_parts = self._collect_content_file_parts()
        if not file_parts:
            return messages

        for index in range(len(messages.root) - 1, -1, -1):
            message = messages.root[index]
            if message.role != LanguageModelMessageRole.USER:
                continue

            content_parts: list[dict[str, str]] = []
            if isinstance(message.content, str):
                content_parts.append({"type": "text", "text": message.content})
            elif isinstance(message.content, list):
                content_parts.extend(
                    part
                    for part in message.content
                    if isinstance(part, dict)
                    and part.get("type") in ("text", "input_text")
                    and isinstance(part.get("text"), str)
                )

            if not content_parts:
                content_parts = [{"type": "text", "text": ""}]

            messages.root[index] = LanguageModelUserMessage(
                content=content_parts + file_parts
            )
            break

        return messages

    def should_retry_without_pdf_files(self, exc: Exception) -> bool:
        if self._pdf_payload_attachments_disabled:
            return False
        if not self._is_feature_enabled():
            return False
        if (
            not self._kb_pdf_payload_enabled()
            and not self._uploaded_pdf_payload_enabled()
        ):
            return False

        has_kb_pdfs = self._kb_pdf_payload_enabled() and bool(self._agent_file_registry)
        has_uploaded_pdfs = self._uploaded_pdf_payload_enabled() and bool(
            self._get_uploaded_documents()
        )
        if not has_kb_pdfs and not has_uploaded_pdfs:
            return False

        error_text = str(exc).lower()
        return any(signal in error_text for signal in self._RETRY_SIGNALS)

    def prepare_retry_messages(
        self, messages: LanguageModelMessages
    ) -> LanguageModelMessages:
        self._tool_manager.remove_tool(self._OPEN_PDF_TOOL_NAME)
        self._pdf_payload_attachments_disabled = True

        messages = self.strip_file_parts_from_messages(messages)

        if self._kb_pdf_payload_enabled():
            self._strip_open_pdf_messages(messages)
        if self._uploaded_pdf_payload_enabled():
            self._inject_uploaded_pdf_fallback_messages(messages)

        self._agent_file_registry.clear()
        return messages

    async def report_pdf_fallback_step(self) -> None:
        self._message_step_logger.create_message_log_entry(
            text=(
                "**Open PDF:** The PDF file is too large to open. "
                "Please ask an admin to include the document in the knowledge base."
            ),
            references=[],
        )

    def filter_evaluation_names(
        self, evaluation_names: list[EvaluationMetricName]
    ) -> list[EvaluationMetricName]:
        if not self._agent_file_registry:
            return evaluation_names

        filtered_names = [
            name
            for name in evaluation_names
            if name != EvaluationMetricName.HALLUCINATION
        ]
        if len(filtered_names) != len(evaluation_names):
            self._logger.info(
                "OpenPdf was used - skipping hallucination check "
                "(LLM has full PDF content, not just search chunks)."
            )
        return filtered_names

    def inject_open_pdf_reminder(self, tool_call_responses: list[Any]) -> None:
        if not self._tool_manager.get_tool_by_name(self._OPEN_PDF_TOOL_NAME):
            return

        for response in tool_call_responses:
            if response.name != "InternalSearch":
                continue

            has_pdf_chunks = any(
                chunk.key and chunk.key.split(" : ")[0].lower().endswith(".pdf")
                for chunk in (response.content_chunks or [])
            )
            if not has_pdf_chunks:
                continue

            existing_reminder = response.system_reminder or ""
            response.system_reminder = (
                f"{existing_reminder}\n{self._OPEN_PDF_SYSTEM_REMINDER}".strip()
            )

    def get_uploaded_documents(self) -> list[Content]:
        return self._get_uploaded_documents()

    @staticmethod
    def strip_file_parts_from_messages(
        messages: LanguageModelMessages,
    ) -> LanguageModelMessages:
        for index, message in enumerate(messages.root):
            if message.role != LanguageModelMessageRole.USER:
                continue
            if not isinstance(message.content, list):
                continue

            text_parts = [
                part
                for part in message.content
                if isinstance(part, dict) and part.get("type") in ("text", "input_text")
            ]
            if not text_parts:
                continue

            text = " ".join(part.get("text", "") for part in text_parts).strip()
            messages.root[index] = LanguageModelUserMessage(content=text)

        return messages

    def _is_feature_enabled(self) -> bool:
        return self._responses_api_enabled() and self._pdf_config.enabled

    def _responses_api_enabled(self) -> bool:
        responses_config = self._config.agent.experimental.responses_api_config
        return (
            responses_config.use_responses_api
            or self._config.agent.experimental.use_responses_api
        )

    @property
    def _pdf_config(self):  # noqa: ANN202
        return self._config.agent.experimental.open_pdf_tool_config

    def _kb_pdf_payload_enabled(self) -> bool:
        return self._pdf_config.send_pdf_files_in_payload

    def _uploaded_pdf_payload_enabled(self) -> bool:
        return self._pdf_config.send_uploaded_pdf_in_payload

    def _get_uploaded_documents(self) -> list[Content]:
        if self._cached_uploaded_documents is None:
            now = datetime.now(timezone.utc)
            all_documents = self._content_service.get_documents_uploaded_to_chat()
            uploaded_documents = [
                document
                for document in all_documents
                if (document.expired_at is None or document.expired_at > now)
                and document.key.lower().endswith(".pdf")
            ]
            # Preserve upload order for payload file parts so the first uploaded
            # document remains the first file the model sees.
            self._cached_uploaded_documents = sorted(
                uploaded_documents,
                key=lambda document: (
                    document.created_at is None,
                    document.created_at or datetime.max.replace(tzinfo=timezone.utc),
                ),
            )
        return self._cached_uploaded_documents

    def _collect_content_file_parts(self) -> list[dict[str, dict[str, str] | str]]:
        if self._pdf_payload_attachments_disabled:
            return []

        seen_ids: set[str] = set()
        file_parts: list[dict[str, dict[str, str] | str]] = []

        if self._uploaded_pdf_payload_enabled():
            for document in self._get_uploaded_documents():
                if not document.id or document.id in seen_ids:
                    continue

                seen_ids.add(document.id)
                file_parts.append(
                    {
                        "type": "file",
                        "file": {
                            "filename": document.key or document.id,
                            "file_data": f"unique://content/{document.id}",
                        },
                    }
                )

        if self._kb_pdf_payload_enabled():
            for content_id in self._agent_file_registry:
                if content_id in seen_ids:
                    continue

                seen_ids.add(content_id)
                file_parts.append(
                    {
                        "type": "file",
                        "file": {
                            "filename": content_id,
                            "file_data": f"unique://content/{content_id}",
                        },
                    }
                )

        return file_parts

    def _strip_open_pdf_messages(self, messages: LanguageModelMessages) -> None:
        open_pdf_call_ids: set[str] = set()

        for message in messages.root:
            if not isinstance(message, LanguageModelAssistantMessage):
                continue
            if not message.tool_calls:
                continue

            for tool_call in message.tool_calls:
                if tool_call.function.name == self._OPEN_PDF_TOOL_NAME:
                    open_pdf_call_ids.add(tool_call.id or tool_call.function.id)

        if not open_pdf_call_ids:
            return

        messages.root[:] = [
            message
            for message in messages.root
            if not (
                isinstance(message, LanguageModelToolMessage)
                and message.tool_call_id in open_pdf_call_ids
            )
        ]

        for message in messages.root:
            if not isinstance(message, LanguageModelAssistantMessage):
                continue
            if not message.tool_calls:
                continue

            message.tool_calls = [
                tool_call
                for tool_call in message.tool_calls
                if tool_call.function.name != self._OPEN_PDF_TOOL_NAME
            ]

    def _inject_uploaded_pdf_fallback_messages(
        self, messages: LanguageModelMessages
    ) -> None:
        uploaded_documents = self._get_uploaded_documents()
        if not uploaded_documents:
            return

        content_ids = [document.id for document in uploaded_documents if document.id]
        if not content_ids:
            return

        function = LanguageModelFunction(
            name=self._OPEN_PDF_TOOL_NAME,
            arguments={"content_ids": content_ids},
        )
        assistant_message = LanguageModelAssistantMessage.from_functions([function])
        tool_message = LanguageModelToolMessage(
            content=self._PDF_TOO_LARGE_TOOL_RESPONSE,
            name=self._OPEN_PDF_TOOL_NAME,
            tool_call_id=function.id,
        )
        messages.root.append(assistant_message)
        messages.root.append(tool_message)
