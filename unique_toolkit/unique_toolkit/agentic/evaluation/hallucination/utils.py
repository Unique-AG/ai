import re
from enum import StrEnum
from logging import getLogger

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.evaluation.config import EvaluationMetricConfig
from unique_toolkit.agentic.evaluation.exception import EvaluatorException
from unique_toolkit.agentic.evaluation.output_parser import parse_eval_metric_result
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.content import ContentReference
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.service import LanguageModelService

from .constants import (
    hallucination_required_input_fields,
)

_LOGGER = getLogger(__name__)


async def check_hallucination(
    company_id: str,
    user_id: str,
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
) -> EvaluationMetricResult:
    """
    Analyzes the level of hallucination in the generated output by comparing it with the provided input
    and the contexts or history. The analysis classifies the hallucination level as:
    - low
    - medium
    - high

    If no contexts or history are referenced in the generated output, the method checks that the output
    does not contain any relevant information to answer the question.

    This method performs the following steps:
    1. Checks if the hallucination metric is enabled using the provided `config`.
    2. Logs the start of the analysis using the provided `logger`.
    3. Validates the required fields in the `input` data.
    4. Retrieves the messages using the `_get_msgs` method.
    5. Calls `LanguageModelService.complete_async_util` to get a completion result.
    6. Parses and returns the evaluation metric result based on the content of the completion result.

    Args:
        company_id (str): The company ID for the analysis.
        input (EvaluationMetricInput): The input data used for evaluation, including the generated output and reference information.
        config (EvaluationMetricConfig, optional): Configuration settings for the evaluation. Defaults to `hallucination_metric_default_config`.
        logger (Optional[logging.Logger], optional): The logger used for logging information and errors. Defaults to the logger for the current module.

    Returns:
        EvaluationMetricResult | None: The result of the evaluation, indicating the level of hallucination. Returns `None` if the metric is not enabled or if an error occurs.

    Raises:
        EvaluatorException: If the context texts are empty, required fields are missing, or an error occurs during the evaluation.
    """

    model_name = config.language_model.name
    _LOGGER.info(f"Analyzing level of hallucination with {model_name}.")

    input.validate_required_fields(hallucination_required_input_fields)

    try:
        msgs = _get_msgs(input, config)

        result = await LanguageModelService.complete_async_util(
            company_id=company_id, user_id=user_id, messages=msgs, model_name=model_name
        )
        result_content = result.choices[0].message.content
        if not result_content:
            error_message = "Hallucination evaluation did not return a result."
            raise EvaluatorException(
                error_message=error_message,
                user_message=error_message,
            )
        result = parse_eval_metric_result(
            result_content,  # type: ignore
            EvaluationMetricName.HALLUCINATION,
        )

        return result
    except Exception as e:
        error_message = "Error occurred during hallucination metric analysis"
        raise EvaluatorException(
            error_message=f"{error_message}: {e}",
            user_message=error_message,
            exception=e,
        )


def _get_msgs(
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
):
    """
    Composes the messages for hallucination analysis based on the provided input and configuration.

    This method composes messages with or without context based on the availability of context texts
    and history message texts in the input.

    Args:
        input (EvaluationMetricInput): The input data that includes context texts and history message texts
                                      for the analysis.
        config (EvaluationMetricConfig): The configuration settings for composing messages.
        logger (Optional[logging.Logger], optional): The logger used for logging debug information.

    Returns:
        The composed messages as per the provided input and configuration.
    """
    has_context = bool(input.context_texts or input.history_messages)

    if has_context:
        _LOGGER.debug("Using context / history for hallucination evaluation.")
    else:
        _LOGGER.debug("No contexts and history provided for hallucination evaluation.")

    return _compose_msgs(input, config, has_context)


def _compose_msgs(
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
    has_context: bool,
):
    """
    Composes the hallucination analysis messages using Jinja2 templates.

    Args:
        input (EvaluationMetricInput): The input data for evaluation.
        config (EvaluationMetricConfig): The configuration settings.
        has_context (bool): Whether context/history is available.

    Returns:
        LanguageModelMessages: The composed messages for evaluation.
    """
    # Get templates
    system_template = config.prompts_config.system_prompt_template
    user_template = config.prompts_config.user_prompt_template

    # Render system message
    system_msg_content = render_template(
        system_template,
        has_context=has_context,
    )
    system_msg = LanguageModelSystemMessage(content=system_msg_content)

    # Render user message
    user_msg_content = render_template(
        user_template,
        input_text=input.input_text,
        contexts_text=input.get_joined_context_texts(tag_name="reference")
        if has_context
        else None,
        history_messages_text=input.get_joined_history_texts(tag_name="conversation")
        if has_context
        else None,
        output_text=input.output_text,
    )
    user_msg = LanguageModelUserMessage(content=user_msg_content)

    return LanguageModelMessages([system_msg, user_msg])


