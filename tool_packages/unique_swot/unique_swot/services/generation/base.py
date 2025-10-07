"""
SWOT Analysis Report Generation Base Module

This module provides the core infrastructure for generating SWOT analysis reports.
It handles batching of large datasets, token management, and structured output generation
using language models. The system is designed to process large amounts of source data
efficiently by splitting it into manageable batches.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import getLogger
from typing import Callable, Generic, Sequence, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field
from tiktoken import get_encoding
from unique_toolkit import LanguageModelService
from unique_toolkit._common.default_language_model import (
    DEFAULT_GPT_4o,
)
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_swot.services.notifier import Notifier
from unique_swot.services.schemas import Source

logger = getLogger(__name__)

_DEFAULT_LANGUAGE_MODEL = DEFAULT_GPT_4o
_DEFAULT_BATCH_SIZE = 3
_DEFAULT_MAX_TOKENS_PER_BATCH = 30_000

# Generic type variable for ReportGenerationOutputModel subclasses
T = TypeVar("T", bound="ReportGenerationOutputModel")


class ReportGenerationConfig(BaseModel):
    """
    Configuration settings for SWOT report generation.

    Controls the language model, batching behavior, and token limits for report generation.

    Attributes:
        language_model: The language model to use for generation
        batch_size: Number of sources to process in each batch
        max_tokens_per_batch: Maximum tokens allowed per batch to prevent overflow
    """

    model_config = get_configuration_dict()

    language_model: LMI = get_LMI_default_field(_DEFAULT_LANGUAGE_MODEL)
    batch_size: int = Field(default=_DEFAULT_BATCH_SIZE)
    max_tokens_per_batch: int = Field(default=_DEFAULT_MAX_TOKENS_PER_BATCH)


class ReportGenerationOutputModel(BaseModel, ABC, Generic[T]):
    """
    Abstract base class for SWOT analysis output models.

    This class defines the interface that all SWOT analysis output models must implement.
    It provides a generic framework for combining multiple batches of analysis results
    into a single comprehensive report.

    Attributes:
        model_config: Pydantic configuration to forbid extra fields
    """

    model_config = ConfigDict(extra="forbid")

    @classmethod
    @abstractmethod
    def group_batches(cls, batches: Sequence[T]) -> T:
        """
        Combine multiple batches of the same type into a single instance.

        This method is crucial for processing large datasets that need to be split
        into multiple batches due to token limits. Each batch generates partial results
        that must be combined into a final comprehensive report.

        Args:
            batches: Sequence of instances of the same type to combine

        Returns:
            A single combined instance of the same type
        """
        raise NotImplementedError


@dataclass
class ReportGenerationContext(Generic[T]):
    """
    Context information for generating SWOT analysis reports.

    Contains all the necessary information to generate a report for a specific
    SWOT component (Strengths, Weaknesses, Opportunities, or Threats).

    Attributes:
        step_name: Name of the SWOT analysis step being executed
        system_prompt: The system prompt to guide the language model
        sources: List of data sources to analyze
        output_model: The Pydantic model class for structured output
    """

    step_name: str
    system_prompt: str
    sources: list[Source]
    output_model: type[T]


async def generate_report(
    *,
    context: ReportGenerationContext[T],
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: Notifier,
    batch_parser: Callable[[list[Source]], str],
) -> T:
    """
    Generate a SWOT analysis report by processing sources in batches.

    This function handles the complete workflow of report generation:
    1. Splits sources into manageable batches based on token limits
    2. Processes each batch with the language model
    3. Combines results from all batches into a final report
    4. Provides progress notifications throughout the process

    Args:
        context: The generation context containing sources and configuration
        configuration: Report generation settings (batching, model, etc.)
        language_model_service: Service for interacting with language models
        notifier: Service for sending progress notifications
        batch_parser: Function to convert source batches into text for the LLM

    Returns:
        The generated SWOT analysis report
    """
    batches = _split_context_into_batches(
        sources=context.sources,
        batch_size=configuration.batch_size,
        max_tokens_per_batch=configuration.max_tokens_per_batch,
        language_model=configuration.language_model,
    )
    report_batches = []
    for i, batch in enumerate(batches):
        report_batch = await _generate_report_batch(
            system_prompt=context.system_prompt,
            batch_parser=batch_parser,
            language_model_service=language_model_service,
            language_model=configuration.language_model,
            output_model=context.output_model,
            batch=batch,
        )
        notifier.notify(
            step_name=context.step_name,
            progress=i / len(batches),
        )
        if report_batch is None:
            continue
        report_batches.append(report_batch)

    # Make sure to notify the progress to 1.0
    notifier.notify(
        step_name=context.step_name,
        progress=1.0,
    )
    return cast(T, context.output_model.group_batches(report_batches))


@dataclass
class ReportModifyContext(Generic[T]):
    """
    Context information for modifying existing SWOT analysis reports.

    Contains the information needed to modify an already-generated SWOT analysis
    based on new sources or specific instructions.

    Attributes:
        step_name: Name of the SWOT analysis step being modified
        system_prompt: The system prompt to guide the language model
        modify_instruction: Specific instruction for how to modify the report
        structured_report: The existing report to be modified
        sources: List of new data sources to incorporate
    """

    step_name: str
    system_prompt: str
    modify_instruction: str
    structured_report: T
    sources: list[Source]


async def modify_report(
    *,
    context: ReportModifyContext[T],
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: Notifier,
) -> T:
    """
    Modify an existing SWOT analysis report.

    This function is designed to update an existing SWOT analysis with new information
    or specific modifications. Currently not implemented.

    Args:
        context: The modification context containing the existing report and instructions
        configuration: Report generation settings
        language_model_service: Service for interacting with language models
        notifier: Service for sending progress notifications

    Returns:
        The modified SWOT analysis report

    Raises:
        NotImplementedError: This functionality is not yet implemented
    """
    raise NotImplementedError("Not implemented")


def _split_context_into_batches(
    *,
    sources: list[Source],
    batch_size: int,
    max_tokens_per_batch: int,
    language_model: LMI,
) -> list[list[Source]]:
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
    groups = []
    current_group = []
    current_group_size = 0
    encoding = get_encoding(language_model.encoder_name)
    for i in range(0, len(sources), batch_size):
        # Check if the current group size plus the size of the next context item is greater than the max tokens per batch
        if (
            current_group_size + len(encoding.encode(sources[i].content))
            > max_tokens_per_batch
        ):
            groups.append(current_group)
            current_group = []
            current_group_size = 0
        current_group.append(sources[i])
        current_group_size += len(encoding.encode(sources[i].content))
    groups.append(current_group)
    return groups


async def _generate_report_batch(
    *,
    system_prompt: str,
    batch_parser: Callable[[list[Source]], str],
    language_model_service: LanguageModelService,
    language_model: LMI,
    output_model: type[T],
    batch: list[Source],
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
        logger.exception(f"Error generating report batch: {e}")
