import asyncio
import logging
from collections import defaultdict
from typing import NamedTuple, override

import unique_sdk
from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.tools.a2a.postprocessing._display_utils import (
    get_sub_agent_answer_display,
    remove_sub_agent_answer_from_text,
)
from unique_toolkit.agentic.tools.a2a.postprocessing._ref_utils import (
    add_content_refs_and_replace_in_text,
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


class SubAgentResponsesPostprocessorConfig(BaseModel):
    model_config = get_configuration_dict()

    sleep_time_before_update: float = Field(
        default=1, description="Time to sleep before updating the main agent message."
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

        for assistant_id, responses in displayed_sub_agent_responses.items():
            for response in responses:
                message = response.message
                tool_info = self._display_specs[assistant_id]

                _add_response_references_to_message_in_place(
                    loop_response=loop_response, response=message
                )

                display_name = tool_info.display_name
                if len(responses) > 1:
                    display_name += f" {response.sequence_number}"

                if message["text"] is None:
                    logger.warning(
                        "Sub agent response for assistant %s with sequence number %s does not contain any text",
                        assistant_id,
                        response.sequence_number,
                    )

                if tool_info.display_config.mode == SubAgentResponseDisplayMode.HIDDEN:
                    continue

                answer = get_sub_agent_answer_display(
                    display_name=display_name,
                    display_config=tool_info.display_config,
                    answer=message["text"] or "",
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
    loop_response: LanguageModelStreamResponse, response: unique_sdk.Space.Message
) -> None:
    references = response["references"]
    text = response["text"]

    if references is None or len(references) == 0 or text is None:
        return

    content_refs = [ContentReference.from_sdk_reference(ref) for ref in references]

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
    sep: str = "<br>\n\n",
) -> str:
    if len(answers_before) > 0:
        text = sep.join(answers_before) + sep + text

    if len(answers_after) > 0:
        text = text + sep + sep.join(answers_after)
    return text
