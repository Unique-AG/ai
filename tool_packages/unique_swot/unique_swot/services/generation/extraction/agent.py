from logging import getLogger

from jinja2 import Template
from pydantic import BaseModel, Field
from tiktoken import get_encoding
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.config import ExtractionConfig
from unique_swot.services.generation.extraction.models import (
    SWOTExtractionModel,
    get_swot_extraction_model,
)
from unique_swot.services.generation.extraction.prompts import (
    get_swot_extraction_system_prompt,
)
from unique_swot.services.generation.extraction.utils import batch_parser
from unique_swot.services.generation.structured_output import generate_structured_output
from unique_swot.services.source_management.schema import Source, SourceChunk

_LOGGER = getLogger(__name__)


class ExtractorAgent:
    def __init__(
        self,
        *,
        llm_service: LanguageModelService,
        llm: LMI,
        extraction_config: ExtractionConfig,
    ):
        self._llm_service = llm_service
        self._llm = llm
        self._extraction_config = extraction_config
        self._batch_parser = batch_parser

    async def extract(
        self,
        *,
        company_name: str,
        component: SWOTComponent,
        source: Source,
        optional_instruction: str | None,
    ) -> SWOTExtractionModel:
        ## Get the system prompt
        system_prompt = self._get_system_prompt(
            company_name=company_name,
            component=component,
            optional_instruction=optional_instruction,
        )

        ## Get the output model
        output_model = get_swot_extraction_model(component)

        ## Split the context into batches
        source_batches = _split_context_into_batches(
            source=source,
            batch_size=self._extraction_config.batch_size,
            max_tokens_per_batch=self._extraction_config.max_tokens_per_batch,
            llm=self._llm,
        )

        ## Prepare the extraction results
        extraction_results: list[SWOTExtractionModel] = []

        for batch in source_batches.batches:
            ## Extract the SWOT analysis from the batch
            extraction_result = await generate_structured_output(
                system_prompt=system_prompt,
                user_message=batch_parser(batch),
                llm_service=self._llm_service,
                llm=self._llm,
                output_model=output_model,
            )
            if extraction_result is not None:
                extraction_results.append(extraction_result)

        ## Group the extraction results
        return output_model.group_batches(batches=extraction_results)  # type: ignore

    def _get_system_prompt(
        self,
        *,
        company_name: str,
        component: SWOTComponent,
        optional_instruction: str | None,
    ) -> str:
        system_prompt_template = get_swot_extraction_system_prompt(
            component, self._extraction_config.prompt_config
        )
        system_prompt = Template(system_prompt_template).render(
            company_name=company_name,
            optional_instruction=optional_instruction,
        )

        return system_prompt


class SourceBatches(BaseModel):
    source: Source
    batches: list[list[SourceChunk]] = Field(default_factory=list)


def _split_context_into_batches(
    *,
    source: Source,
    batch_size: int,
    max_tokens_per_batch: int,
    llm: LMI,
) -> SourceBatches:
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

    encoding = get_encoding(llm.encoder_name)

    source_batches = SourceBatches(source=source)
    current_batch: list[SourceChunk] = []
    current_batch_size = 0
    for chunk in source.chunks:
        chunk_size = len(encoding.encode(chunk.text))

        # If adding this chunk would exceed the limit, finalize current group and start a new one
        if (
            current_batch_size + chunk_size > max_tokens_per_batch
            or len(current_batch) >= batch_size
        ):
            source_batches.batches.append(current_batch)
            current_batch = [chunk]
            current_batch_size = chunk_size
        else:
            current_batch.append(chunk)
            current_batch_size += chunk_size

    # Add any remaining chunks in the current group
    if current_batch:
        source_batches.batches.append(current_batch)

    _LOGGER.info(
        f"Split sources into {len(source_batches.batches)} batches out of {len(source.chunks)} chunks"
    )
    return source_batches
