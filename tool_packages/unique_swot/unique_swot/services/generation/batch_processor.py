from logging import getLogger
from typing import Callable

from pydantic import BaseModel, Field
from tiktoken import get_encoding
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_swot.services.collection.schema import Source, SourceChunk
from unique_swot.services.generation.models import SWOTExtractionModel

_LOGGER = getLogger(__name__)


class SourceBatchs(BaseModel):
    source: Source
    batches: list[list[SourceChunk]] = Field(default_factory=list)


def split_context_into_batches(
    *,
    sources: list[Source],
    batch_size: int,
    max_tokens_per_batch: int,
    language_model: LMI,
) -> list[SourceBatchs]:
    """
    Split sources into batches based on token limits and batch size.

    This function ensures that each batch doesn't exceed the maximum token limit
    while respecting the desired batch size. It uses the language model's encoder
    to accurately count tokens for each source.

    Args:
        sources: List of data sources to split into batches
        batch_size: Maximum number of sources per batch
        max_tokens_per_batch: Maximum tokens allowed per batch
        language_model: Language model configuration for token encoding

    Returns:
        List of source batches, each containing sources that fit within token limits
    """
    source_batches: list[SourceBatchs] = []
    encoding = get_encoding(language_model.encoder_name)

    for source in sources:
        current_source = SourceBatchs(source=source)
        current_batch: list[SourceChunk] = []
        current_batch_size = 0
        for chunk in source.chunks:
            chunk_size = len(encoding.encode(chunk.text))

            # If adding this chunk would exceed the limit, finalize current group and start a new one
            if (
                current_batch_size + chunk_size > max_tokens_per_batch
                or len(current_batch) >= batch_size
            ):
                current_source.batches.append(current_batch)
                current_batch = [chunk]
                current_batch_size = chunk_size
            else:
                current_batch.append(chunk)
                current_batch_size += chunk_size

        # Add any remaining chunks in the current group
        if current_batch:
            current_source.batches.append(current_batch)

        source_batches.append(current_source)

    _LOGGER.info(
        f"Split sources into {len(source_batches)} batches out of {len(sources)} sources"
    )
    return source_batches


async def extract_swot_from_source_batch(
    *,
    system_prompt: str,
    batch_parser: Callable[[list[SourceChunk]], str],
    language_model_service: LanguageModelService,
    language_model: LMI,
    output_model: type[SWOTExtractionModel],
    batch: list[SourceChunk],
) -> SWOTExtractionModel | None:
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
        _LOGGER.info(f"Generating report batch with {len(batch)} chunks")
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(batch_parser(batch))
            .build()
        )
        response = await language_model_service.complete_async(
            model_name=language_model.name,
            messages=messages,
            structured_output_model=output_model,
            structured_output_enforce_schema=True,
        )
        return output_model.model_validate(response.choices[0].message.parsed)
    except Exception as e:
        _LOGGER.exception(f"Error generating report batch: {e}")


async def summarize_swot_extraction_results(
    *,
    system_prompt: str,
    language_model_service: LanguageModelService,
    language_model: LMI,
    extraction_output_model: SWOTExtractionModel,
) -> str:
    """
    Summarize a SWOT extraction report.
    """
    try:
        _LOGGER.info(
            f"Summarizing report from {extraction_output_model.__class__.__name__} model"
        )
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(extraction_output_model.model_dump_json())
            .build()
        )
        response = await language_model_service.complete_async(
            model_name=language_model.name,
            messages=messages,
        )
        text_response = response.choices[0].message.content

        assert isinstance(text_response, str), (
            f"Expected a string, got {type(text_response)}"
        )

        return text_response
    except Exception as e:
        _LOGGER.exception(f"Error summarizing report: {e}")
        return f"Unavailable summary due to error: {e}"
