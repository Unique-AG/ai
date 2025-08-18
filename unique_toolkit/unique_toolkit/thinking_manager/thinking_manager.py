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
    def __init__(
        self,
        logger: Logger,
        config: ThinkingManagerConfig,
        tool_progress_reporter: ToolProgressReporter,
        chat_service: ChatService,
    ):
        self.chat_service = chat_service
        self.config = config
        self.thinking_steps = ""
        self.thinking_step_number = 1
        self.tool_progress_reporter = tool_progress_reporter

    def thinking_is_displayed(self) -> bool:
        return self.config.thinking_steps_display

    def update_tool_progress_reporter(self, loop_response: LanguageModelStreamResponse):
        if self.config.thinking_steps_display and (
            not loop_response.message.text
            == self.tool_progress_reporter._progress_start_text
        ):
            self.tool_progress_reporter.tool_statuses = {}
            self.tool_progress_reporter._progress_start_text = (
                loop_response.message.text
            )

    def update_start_text(
        self, start_text: str, loop_response: LanguageModelStreamResponse
    ) -> str:
        if not self.config.thinking_steps_display:
            return start_text
        if not loop_response.message.original_text:
            return start_text
        if loop_response.message.original_text == "":
            return start_text

        update_message = loop_response.message.original_text

        if start_text == "":
            self.thinking_steps = f"\n<i><b>Step 1:</b>\n{update_message}</i>\n"
            start_text = f"""<details open>\n<summary><b>Thinking steps</b></summary>\n{self.thinking_steps}\n</details>\n\n---\n\n"""
        else:
            self.thinking_steps += f"\n\n<i><b>Step {self.thinking_step_number}:</b>\n{update_message}</i>\n\n"
            start_text = f"""<details open>\n<summary><b>Thinking steps</b></summary>\n<i>{self.thinking_steps}\n\n</i>\n</details>\n\n---\n\n"""

        self.thinking_step_number += 1
        return start_text

    def close_thinking_steps(self, loop_response: LanguageModelStreamResponse):
        if not self.config.thinking_steps_display:
            return
        if not self.thinking_steps:
            return
        if not loop_response.message.text:
            return
        if not loop_response.message.text.startswith("<details open>"):
            return

        loop_response.message.text = loop_response.message.text.replace(
            "<details open>", "<details>"
        )

        self.chat_service.modify_assistant_message(content=loop_response.message.text)
        return
