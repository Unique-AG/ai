"""Generation handler service for LLM-based summarization."""

import logging
from pathlib import Path
from typing import Any, Callable

from jinja2 import Template
from tiktoken import get_encoding

from unique_toolkit._common.experimental.write_up_agent.schemas import (
    GroupData,
    ProcessedGroup,
)
from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.config import (
    GenerationHandlerConfig,
)
from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.exceptions import (
    BatchCreationError,
    LLMCallError,
    PromptBuildError,
    TokenLimitError,
)
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

logger = logging.getLogger(__name__)


class GenerationHandler:
    """
    Handles LLM-based generation with adaptive batching and iterative aggregation.

    This service:
    - Splits groups into batches based on token/row limits
    - Builds prompts from Jinja templates
    - Calls LLM for each batch
    - Aggregates results iteratively with context
    """

    def __init__(
        self,
        config: GenerationHandlerConfig,
        llm_service: LanguageModelService,
        renderer: Callable,
    ):
        """
        Initialize generation handler.

        Args:
            config: Configuration for generation
            renderer: Function to render group content (injected from template handler)
                     Signature: renderer(group_data, llm_response=None) -> str
        """
        self.config = config
        self.renderer = renderer

        # Load prompt templates
        prompts_dir = Path(__file__).parent / "prompts"
        system_template_path = prompts_dir / "system_prompt.j2"
        user_template_path = prompts_dir / "user_prompt.j2"

        self.system_template = Template(system_template_path.read_text())
        self.user_template = Template(user_template_path.read_text())

        self.llm_service = llm_service
        self.encoder = get_encoding(self.config.language_model.encoder_name)

        def token_counter(text: str) -> int:
            return len(self.encoder.encode(text))

        # Token counter (use provided or default to character approximation)
        self.token_counter = token_counter

    def process_groups(self, groups: list[GroupData]) -> list[ProcessedGroup]:
        """
        Process all groups with LLM generation.

        Args:
            groups: List of GroupData instances

        Returns:
            List of ProcessedGroup instances with llm_response added

        Raises:
            GenerationHandlerError: If generation fails
        """
        processed_groups = []

        for group in groups:
            group_key_string = group.group_key

            logger.info(f"Processing group: {group_key_string}")

            # Get group-specific instruction
            group_instruction = self.config.group_specific_instructions.get(
                group_key_string
            )

            try:
                # Process group with batching
                llm_response = self._process_group_with_batching(
                    group, group_instruction
                )

                # Create ProcessedGroup with proper typing
                processed_group = ProcessedGroup(
                    group_key=group.group_key,
                    rows=group.rows,
                    llm_response=llm_response,
                )
                processed_groups.append(processed_group)

                logger.info(
                    f"Successfully processed group: {group_key_string} "
                    f"(response length: {self.token_counter(llm_response)} tokens)"
                )

            except Exception as e:
                logger.error(f"Error processing group {group_key_string}: {e}")
                # Re-raise to allow caller to handle
                raise

        return processed_groups

    def _process_group_with_batching(
        self, group: GroupData, group_instruction: str | None
    ) -> str:
        """
        Process a single group with adaptive batching.

        Args:
            group: GroupData instance
            group_instruction: Optional group-specific instruction

        Returns:
            Final LLM response (aggregated if multiple batches)

        Raises:
            BatchCreationError: If batching fails
            LLMCallError: If LLM call fails
            AggregationError: If aggregation fails
        """
        group_key = group.group_key
        rows = group.rows

        # Create batches adaptively
        try:
            batches = self._create_batches(rows, group_key)
            logger.info(
                f"Created {len(batches)} batches for group {group_key} "
                f"({len(rows)} total rows)"
            )
        except Exception as e:
            raise BatchCreationError(
                f"Failed to create batches for group {group_key}: {e}",
                group_key=str(group_key),
                row_count=len(rows),
            ) from e

        # Process each batch iteratively, keeping only one previous summary at a time
        previous_summary: str | None = None

        for batch_index, batch_group in enumerate(batches, start=1):
            try:
                # Render content for this batch
                content = self.renderer(batch_group)

                # Build prompts with section name and at most one previous summary
                system_prompt, user_prompt = self._build_prompts(
                    section_name=group_key,
                    content=content,
                    group_instruction=group_instruction,
                    previous_summary=previous_summary,
                )

                # Call LLM
                batch_summary = self._call_llm(system_prompt, user_prompt)

                # Keep only this summary for the next iteration
                previous_summary = batch_summary

                logger.debug(
                    f"Batch {batch_index}/{len(batches)} processed "
                    f"(summary length: {self.token_counter(batch_summary)} tokens)"
                )

            except LLMCallError:
                raise
            except Exception as e:
                raise LLMCallError(
                    f"Error processing batch {batch_index} for group {group_key}: {e}",
                    group_key=str(group_key),
                    batch_index=batch_index,
                    error_details=str(e),
                ) from e

        # Return final summary (last batch's result)
        return previous_summary if previous_summary else ""

    def _create_batches(
        self, rows: list[dict[str, Any]], group_key: str
    ) -> list[GroupData]:
        """
        Create batches adaptively based on token and row limits.

        Fits as many rows as possible per batch while staying under limits.

        Args:
            rows: List of row dicts
            group_key: Group identifier for creating GroupData instances

        Returns:
            List of GroupData instances (each representing a batch)

        Raises:
            TokenLimitError: If token counting fails
        """
        if not rows:
            return [GroupData(group_key=group_key, rows=[])]

        batches = []
        current_batch = []
        current_batch_tokens = 0

        for row in rows:
            # Estimate tokens for this row (rough approximation)
            try:
                row_str = str(row)
                row_tokens = self.token_counter(row_str)
            except Exception as e:
                raise TokenLimitError(
                    f"Failed to count tokens for row: {e}",
                    estimated_tokens=0,
                    max_tokens=self.config.max_tokens_per_batch,
                ) from e

            # Check if adding this row would exceed limits
            would_exceed_tokens = (
                current_batch_tokens + row_tokens > self.config.max_tokens_per_batch
            )
            would_exceed_rows = len(current_batch) >= self.config.max_rows_per_batch

            if current_batch and (would_exceed_tokens or would_exceed_rows):
                # Start new batch - create GroupData instance
                batches.append(GroupData(group_key=group_key, rows=current_batch))
                current_batch = [row]
                current_batch_tokens = row_tokens
            else:
                # Add to current batch
                current_batch.append(row)
                current_batch_tokens += row_tokens

        # Add final batch
        if current_batch:
            batches.append(GroupData(group_key=group_key, rows=current_batch))

        return batches

    def _build_prompts(
        self,
        section_name: str,
        content: str,
        group_instruction: str | None,
        previous_summary: str | None,
    ) -> tuple[str, str]:
        """
        Build system and user prompts from templates.

        Args:
            section_name: Name of the section being processed (group_key)
            content: Rendered content to summarize
            group_instruction: Optional group-specific instruction
            previous_summary: Optional previous batch summary for context

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            PromptBuildError: If prompt building fails
        """
        try:
            # Build system prompt
            system_prompt = self.system_template.render(
                common_instruction=self.config.common_instruction,
            )

            # Build user prompt with section name
            user_prompt = self.user_template.render(
                section_name=section_name,
                content=content,
                group_instruction=group_instruction,
                previous_summary=previous_summary,
            )

            return system_prompt.strip(), user_prompt.strip()

        except Exception as e:
            raise PromptBuildError(
                f"Failed to build prompts: {e}",
                context={
                    "section_name": section_name,
                    "has_group_instruction": group_instruction is not None,
                    "has_previous_summary": previous_summary is not None,
                },
            ) from e

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call LLM with prompts.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            LLM response text

        Raises:
            LLMCallError: If LLM call fails
        """
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )
        try:
            # Call the language model using the configured LMI
            response = self.llm_service.complete(
                messages=messages,
                model_name=self.config.language_model.name,
            )

            return response.choices[0].message.content  # type: ignore

        except Exception as e:
            raise LLMCallError(
                f"LLM call failed: {e}",
                error_details=str(e),
            ) from e
