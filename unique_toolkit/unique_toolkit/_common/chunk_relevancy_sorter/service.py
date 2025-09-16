import logging
import time
from collections import Counter
from typing import Any, overload

from typing_extensions import deprecated

from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.exception import (
    ChunkRelevancySorterException,
)
from unique_toolkit._common.chunk_relevancy_sorter.schemas import (
    ChunkRelevancy,
    ChunkRelevancySorterResult,
)
from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.agentic.evaluation.config import EvaluationMetricConfig
from unique_toolkit.agentic.evaluation.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
    StructuredOutputConfig,
)
from unique_toolkit.agentic.evaluation.context_relevancy.service import (
    ContextRelevancyEvaluator,
)
from unique_toolkit.agentic.evaluation.exception import EvaluatorException
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.app.performance.async_tasks import run_async_tasks_parallel
from unique_toolkit.app.schemas import BaseEvent, ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo


class ChunkRelevancySorter:
    @deprecated(
        "Use __init__ with company_id and user_id instead or use the classmethod `from_event`"
    )
    @overload
    def __init__(self, event: ChatEvent | BaseEvent):
        """
        Initialize the ChunkRelevancySorter with an event (deprecated)
        """

    @overload
    def __init__(self, *, company_id: str, user_id: str):
        """
        Initialize the ChunkRelevancySorter with a company_id and user_id
        """

    def __init__(
        self,
        event: ChatEvent | BaseEvent | None = None,
        company_id: str | None = None,
        user_id: str | None = None,
    ):
        if isinstance(event, (ChatEvent, BaseEvent)):
            self.chunk_relevancy_evaluator = ContextRelevancyEvaluator.from_event(event)
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            self.chunk_relevancy_evaluator = ContextRelevancyEvaluator(
                company_id=company_id, user_id=user_id
            )
        module_name = "ChunkRelevancySorter"
        self.logger = logging.getLogger(f"{module_name}.{__name__}")

    @classmethod
    def from_event(cls, event: ChatEvent | BaseEvent):
        return cls(company_id=event.company_id, user_id=event.user_id)

    async def run(
        self,
        input_text: str,
        chunks: list[ContentChunk],
        config: ChunkRelevancySortConfig,
    ) -> ChunkRelevancySorterResult:
        """
        Resorts the search chunks by classifying each chunk into High, Medium, Low depending on the relevancy to the user input, then
        sorts the chunks based on the classification while preserving the orginial order.

        Args:
            chunks (list[ContentChunk]): The list of search chunks to be reranked.

        Returns:
            ChunkRelevancySorterResult: The result of the chunk relevancy sort.

        Raises:
            ChunkRelevancySorterException: If an error occurs while sorting the chunks.
        """

        if not config.enabled:
            self.logger.info("Chunk relevancy sort is disabled.")
            return ChunkRelevancySorterResult.from_chunks(chunks)

        self.logger.info("Running chunk relevancy sort.")
        return await self._run_chunk_relevancy_sort(input_text, chunks, config)

    async def _run_chunk_relevancy_sort(
        self,
        input_text: str,
        chunks: list[ContentChunk],
        config: ChunkRelevancySortConfig,
    ) -> ChunkRelevancySorterResult:
        start_time = time.time()

        resorted_relevancies = []

        try:
            self.logger.info(f"Resorting {len(chunks)} chunks based on relevancy...")
            chunk_relevancies = await self._evaluate_chunks_relevancy(
                input_text,
                chunks,
                config,
            )
            resorted_relevancies = await self._validate_and_sort_relevant_chunks(
                config,
                chunk_relevancies,
            )
        except ChunkRelevancySorterException as e:
            self.logger.error(e.error_message)
            raise e
        except Exception as e:
            unknown_error_msg = "Unknown error occurred while resorting search results."
            raise ChunkRelevancySorterException(
                user_message=f"{unknown_error_msg}. Fallback to original search results.",
                error_message=f"{unknown_error_msg}: {e}",
            )
        finally:
            end_time = time.time()
            duration = end_time - start_time
            total_chunks = len(resorted_relevancies)
            success_msg = f"Resorted {total_chunks} chunks in {duration:.2f} seconds."
            self.logger.info(success_msg)
            return ChunkRelevancySorterResult(
                relevancies=resorted_relevancies,
                user_message=success_msg,
            )

    async def _evaluate_chunks_relevancy(
        self,
        input_text: str,
        chunks: list[ContentChunk],
        config: ChunkRelevancySortConfig,
    ) -> list[ChunkRelevancy]:
        """
        Evaluates the relevancy of the chunks.
        """
        self.logger.info(
            f"Processing chunk relevancy for {len(chunks)} chunks with {config.language_model.name}. "
            f"(Structured output: {config.structured_output_config.enabled}. Extract fact list: {config.structured_output_config.extract_fact_list})",
        )

        # Evaluate the relevancy of each chunk
        tasks = [
            self._process_relevancy_evaluation(input_text, chunk=chunk, config=config)
            for chunk in chunks
        ]
        chunk_relevancies = await run_async_tasks_parallel(
            tasks=tasks,
            max_tasks=config.max_tasks,
            logger=self.logger,
        )

        # handle exceptions
        for chunk_relevancy in chunk_relevancies:
            if isinstance(chunk_relevancy, Exception):
                error_msg = "Error occurred while evaluating context relevancy of a specific chunk"
                raise ChunkRelevancySorterException(
                    user_message=f"{error_msg}. Fallback to original search results.",
                    error_message=f"{error_msg}: {chunk_relevancy}",
                    exception=chunk_relevancy,
                )

        # This check is currently necessary for typing purposes only
        # as the run_async_tasks_parallel function does not enforce the return type
        # TODO fix return type in run_async_tasks_parallel
        chunk_relevancies = [
            chunk_relevancy
            for chunk_relevancy in chunk_relevancies
            if isinstance(chunk_relevancy, ChunkRelevancy)
        ]

        return chunk_relevancies

    async def _evaluate_chunk_relevancy(
        self,
        input_text: str,
        langugage_model: LanguageModelInfo,
        chunk: ContentChunk,
        structured_output_config: StructuredOutputConfig,
        additional_llm_options: dict[str, Any],
    ) -> EvaluationMetricResult | None:
        """
        Gets the relevancy score of the chunk compared to the user message txt.
        """
        structured_output_schema = (
            (
                EvaluationSchemaStructuredOutput.get_with_descriptions(
                    structured_output_config
                )
            )
            if structured_output_config.enabled
            else None
        )

        metric_config = EvaluationMetricConfig(
            enabled=True,
            name=EvaluationMetricName.CONTEXT_RELEVANCY,
            language_model=langugage_model,
            additional_llm_options=additional_llm_options,
        )
        relevancy_input = EvaluationMetricInput(
            input_text=input_text,
            context_texts=[chunk.text],
        )

        return await self.chunk_relevancy_evaluator.analyze(
            input=relevancy_input,
            config=metric_config,
            structured_output_schema=structured_output_schema,
        )

    async def _process_relevancy_evaluation(
        self,
        input_text: str,
        chunk: ContentChunk,
        config: ChunkRelevancySortConfig,
    ):
        model = config.language_model
        fallback_model = config.fallback_language_model
        try:
            relevancy = await self._evaluate_chunk_relevancy(
                input_text=input_text,
                langugage_model=model,
                chunk=chunk,
                structured_output_config=config.structured_output_config,
                additional_llm_options=config.additional_llm_options,
            )
            return ChunkRelevancy(
                chunk=chunk,
                relevancy=relevancy,
            )
        except EvaluatorException as e:
            if e.exception:
                self.logger.warning(
                    "Error evaluating chunk ID %s with model %s. Trying fallback model %s.",
                    chunk.chunk_id,
                    model,
                    e.exception,
                )
                relevancy = await self._evaluate_chunk_relevancy(
                    input_text=input_text,
                    langugage_model=fallback_model,
                    chunk=chunk,
                    structured_output_config=config.structured_output_config,
                    additional_llm_options=config.additional_llm_options,
                )
            else:
                raise e
        except Exception as e:
            raise ChunkRelevancySorterException(
                user_message="Error occurred while evaluating context relevancy of a specific chunk.",
                error_message=f"Error in _process_relevancy_evaluation: {e}",
                exception=e,
            )

    async def _validate_and_sort_relevant_chunks(
        self,
        config: ChunkRelevancySortConfig,
        chunk_relevancies: list[ChunkRelevancy],
    ) -> list[ChunkRelevancy]:
        """
        Checks for error or no value in chunk relevancy.
        """

        # Check that all chunk relevancies have a relevancy level
        await self._validate_chunk_relevancies(chunk_relevancies)

        # Filter the chunks based on the relevancy levels to consider
        chunk_relevancies = await self._filter_chunks_by_relevancy_levels(
            config,
            chunk_relevancies,
        )

        # Sort the chunks based on the relevancy levels
        sorted_chunks = await self._sort_chunk_relevancies_by_relevancy_and_chunk(
            config,
            chunk_relevancies,
        )

        return sorted_chunks

    async def _validate_chunk_relevancies(
        self,
        chunk_relevancies: list[ChunkRelevancy],
    ):
        for chunk_relevancy in chunk_relevancies:
            if not chunk_relevancy.relevancy or not chunk_relevancy.relevancy.value:
                raise ChunkRelevancySorterException(
                    user_message="Error occurred while evaluating chunk relevancy.",
                    error_message=f"No relevancy level returned for chunk ID {chunk_relevancy.chunk.chunk_id}.",
                )

    async def _sort_chunk_relevancies_by_relevancy_and_chunk(
        self,
        config: ChunkRelevancySortConfig,
        chunk_relevancies: list[ChunkRelevancy],
    ):
        # Define the custom sorting order for relevancy
        relevancy_level_order = config.relevancy_level_order

        # Create a dictionary to map the chunk chunkId to its position in the original order
        chunk_order = {
            relevancy.chunk.chunk_id: index
            for index, relevancy in enumerate(chunk_relevancies)
        }

        # Sort the chunk relevancies first by relevancy and then by original order within each relevancy level
        sorted_chunk_relevancies = sorted(
            chunk_relevancies,
            key=lambda obj: (
                relevancy_level_order[obj.relevancy.value.lower()],  # type: ignore
                chunk_order[obj.chunk.chunk_id],
            ),
        )

        # Count and print the distinct values of relevancy
        self._count_distinct_values(sorted_chunk_relevancies)

        # Return only the chunk in the sorted order
        return sorted_chunk_relevancies

    async def _filter_chunks_by_relevancy_levels(
        self,
        config: ChunkRelevancySortConfig,
        chunk_relevancies: list[ChunkRelevancy],
    ) -> list[ChunkRelevancy]:
        levels_to_consider = [
            relevancy_level.lower()
            for relevancy_level in config.relevancy_levels_to_consider
        ]
        if not levels_to_consider:
            self.logger.warning("No relevancy levels defined, including all levels.")
            return chunk_relevancies

        self.logger.info(
            "Filtering chunks by relevancy levels: %s.", levels_to_consider
        )
        return [
            chunk_relevancy
            for chunk_relevancy in chunk_relevancies
            if chunk_relevancy.relevancy.value.lower() in levels_to_consider  # type: ignore
        ]

    def _count_distinct_values(self, chunk_relevancies: list[ChunkRelevancy]):
        # Extract the values from the relevancy field
        values = [
            cr.relevancy.value
            for cr in chunk_relevancies
            if cr.relevancy and cr.relevancy.value
        ]

        # Use Counter to count occurrences
        value_counts = Counter(values)

        self.logger.info("Count of distinct relevancy values:")
        for value, count in value_counts.items():
            self.logger.info(f"Relevancy: {value}, Count: {count}")

        return value_counts
