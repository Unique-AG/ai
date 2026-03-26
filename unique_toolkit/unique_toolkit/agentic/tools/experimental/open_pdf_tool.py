from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import BaseToolConfig, ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class OpenPdfTool(Tool[BaseToolConfig]):
    """Tool that lets the agent open a knowledge-base PDF so the full document
    is included in the LLM payload (unique://content/<id> URL).

    The agent calls this with the content_id it sees in search results.  The
    shared registry is then read by UniqueAI._collect_content_file_parts() on
    every subsequent loop iteration.
    """

    name = "OpenPdf"

    def __init__(
        self,
        event: ChatEvent,
        registry: list[str],
    ) -> None:
        super().__init__(BaseToolConfig(), event)
        self._registry = registry

    def display_name(self) -> str:
        return "Open PDF"

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=(
                "Open one or more PDF documents so you can read and reason over their "
                "full content. ALWAYS call this tool for any PDF you want to answer "
                "questions about — the text chunks from InternalSearch are lossy extracts "
                "and miss tables, charts, layout, and context. Opening the full PDF gives "
                "you far superior information.\n\n"
                "How to find the content_id:\n"
                "- After an InternalSearch call, each PDF source includes a 'content_id' "
                "field (starts with 'cont_'). Use that value.\n"
                "- The document name is shown inside <|document|>…<|/document|> tags in "
                "the search result content, e.g. "
                "'<|document|>Report.pdf<|/document|>'.\n\n"
                "Only PDF documents are supported. "
                "The opened files will be available in all subsequent iterations."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "content_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of content_ids of the PDF documents to open. "
                            "Each content_id is found in search results as the "
                            "'content_id' field (starts with 'cont_'). "
                            "Only PDF documents are supported."
                        ),
                    }
                },
                "required": ["content_ids"],
            },
        )

    def tool_description_for_system_prompt(self) -> str:
        return (
            "When the user asks you to work with, analyze, summarize, or reason over a "
            "PDF document, you MUST open it with OpenPdf before answering. "
            "The text chunks returned by InternalSearch are extracted fragments — they lose "
            "tables, charts, formatting, and cross-page context. Opening the full PDF gives "
            "you the complete document with all visual and structural information intact.\n\n"
            "Workflow:\n"
            "1. Use InternalSearch to find relevant documents and identify their content_ids.\n"
            "2. Call OpenPdf with the content_ids of the PDFs you need.\n"
            "3. The full PDFs will be available in the next iteration for you to read.\n"
            "4. Answer the user's question using the full PDF content, referencing the "
            "InternalSearch source numbers for citations.\n\n"
            "You should still cite source numbers from InternalSearch in your answer "
            "(e.g. [source0]), but base your reasoning on the full opened PDF when available."
        )

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        args = tool_call.arguments or {}
        content_ids: list[str] = args.get("content_ids", [])

        if not isinstance(content_ids, list) or not content_ids:
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message="content_ids must be a non-empty list of content IDs.",
            )

        invalid = [cid for cid in content_ids if not cid.startswith("cont_")]
        if invalid:
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message=(
                    f"Invalid content_id(s): {invalid}. "
                    "All IDs must start with 'cont_'."
                ),
            )

        added = []
        for content_id in content_ids:
            if content_id not in self._registry:
                self._registry.append(content_id)
                added.append(content_id)

        already = [cid for cid in content_ids if cid not in added]
        parts = []
        if added:
            parts.append(f"Added: {added}")
        if already:
            parts.append(f"Already registered: {already}")

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content=f"Files will be included in the LLM context. {' | '.join(parts)}",
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []


ToolFactory.register_tool(OpenPdfTool, BaseToolConfig)