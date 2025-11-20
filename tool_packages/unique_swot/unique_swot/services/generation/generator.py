from typing import Callable

from jinja2 import Template
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
from unique_swot.services.notifier import (
    MessageLogEvent,
    MessageLogStatus,
    ProgressNotifier,
)


async def extract_swot_from_sources(
    *,
    context: ReportGenerationContext,
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: ProgressNotifier,
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
    source_batches = split_context_into_batches(
        sources=context.sources,
        batch_size=configuration.extraction_batch_size,
        max_tokens_per_batch=configuration.max_tokens_per_extraction_batch,
        language_model=configuration.language_model,
    )

    report_batches = []
    notification_title = f"Extracting **{context.component.value}** from collection"

    for source_batch in tqdm(
        source_batches,
        total=len(source_batches),
        desc=f"Generating report {context.component}",
    ):
        notifier.notify(
            notification_title=notification_title,
            status=MessageLogStatus.RUNNING,
            message_log_event=MessageLogEvent(
                type="InternalSearch",
                text=f"Processing {source_batch.source.title}",
            ),
        )

        step_precentage_increment = 1 / (
            len(source_batch.batches) * len(source_batches)
        )

        for batch in source_batch.batches:
            notifier.update_progress(
                step_precentage_increment=0,
                current_step_message=f"Extracting **{context.component.value}** from `{source_batch.source.title}`",
            )
            system_prompt = Template(context.extraction_system_prompt).render(
                company_name=context.company_name
            )
            report_batch = await extract_swot_from_source_batch(
                system_prompt=system_prompt,
                batch_parser=batch_parser,
                language_model_service=language_model_service,
                language_model=configuration.language_model,
                output_model=context.extraction_output_model,
                batch=batch,
            )
            if report_batch is None:
                continue

            report_batches.append(report_batch)
            notifier.update_progress(
                step_precentage_increment=step_precentage_increment,
                current_step_message=f"Extracted **{context.component.value}** from `{source_batch.source.title}`",
            )

        notifier.notify(
            notification_title=notification_title,
            status=MessageLogStatus.COMPLETED,
        )

    return context.extraction_output_model.group_batches(report_batches)


async def summarize_swot_extraction(
    *,
    context: ReportSummarizationContext,
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: ProgressNotifier,
) -> str:
    """
    Summarize a SWOT extraction report.
    """
    notification_title = f"Generating **{context.component.value}** report"
    notifier.notify(
        notification_title=notification_title,
        status=MessageLogStatus.RUNNING,
        message_log_event=MessageLogEvent(
            type="InternalSearch",
            text=f"Synthesizing **{context.extraction_results.number_of_items}** extracted items",
        ),
    )
    notifier.update_progress(
        step_precentage_increment=0,
        current_step_message=f"Synthesizing **{context.component.value}** report from **{context.extraction_results.number_of_items}** extracted items",
    )
    system_prompt = Template(context.summarization_system_prompt).render(
        company_name=context.company_name
    )
    summary = await summarize_swot_extraction_results(
        system_prompt=system_prompt,
        language_model_service=language_model_service,
        language_model=configuration.language_model,
        extraction_output_model=context.extraction_results,
    )
    notifier.update_progress(
        step_precentage_increment=0,
        current_step_message=f"Synthesized **{context.component.value}** report from **{context.extraction_results.number_of_items}** extracted items",
    )
    notifier.notify(
        notification_title=notification_title, status=MessageLogStatus.COMPLETED
    )
    return summary


async def modify_report(
    *,
    context: ReportModificationContext,
    configuration: ReportGenerationConfig,
    language_model_service: LanguageModelService,
    notifier: ProgressNotifier,
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
