from logging import Logger
from pydantic import BaseModel, Field

from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelStreamResponse,
)
from unique_toolkit.tools.tool_progress_reporter import (
    ToolProgressReporter,
)


class ThinkingManagerConfig(BaseModel):
    thinking_steps_display: bool = Field(
        default=True, description="Whether to display thinking steps in the chat."
    )


class ThinkingManager:
    """
    Manages the display and tracking of thinking steps during response generation.

    This class is responsible for:
    - Tracking and formatting thinking steps as part of the response process.
    - Updating the tool progress reporter with the latest thinking step information.
    - Managing the display of thinking steps in the assistant's response.
    - Closing and finalizing the thinking steps section when the process is complete.

    Key Features:
    - Thinking Step Tracking: Maintains a sequential log of thinking steps with step numbers.
    - Configurable Display: Supports enabling or disabling the display of thinking steps based on configuration.
    - Integration with Tool Progress: Updates the tool progress reporter to reflect the current thinking state.
    - Dynamic Response Updates: Modifies the assistant's response to include or finalize thinking steps.
    - Flexible Formatting: Formats thinking steps in a structured and user-friendly HTML-like format.

    The ThinkingManager enhances transparency and user understanding by providing a clear view of the assistant's reasoning process.
    """
    def __init__(
        self,
        logger: Logger,
        config: ThinkingManagerConfig,
        tool_progress_reporter: ToolProgressReporter,
        chat_service: ChatService,
    ):
        self._chat_service = chat_service
        self._config = config
        self._thinking_steps = ""
        self._thinking_step_number = 1
        self._tool_progress_reporter = tool_progress_reporter

    def thinking_is_displayed(self) -> bool:
        return self._config.thinking_steps_display

    def update_tool_progress_reporter(self, loop_response: LanguageModelStreamResponse):
        if self._config.thinking_steps_display and (
            not loop_response.message.text
            == self._tool_progress_reporter._progress_start_text
        ):
            self._tool_progress_reporter.tool_statuses = {}
            self._tool_progress_reporter._progress_start_text = (
                loop_response.message.text
            )

    def update_start_text(
        self, start_text: str, loop_response: LanguageModelStreamResponse
    ) -> str:
        if not self._config.thinking_steps_display:
            return start_text
        if not loop_response.message.original_text:
            return start_text
        if loop_response.message.original_text == "":
            return start_text

        update_message = loop_response.message.original_text

        if start_text == "":
            self._thinking_steps = f"\n<i><b>Step 1:</b>\n{update_message}</i>\n"
            start_text = f"""<details open>\n<summary><b>Thinking steps</b></summary>\n{self._thinking_steps}\n</details>\n\n---\n\n"""
        else:
            self._thinking_steps += f"\n\n<i><b>Step {self._thinking_step_number}:</b>\n{update_message}</i>\n\n"
            start_text = f"""<details open>\n<summary><b>Thinking steps</b></summary>\n<i>{self._thinking_steps}\n\n</i>\n</details>\n\n---\n\n"""

        self._thinking_step_number += 1
        return start_text

    def close_thinking_steps(self, loop_response: LanguageModelStreamResponse):
        if not self._config.thinking_steps_display:
            return
        if not self._thinking_steps:
            return
        if not loop_response.message.text:
            return
        if not loop_response.message.text.startswith("<details open>"):
            return

        loop_response.message.text = loop_response.message.text.replace(
            "<details open>", "<details>"
        )

        self._chat_service.modify_assistant_message(content=loop_response.message.text)
        return
