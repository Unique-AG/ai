import logging

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override
from unique_toolkit._common.docx_generator import pandoc_markdown_to_docx_async
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.language_model.service import LanguageModelToolDescription
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

from unique_document_generator.config import DocGeneratorToolConfig

_LOGGER = logging.getLogger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DocGeneratorToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown_content: str = Field(
        description="The full markdown text of the document to generate.",
    )
    filename: str = Field(
        default="document.docx",
        description="Output filename, must end with .docx.",
    )


class DocGeneratorTool(Tool[DocGeneratorToolConfig]):
    name = "DocGenerator"

    def __init__(
        self,
        configuration: DocGeneratorToolConfig,
        event: ChatEvent,
        *args,
        **kwargs,
    ):
        super().__init__(configuration, event, *args, **kwargs)
        self._knowledge_base_service = KnowledgeBaseService.from_event(self._event)

    def _get_template(self) -> bytes | None:
        content_id = self.config.template_content_id.strip()
        if not content_id:
            return None
        try:
            return self._knowledge_base_service.download_content_to_bytes(
                content_id=content_id,
            )
        except Exception:
            _LOGGER.warning(
                "Failed to download template %s — falling back to pandoc defaults",
                content_id,
                exc_info=True,
            )
            return None

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=DocGeneratorToolInput,
        )

    @override
    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        if not isinstance(tool_call.arguments, dict):
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message="Invalid tool call arguments",
            )

        markdown_content: str = tool_call.arguments.get("markdown_content", "")
        filename: str = tool_call.arguments.get("filename", "document.docx")

        if not markdown_content.strip():
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message="markdown_content is required and cannot be empty",
            )

        if not filename.strip().lower().endswith(".docx"):
            filename = filename.rstrip() + ".docx"
        content_name = filename.strip() or "document.docx"

        template = self._get_template()

        docx_bytes = await pandoc_markdown_to_docx_async(
            source=markdown_content,
            template=template,
        )

        content = await self._chat_service.upload_to_chat_from_bytes_async(
            content=docx_bytes,
            content_name=content_name,
            mime_type=DOCX_MIME,
            skip_ingestion=True,
            hide_in_chat=True,
        )

        ref_number = 1
        reference = ContentReference(
            name=content_name,
            url=f"unique://content/{content.id}",
            sequence_number=ref_number,
            source="document-generator",
            source_id=content.id,
        )

        await self._chat_service.modify_assistant_message_async(
            references=[reference],
        )

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content=(
                f"Document generated successfully. "
                f"Use this exact download link in your response: <sup>{ref_number}</sup>"
            ),
        )

    @override
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    @override
    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []


ToolFactory.register_tool(
    tool=DocGeneratorTool, tool_config=DocGeneratorToolConfig
)
