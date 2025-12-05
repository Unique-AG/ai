from logging import getLogger
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder

_LOGGER = getLogger(__name__)

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
        description="A notification message to entertain the use about the outcome of the operation. Might briefly highlight key findings or results etc..."
    )
    progress_notification_message: str = Field(
        description="A very short message to update the message of the progress bar."
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
    Generate a SWOT analysis report for a single batch of sources.

    This function processes a batch of sources through the language model to generate
    structured SWOT analysis results. It handles errors gracefully and returns None
    if generation fails.

    Args:
        system_prompt: The system prompt to guide the language model
        batch_parser: Function to convert source batch into text for the LLM
        language_model_service: Service for interacting with language models
        language_model: Language model configuration
        output_model: The Pydantic model class for structured output
        batch: List of sources to process in this batch

    Returns:
        The generated SWOT analysis for this batch, or None if generation failed
    """
    try:
        _LOGGER.info(
            f"Generating structured output with {output_model.__class__.__name__} model"
        )
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_message)
            .build()
        )
        response = await llm_service.complete_async(
            model_name=llm.name,
            messages=messages,
            structured_output_model=output_model,
            structured_output_enforce_schema=True,
        )
        return output_model.model_validate(response.choices[0].message.parsed)
    except Exception as e:
        _LOGGER.exception(f"Error generating report batch: {e}")
