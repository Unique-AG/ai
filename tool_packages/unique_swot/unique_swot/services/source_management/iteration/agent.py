from logging import getLogger
from typing import AsyncIterator, Generator

from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import Content

from unique_swot.services.orchestrator.service import StepNotifier
from unique_swot.services.source_management.iteration.config import (
    SourceIterationConfig,
)
from unique_swot.services.source_management.iteration.schema import (
    SourceIterationResults,
)
from unique_swot.utils import (
    generate_structured_output,
    generate_unique_id,
    get_content_chunk_title,
)

_LOGGER = getLogger(__name__)


class SourceIterationAgent:
    def __init__(
        self,
        *,
        llm_service: LanguageModelService,
        llm: LMI,
        source_iteration_config: SourceIterationConfig,
    ):
        self._llm_service = llm_service
        self._llm = llm
        self._source_iteration_config = source_iteration_config
        self._content_map = {}

    async def iterate(
        self, *, contents: list[Content], step_notifier: StepNotifier
    ) -> AsyncIterator[Content]:
        system_prompt = self._compose_system_prompt(
            objective=self._source_iteration_config.prompt_config.objective
        )
        user_prompt = self._compose_user_prompt(contents=contents)

        notification_title = "Sorting sources"

        await step_notifier.notify(
            title=notification_title,
        )

        response = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_prompt,
            llm=self._llm,
            llm_service=self._llm_service,
            output_model=SourceIterationResults,
        )

        fallback_notification_message = (
            "Unable to sort the sources. Original order will be preserved."
        )

        notification_description = (
            response.results_summary if response else fallback_notification_message
        )

        await step_notifier.notify(
            title=notification_title,
            description=notification_description,
            completed=True,
            progress=100,
        )

        # Return the ordered (and missed) contents as an AsyncIterator
        return self._handle_results(results=response)

    def _compose_system_prompt(self, *, objective: str) -> str:
        template = Template(self._source_iteration_config.prompt_config.system_prompt)
        return template.render(objective=objective)

    def _compose_user_prompt(self, *, contents: list[Content]) -> str:
        contents_list = list(self._return_contents(contents=contents))

        template = Template(self._source_iteration_config.prompt_config.user_prompt)
        return template.render(contents=contents_list)

    def _return_contents(
        self, *, contents: list[Content]
    ) -> Generator[dict[str, str], None, None]:
        for content in contents:
            unique_id = generate_unique_id(prefix="content")
            self._content_map[unique_id] = content
            selected_chunks = content.chunks[
                : self._source_iteration_config.max_number_of_selected_chunks
            ]
            selected_chunks_texts = [chunk.text for chunk in selected_chunks]
            yield {
                "id": unique_id,
                "document_title": get_content_chunk_title(content),
                "chunks": "\n".join(selected_chunks_texts),
            }

    def _handle_results(
        self, *, results: SourceIterationResults | None
    ) -> AsyncIterator[Content]:
        if results is None:
            # If no results, return all contents in original order
            async def _default_generator():
                for content in self._content_map.values():
                    yield content

            return _default_generator()

        async def _generator():
            # Create a mapping of ID to order for efficient lookup
            id_to_order = {
                result.id: result.order for result in results.ordered_sources
            }

            # Separate missed and ordered contents in one pass
            missed_contents = []
            ordered_items = []

            for content_id, content in self._content_map.items():
                if content_id in id_to_order:
                    ordered_items.append((id_to_order[content_id], content))
                else:
                    missed_contents.append(content)

            # Yield missed documents first
            for content in missed_contents:
                yield content

            # Sort and yield ordered documents
            ordered_items.sort(key=lambda x: x[0])  # Sort by order
            for _, content in ordered_items:
                yield content

        return _generator()
