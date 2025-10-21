from typing import Callable

from tqdm import tqdm
from unique_toolkit import LanguageModelService

from unique_swot.services.collection.schema import SourceChunk
from unique_swot.services.generation.batch_processor import (
    extract_swot_from_source_batch,
    split_context_into_batches,
    summarize_swot_extraction_results,
)
from unique_swot.services.generation.config import ReportGenerationConfig
from unique_swot.services.generation.contexts import (
    ReportGenerationContext,
    ReportModificationContext,
    ReportSummarizationContext,
)
from unique_swot.services.generation.models import SWOTExtractionModel
from unique_swot.services.notifier import Notifier


async def extract_swot_from_sources(
    *,
    context: ReportGenerationContext,
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: Notifier,
    batch_parser: Callable[[list[SourceChunk]], str],
) -> SWOTExtractionModel:
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
    batches = split_context_into_batches(
        sources=context.sources,
        batch_size=configuration.batch_size,
        max_tokens_per_batch=configuration.max_tokens_per_batch,
        language_model=configuration.language_model,
    )

    report_batches = []
    for i, batch in tqdm(
        enumerate(batches),
        total=len(batches),
        desc=f"Generating report {context.step_name}",
    ):
        report_batch = await extract_swot_from_source_batch(
            system_prompt=context.extraction_system_prompt,
            batch_parser=batch_parser,
            language_model_service=language_model_service,
            language_model=configuration.language_model,
            output_model=context.extraction_output_model,
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
    aggregated_extraction_result = context.extraction_output_model.group_batches(
        report_batches
    )

    return aggregated_extraction_result


async def summarize_swot_extraction(
    *,
    context: ReportSummarizationContext,
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: Notifier,
) -> str:
    """
    Summarize a SWOT extraction report.
    """
    summary = await summarize_swot_extraction_results(
        system_prompt=context.summarization_system_prompt,
        language_model_service=language_model_service,
        language_model=configuration.language_model,
        extraction_output_model=context.extraction_results,
    )
    notifier.notify(
        step_name=context.step_name,
        progress=1.0,
    )
    return summary


async def modify_report(
    *,
    context: ReportModificationContext,
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: Notifier,
) -> SWOTExtractionModel:
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