class SourceSelectionMode(StrEnum):
    FROM_IDS = "FROM_IDS"
    FROM_ORDER = "FROM_ORDER"
    FROM_ORIGINAL_RESPONSE = "FROM_ORIGINAL_RESPONSE"


def context_text_from_stream_response(
    response: LanguageModelStreamResponse,
    selected_chunks: list[ContentChunk],
    source_selection_mode: SourceSelectionMode = SourceSelectionMode.FROM_IDS,
    ref_pattern: str = r"[\[<]?source(\d+)[>\]]?",
) -> list[str]:
    """Extract context text from stream response based on selected chunks.

    Args:
        response: The language model stream response containing references.
        selected_chunks: List of content chunks to select from.
        source_selection_mode: Strategy for selecting referenced chunks.
            - FROM_IDS: Match by chunk IDs (default)
            - FROM_ORDER: Select by order of appearance
            - FROM_ORIGINAL_RESPONSE: Extract from original response text using regex
        ref_pattern: Regex pattern for extracting source numbers (only used with FROM_ORIGINAL_RESPONSE).

    Returns:
        List of text strings from the referenced chunks.

    Raises:
        ValueError: If source_selection_mode is invalid or required data is missing.
    """
    response_references = response.message.references

    # Define selection strategies
    strategies = {
        SourceSelectionMode.FROM_IDS: lambda: _default_source_selection_mode(
            response_references, selected_chunks
        ),
        SourceSelectionMode.FROM_ORDER: lambda: _from_order_source_selection_mode(
            response_references, selected_chunks
        ),
        SourceSelectionMode.FROM_ORIGINAL_RESPONSE: lambda: _from_original_response_source_selection_mode(
            response.message.original_text, selected_chunks, ref_pattern
        ),
    }

    try:
        if source_selection_mode not in strategies:
            raise ValueError(f"Invalid source selection mode: {source_selection_mode}")

        _LOGGER.info(f"Selecting context text using {source_selection_mode} mode.")
        referenced_chunks = strategies[source_selection_mode]()
    except Exception as e:
        _LOGGER.error(f"Error selecting context text: {e}")
        _LOGGER.info("Falling back to default source selection mode.")
        referenced_chunks = _default_source_selection_mode(
            response_references, selected_chunks
        )

    return [chunk.text for chunk in referenced_chunks]


def _default_source_selection_mode(
    references: list[ContentReference], selected_chunks: list[ContentChunk]
) -> list[ContentChunk]:
    """Select chunks by matching reference IDs.

    Args:
        references: List of content references with source IDs.
        selected_chunks: List of content chunks to select from.

    Returns:
        List of referenced content chunks.
    """
    reference_ids = {reference.source_id for reference in references}

    def build_chunk_id(chunk: ContentChunk) -> str:
        return f"{chunk.id}_{chunk.chunk_id}"

    referenced_chunks = [
        chunk for chunk in selected_chunks if build_chunk_id(chunk) in reference_ids
    ]

    return referenced_chunks


def _from_order_source_selection_mode(
    references: list[ContentReference], selected_chunks: list[ContentChunk]
) -> list[ContentChunk]:
    """Select chunks by order of appearance in references.

    Args:
        references: List of content references with original indices.
        selected_chunks: List of content chunks to select from.

    Returns:
        List of referenced content chunks in order of appearance.
    """
    original_chunks_order: list[int] = []
    for reference in references:
        for original_index in reference.original_index:
            if original_index not in original_chunks_order:
                original_chunks_order.append(original_index)

    referenced_chunks: list[ContentChunk] = []
    for index in original_chunks_order:
        referenced_chunks.append(selected_chunks[index])

    return referenced_chunks


def _from_original_response_source_selection_mode(
    original_text: str | None,
    selected_chunks: list[ContentChunk],
    ref_pattern: str,
) -> list[ContentChunk]:
    """Extract referenced chunks from original text using regex pattern.

    Args:
        original_text: The original response text containing source references.
        selected_chunks: List of content chunks to select from.
        ref_pattern: Regex pattern for extracting source numbers.

    Returns:
        List of referenced content chunks.
    """
    if original_text is None:
        raise ValueError("original_text is required for FROM_ORIGINAL_RESPONSE mode")
    _LOGGER.debug("Processing original text for source extraction")
    source_number_matches = re.findall(ref_pattern, original_text)
    source_numbers = {int(num) for num in source_number_matches}

    # Add bounds checking
    max_index = len(selected_chunks) - 1
    valid_source_numbers = [idx for idx in source_numbers if 0 <= idx <= max_index]

    if len(valid_source_numbers) < len(source_numbers):
        invalid_numbers = set(source_numbers) - set(valid_source_numbers)
        _LOGGER.warning(
            f"Some source indices were out of bounds (max index: {max_index}). "
            f"Valid indices: {sorted(valid_source_numbers)}, Invalid indices: {sorted(invalid_numbers)}"
        )

    referenced_chunks = [selected_chunks[idx] for idx in valid_source_numbers]
    return referenced_chunks
