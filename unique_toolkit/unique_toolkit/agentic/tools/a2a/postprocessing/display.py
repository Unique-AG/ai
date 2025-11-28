import asyncio
import logging
from collections import defaultdict
from typing import NamedTuple, override

import unique_sdk
from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.tools.a2a.postprocessing._display_utils import (
    SubAgentAnswerPart,
    get_sub_agent_answer_display,
    get_sub_agent_answer_from_parts,
    get_sub_agent_answer_parts,
    remove_sub_agent_answer_from_text,
)
from unique_toolkit.agentic.tools.a2a.postprocessing._ref_utils import (
    add_content_refs_and_replace_in_text,
    remove_unused_refs,
)
from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentDisplayConfig,
    SubAgentResponseDisplayMode,
)
from unique_toolkit.agentic.tools.a2a.response_watcher import (
    SubAgentResponse,
    SubAgentResponseWatcher,
)
from unique_toolkit.content import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

logger = logging.getLogger(__name__)

SpaceMessage = unique_sdk.Space.Message


class SubAgentDisplaySpec(NamedTuple):
    assistant_id: str
    display_name: str
    display_config: SubAgentDisplayConfig


_ANSWERS_JINJA_TEMPLATE = """
{% for answer in answers %}
{{ answer }}
{% endfor %}
""".strip()


class SubAgentResponsesPostprocessorConfig(BaseModel):
    model_config = get_configuration_dict()

    sleep_time_before_update: float = Field(
        default=0, description="Time to sleep before updating the main agent message."
    )
    answers_jinja_template: str = Field(
        default=_ANSWERS_JINJA_TEMPLATE,
        description="The template to use to display the sub agent answers.",
    )
    filter_duplicate_answers: bool = Field(
        default=True,
        description="If set, duplicate answers will be filtered out.",
    )


class SubAgentResponsesDisplayPostprocessor(Postprocessor):
    def __init__(
        self,
        config: SubAgentResponsesPostprocessorConfig,
        response_watcher: SubAgentResponseWatcher,
        display_specs: list[SubAgentDisplaySpec],
    ) -> None:
        super().__init__(name=self.__class__.__name__)

        self._config = config
        self._response_watcher = response_watcher
        self._display_specs: dict[str, SubAgentDisplaySpec] = {
            display_spec.assistant_id: display_spec
            for display_spec in display_specs
            if display_spec.display_config.mode != SubAgentResponseDisplayMode.HIDDEN
            # We should keep track of these messages even if they are hidden
            or display_spec.display_config.force_include_references
        }

    @override
    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        await asyncio.sleep(
            self._config.sleep_time_before_update
        )  # Frontend rendering issues

    def _get_displayed_sub_agent_responses(
        self,
    ) -> dict[str, list[SubAgentResponse]]:
        responses = defaultdict(list)
        all_responses = self._response_watcher.get_all_responses()
        for response in all_responses:
            assistant_id = response.assistant_id
            if assistant_id in self._display_specs:
                responses[assistant_id].append(response)
        return responses

    @override
    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        displayed_sub_agent_responses = self._get_displayed_sub_agent_responses()

        if len(displayed_sub_agent_responses) == 0:
            logger.info("No sub agent responses to prepend")
            return False

        logger.info("Prepending sub agent responses to the main agent response")

        answers_displayed_before = []
        answers_displayed_after = []
        all_displayed_answers = set()

        for assistant_id, responses in displayed_sub_agent_responses.items():
            tool_info = self._display_specs[assistant_id]
            tool_name = tool_info.display_name

            for response in responses:
                message = response.message

                if tool_info.display_config.mode == SubAgentResponseDisplayMode.HIDDEN:
                    # Add references and continue
                    _add_response_references_to_message_in_place(
                        loop_response=loop_response,
                        response=message,
                        remove_unused_references=False,
                    )
                    continue

                if message["text"] is None:
                    logger.warning(
                        "Sub agent response for assistant %s with sequence number %s does not contain any text",
                        assistant_id,
                        response.sequence_number,
                    )
                    continue

                answer_parts = get_sub_agent_answer_parts(
                    answer=message["text"],
                    display_config=tool_info.display_config,
                )

                if self._config.filter_duplicate_answers:
                    answer_parts, all_displayed_answers = (
                        _filter_and_update_duplicate_answers(
                            answers=answer_parts,
                            existing_answers=all_displayed_answers,
                        )
                    )

                answer = get_sub_agent_answer_from_parts(
                    answer_parts=answer_parts,
                    config=tool_info.display_config,
                )
                message["text"] = answer

                _add_response_references_to_message_in_place(
                    loop_response=loop_response,
                    response=message,
                    remove_unused_references=not tool_info.display_config.force_include_references,
                )

                if len(answer_parts) == 0:
                    continue

                display_name = tool_name
                if len(responses) > 1:
                    display_name = tool_name + f" {response.sequence_number}"

                answer = get_sub_agent_answer_display(
                    display_name=display_name,
                    display_config=tool_info.display_config,
                    answer=answer,
                    assistant_id=assistant_id,
                )

                if tool_info.display_config.position == "before":
                    answers_displayed_before.append(answer)
                else:
                    answers_displayed_after.append(answer)

        loop_response.message.text = _get_final_answer_display(
            text=loop_response.message.text,
            answers_before=answers_displayed_before,
            answers_after=answers_displayed_after,
            template=self._config.answers_jinja_template,
        )

        return True

    @override
    async def remove_from_text(self, text) -> str:
        for display_info in self._display_specs.values():
            text = remove_sub_agent_answer_from_text(
                display_config=display_info.display_config,
                text=text,
                assistant_id=display_info.assistant_id,
            )
        return text


def _add_response_references_to_message_in_place(
    loop_response: LanguageModelStreamResponse,
    response: unique_sdk.Space.Message,
    remove_unused_references: bool = True,
) -> None:
    references = response["references"]
    text = response["text"]

    if references is None or len(references) == 0 or text is None:
        return

    content_refs = [ContentReference.from_sdk_reference(ref) for ref in references]

    if remove_unused_references:
        content_refs = remove_unused_refs(
            references=content_refs,
            text=text,
        )

    text, refs = add_content_refs_and_replace_in_text(
        message_text=text,
        message_refs=loop_response.message.references,
        new_refs=content_refs,
    )

    response["text"] = text  # Diplayed at a later stage
    loop_response.message.references = refs


def _get_final_answer_display(
    text: str,
    answers_before: list[str],
    answers_after: list[str],
    template: str = _ANSWERS_JINJA_TEMPLATE,
) -> str:
    if len(answers_before) > 0:
        text = render_template(template, {"answers": answers_before}) + text

    if len(answers_after) > 0:
        text = text + render_template(template, {"answers": answers_after})

    return text.strip()


def _filter_and_update_duplicate_answers(
    answers: list[SubAgentAnswerPart],
    existing_answers: set[str],
) -> tuple[list[SubAgentAnswerPart], set[str]]:
    new_answers = []

    for answer in answers:
        if answer.matching_text in existing_answers:
            continue
        existing_answers.add(answer.matching_text)
        new_answers.append(answer)

    return new_answers, existing_answers
