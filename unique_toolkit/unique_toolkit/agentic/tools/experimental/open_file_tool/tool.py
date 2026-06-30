from typing import overload

from typing_extensions import deprecated

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.experimental.open_file_tool.config import (
    OpenFileToolConfig,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)


class OpenFileTool(Tool[OpenFileToolConfig]):
    """Tool that lets the agent open a knowledge-base file so the full document
    is included in the LLM payload (unique://content/<id> URL).

    The agent calls this with the content_id it sees in search results.  The
    shared registry is then read by OpenFileToolRuntime on every subsequent
    loop iteration.
    """

    name = "OpenFile"

    @overload
    def __init__(
        self,
        config: OpenFileToolConfig,
        registry: list[str],
        *,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    @overload
    @deprecated(
        "Passing event is deprecated. Inject chat_service and language_model_service."
    )
    def __init__(
        self,
        config: OpenFileToolConfig,
        registry: list[str],
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = ...,
    ) -> None: ...

    def __init__(
        self,
        config: OpenFileToolConfig,
        registry: list[str],
        event: ChatEvent | None = None,
        tool_progress_reporter: ToolProgressReporter | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
    ) -> None:
        if chat_service is not None and language_model_service is not None:
            super().__init__(
                config,
                tool_progress_reporter=tool_progress_reporter,
                chat_service=chat_service,
                language_model_service=language_model_service,
            )
        elif event is not None:
            super().__init__(config, event, tool_progress_reporter)
        else:
            raise ValueError(
                "OpenFileTool requires event or injected chat_service and "
                "language_model_service"
            )
        self._registry = registry

    def display_name(self) -> str:
        return "Open File"

    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters={
                "type": "object",
                "properties": {
                    "content_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": self.config.tool_parameter_description_content_ids,
                    }
                },
                "required": ["content_ids"],
            },
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        args = tool_call.arguments or {}
        content_ids: list[str] = args.get("content_ids", [])

        if not isinstance(content_ids, list) or not content_ids:  # pyright: ignore[reportUnnecessaryIsInstance]
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


ToolFactory.register_tool(OpenFileTool, OpenFileToolConfig)
