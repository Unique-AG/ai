from logging import getLogger
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder

_LOGGER = getLogger(__name__)
_MAX_RETRIES = 3
T = TypeVar("T", bound=BaseModel)


def load_template(parent_dir: Path, template_name: str) -> str:
    """Load a template from a text file."""
    with open(parent_dir / template_name, "r") as file:
        return file.read().strip()


class StructuredOutputResult(BaseModel):
    """This class is responsible for the result of the structured output generation."""

    model_config = ConfigDict(extra="forbid")


class StructuredOutputWithNotification(StructuredOutputResult):
    """This class is responsible for the result of the structured output generation with a notification message."""

    model_config = ConfigDict(extra="forbid")

    notification_message: str = Field(
        description="A notification message to entertain the user with highlighting key findings or results."
    )
    progress_notification_message: str = Field(
        description="A very short message to update the message of the progress bar. Should name the step and give overall statistics or information."
    )


async def generate_structured_output(
    *,
    user_message: str,
    system_prompt: str,
    llm: LMI,
    output_model: type[T],
    llm_service: LanguageModelService,
) -> T | None:
    """
    Call the LLM to produce a structured Pydantic model with retries.

    Returns None when every attempt fails.
    """
    _LOGGER.info(f"Generating structured output with {output_model.__name__} model")

    def _build_messages(error: str | None = None):
        builder = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_message)
        )
        if error:
            builder.user_message_append(
                f"The following error occurred, please retry and fix the error: \n ```{error}```"
            )
        return builder.build()

    last_error = ""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await llm_service.complete_async(
                model_name=llm.name,
                messages=_build_messages(last_error),
                structured_output_model=output_model,
                structured_output_enforce_schema=True,
            )
            return output_model.model_validate(response.choices[0].message.parsed)
        except Exception as exc:
            last_error = str(exc)
            _LOGGER.exception(
                "Error generating structured output (attempt %s/%s): %s",
                attempt,
                _MAX_RETRIES,
                last_error,
            )

    _LOGGER.error(
        "Failed to generate structured output after %s retries: %s",
        _MAX_RETRIES,
        last_error,
    )
    return None
