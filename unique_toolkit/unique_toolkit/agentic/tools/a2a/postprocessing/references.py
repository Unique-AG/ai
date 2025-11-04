import logging
import re
from typing import override

from unique_toolkit._common.referencing import (
    get_reference_pattern,
    remove_consecutive_ref_space,
)
from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.tools.a2a.postprocessing._ref_utils import (
    add_content_refs_and_replace_in_text,
    to_content_ref,
)
from unique_toolkit.agentic.tools.a2a.response_watcher import (
    SubAgentResponse,
    SubAgentResponseWatcher,
)
from unique_toolkit.agentic.tools.a2a.tool import SubAgentTool
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

logger = logging.getLogger(__name__)


class SubAgentReferencesPostprocessor(Postprocessor):
    def __init__(self, response_watcher: SubAgentResponseWatcher) -> None:
        super().__init__(name=self.__class__.__name__)
        self._response_watcher = response_watcher

    @override
    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        return

    @override
    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        logger.info("Adding sub agent references to the main agent response")

        num_sources = len(loop_response.message.references)

        # At the moment, the `PostprocessorManager` expects modifications to happen in place
        _add_sub_agent_references_in_place(
            loop_response=loop_response,
            responses=self._response_watcher.get_all_responses(),
        )

        return num_sources != len(
            loop_response.message.references
        )  # We only add references

    @override
    async def remove_from_text(self, text: str) -> str:
        """
        It is not possible to **only** remove sub agent references from the text,
        as they are identical to normal references.
        """
        return text


def _add_sub_agent_references_in_place(
    loop_response: LanguageModelStreamResponse,
    responses: list[SubAgentResponse],
) -> None:
    text = loop_response.message.text
    refs = []

    for response in responses:
        sub_agent_refs = []
        references = response.message["references"]

        if references is None or len(references) == 0:
            continue

        for reference in sorted(references, key=lambda r: r["sequenceNumber"]):
            reference_re = SubAgentTool.get_sub_agent_reference_re(
                name=response.name,
                sequence_number=response.sequence_number,
                reference_number=reference["sequenceNumber"],
            )

            if re.search(reference_re, text) is None:
                # Reference not used
                continue

            sub_agent_refs.append(to_content_ref(reference))

        text, refs = add_content_refs_and_replace_in_text(
            message_text=text,
            message_refs=refs,
            new_refs=sub_agent_refs,
            ref_pattern_f=lambda x: r"\s*"  # Normalize spaces
            + SubAgentTool.get_sub_agent_reference_re(
                name=response.name,
                sequence_number=response.sequence_number,
                reference_number=x,
            ),
            ref_replacement_f=lambda x: " " + get_reference_pattern(x),
        )

    loop_response.message.references = refs
    loop_response.message.text = remove_consecutive_ref_space(text)
