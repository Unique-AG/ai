import logging
import re
from typing import NotRequired, TypedDict, override

import unique_sdk

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.tools.a2a.config import (
    ResponseDisplayMode,
    SubAgentToolDisplayConfig,
)
from unique_toolkit.agentic.tools.a2a.postprocessing.display import (
    build_sub_agent_answer_display,
    remove_sub_agent_answer_from_text,
)
from unique_toolkit.agentic.tools.a2a.service import SubAgentTool
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

logger = logging.getLogger(__name__)

SpaceMessage = unique_sdk.Space.Message


class _SubAgentMessageInfo(TypedDict):
    text: str | None
    references: list[unique_sdk.Space.Reference]


class _SubAgentToolInfo(TypedDict):
    display_name: str
    display_config: SubAgentToolDisplayConfig
    response: NotRequired[_SubAgentMessageInfo]


class SubAgentResponsesPostprocessor(Postprocessor):
    def __init__(
        self,
        user_id: str,
        company_id: str,
        agent_chat_id: str,
        sub_agent_tools: list[SubAgentTool],
    ):
        super().__init__(name=self.__class__.__name__)

        self._user_id = user_id
        self._company_id = company_id

        self._agent_chat_id = agent_chat_id

        self._assistant_id_to_tool_info: dict[str, _SubAgentToolInfo] = {}

        for sub_agent_tool in sub_agent_tools:
            sub_agent_tool.subscribe(self)

            self._assistant_id_to_tool_info[sub_agent_tool.config.assistant_id] = (
                _SubAgentToolInfo(
                    display_config=sub_agent_tool.config.response_display_config,
                    display_name=sub_agent_tool.display_name(),
                )
            )

        self._sub_agent_message = None

    @override
    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        self._sub_agent_message = await unique_sdk.Space.get_latest_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._agent_chat_id,
        )

    @override
    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        logger.info("Adding sub agent responses to the response")

        # Get responses to display
        displayed = {}
        for assistant_id, tool_info in self._assistant_id_to_tool_info.items():
            display_mode = tool_info["display_config"].mode

            if "response" not in tool_info:
                logger.warning(
                    "No response from assistant %s",
                    assistant_id,
                )
                continue

            if display_mode != ResponseDisplayMode.HIDDEN:
                displayed[assistant_id] = tool_info["response"]

        existing_refs = {
            ref.source_id: ref.sequence_number
            for ref in loop_response.message.references
        }
        _consolidate_references_in_place(displayed, existing_refs)

        for assistant_id, message in reversed(displayed.items()):
            tool_info = self._assistant_id_to_tool_info[assistant_id]
            display_mode = tool_info["display_config"].mode
            display_name = tool_info["display_name"]
            loop_response.message.text = (
                build_sub_agent_answer_display(
                    display_name=display_name,
                    assistant_id=assistant_id,
                    display_mode=display_mode,
                    answer=message["text"],
                )
                + loop_response.message.text
            )

            assert self._sub_agent_message is not None

            loop_response.message.references.extend(
                ContentReference(
                    message_id=self._sub_agent_message["id"],
                    source_id=ref["sourceId"],
                    url=ref["url"],
                    source=ref["source"],
                    name=ref["name"],
                    sequence_number=ref["sequenceNumber"],
                )
                for ref in message["references"]
            )

        return True

    @override
    async def remove_from_text(self, text) -> str:
        for assistant_id, tool_info in self._assistant_id_to_tool_info.items():
            display_config = tool_info["display_config"]
            if display_config.remove_from_history:
                text = remove_sub_agent_answer_from_text(
                    display_mode=display_config.mode,
                    text=text,
                    assistant_id=assistant_id,
                )
        return text

    def notify_sub_agent_response(
        self, sub_agent_assistant_id: str, response: SpaceMessage
    ) -> None:
        if sub_agent_assistant_id not in self._assistant_id_to_tool_info:
            logger.warning(
                "Unknown assistant id %s received, message will be ignored.",
                sub_agent_assistant_id,
            )
            return

        self._assistant_id_to_tool_info[sub_agent_assistant_id]["response"] = {
            "text": response["text"],
            "references": [
                {
                    "name": ref["name"],
                    "url": ref["url"],
                    "sequenceNumber": ref["sequenceNumber"],
                    "originalIndex": [],
                    "sourceId": ref["sourceId"],
                    "source": ref["source"],
                }
                for ref in response["references"] or []
            ],
        }


def _consolidate_references_in_place(
    messages: dict[str, _SubAgentMessageInfo], existing_refs: dict[str, int]
) -> None:
    start_index = max(existing_refs.values(), default=0) + 1

    for assistant_id, message in messages.items():
        references = message["references"]
        if len(references) == 0 or message["text"] is None:
            logger.info(
                "Message from assistant %s does not contain any references",
                assistant_id,
            )
            continue

        references = list(sorted(references, key=lambda ref: ref["sequenceNumber"]))

        message_new_refs = []
        for reference in references:
            source_id = reference["sourceId"]

            if source_id not in existing_refs:
                message_new_refs.append(reference)
                existing_refs[source_id] = start_index
                start_index += 1

            reference_num = existing_refs[source_id]

            seq_num = reference["sequenceNumber"]
            message["text"] = re.sub(
                rf"<sup>{seq_num}</sup>",
                f"<sup>{reference_num}</sup>",
                message["text"],
            )
            reference["sequenceNumber"] = reference_num

        message["references"] = message_new_refs
