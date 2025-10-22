import logging
import re
from typing import TypedDict, override

import unique_sdk

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.agentic.tools.a2a.postprocessing._display import (
    _build_sub_agent_answer_display,
    _remove_sub_agent_answer_from_text,
)
from unique_toolkit.agentic.tools.a2a.postprocessing._utils import (
    _replace_references_in_text,
)
from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentDisplayConfig,
    SubAgentResponseDisplayMode,
)
from unique_toolkit.agentic.tools.a2a.tool import SubAgentTool
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

logger = logging.getLogger(__name__)

SpaceMessage = unique_sdk.Space.Message


class _SubAgentMessageInfo(TypedDict):
    text: str
    references: list[unique_sdk.Space.Reference]


class _SubAgentToolInfo(TypedDict):
    name: str
    display_name: str
    display_config: SubAgentDisplayConfig
    responses: dict[int, _SubAgentMessageInfo]


class SubAgentResponsesPostprocessor(Postprocessor):
    def __init__(
        self,
        user_id: str,
        company_id: str,
        main_agent_chat_id: str,
    ) -> None:
        super().__init__(name=self.__class__.__name__)

        self._user_id = user_id
        self._company_id = company_id
        self._main_agent_chat_id = main_agent_chat_id

        self._assistant_id_to_tool_info: dict[str, _SubAgentToolInfo] = {}
        self._main_agent_message: SpaceMessage | None = None

    @override
    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        self._main_agent_message = await unique_sdk.Space.get_latest_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._main_agent_chat_id,
        )

    @override
    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        logger.info("Prepending sub agent responses to the main agent response")

        if len(self._assistant_id_to_tool_info) == 0 or all(
            len(tool_info["responses"]) == 0
            for tool_info in self._assistant_id_to_tool_info.values()
        ):
            logger.info("No sub agent responses to prepend")
            return False

        if self._main_agent_message is None:
            raise ValueError(
                "Main agent message is not set, the `run` method must be called first"
            )

        existing_refs = {
            ref.source_id: ref.sequence_number
            for ref in loop_response.message.references
        }

        _consolidate_references_in_place(
            list(self._assistant_id_to_tool_info.values()), existing_refs, loop_response
        )

        answers = []
        for assistant_id in self._assistant_id_to_tool_info.keys():
            messages = self._assistant_id_to_tool_info[assistant_id]["responses"]

            for sequence_number in sorted(messages):
                message = messages[sequence_number]
                tool_info = self._assistant_id_to_tool_info[assistant_id]

                display_mode = tool_info["display_config"].mode
                display_name = tool_info["display_name"]
                if len(messages) > 1:
                    display_name += f" {sequence_number}"

                answers.append(
                    _build_sub_agent_answer_display(
                        display_name=display_name,
                        assistant_id=assistant_id,
                        display_mode=display_mode,
                        answer=message["text"],
                        add_quote_border=tool_info["display_config"].add_quote_border,
                        add_block_border=tool_info["display_config"].add_block_border,
                    )
                )

                loop_response.message.references.extend(
                    ContentReference(
                        message_id=self._main_agent_message["id"],
                        source_id=ref["sourceId"],
                        url=ref["url"] or "",
                        source=ref["source"],
                        name=ref["name"],
                        sequence_number=ref["sequenceNumber"],
                    )
                    for ref in message["references"]
                )

        loop_response.message.text = (
            "\n\n".join(answers) + "<br>\n\n" + loop_response.message.text.strip()
        )

        return True

    @override
    async def remove_from_text(self, text) -> str:
        for assistant_id, tool_info in self._assistant_id_to_tool_info.items():
            display_config = tool_info["display_config"]
            if display_config.remove_from_history:
                text = _remove_sub_agent_answer_from_text(
                    display_mode=display_config.mode,
                    text=text,
                    assistant_id=assistant_id,
                    add_quote_border=display_config.add_quote_border,
                    add_block_border=display_config.add_block_border,
                )
        return text

    def register_sub_agent_tool(
        self, tool: SubAgentTool, display_config: SubAgentDisplayConfig
    ) -> None:
        if display_config.mode == SubAgentResponseDisplayMode.HIDDEN:
            logger.info(
                "Sub agent tool %s has display mode `hidden`, responses will be ignored.",
                tool.config.assistant_id,
            )
            return

        if tool.config.assistant_id not in self._assistant_id_to_tool_info:
            tool.subscribe(self)
            self._assistant_id_to_tool_info[tool.config.assistant_id] = (
                _SubAgentToolInfo(
                    display_config=display_config,
                    name=tool.name,
                    display_name=tool.display_name(),
                    responses={},
                )
            )

    def notify_sub_agent_response(
        self, response: SpaceMessage, sub_agent_assistant_id: str, sequence_number: int
    ) -> None:
        if sub_agent_assistant_id not in self._assistant_id_to_tool_info:
            logger.warning(
                "Unknown assistant id %s received, message will be ignored.",
                sub_agent_assistant_id,
            )
            return

        if response["text"] is None:
            logger.warning(
                "Sub agent response %s has no text, message will be ignored.",
                sequence_number,
            )
            return

        self._assistant_id_to_tool_info[sub_agent_assistant_id]["responses"][
            sequence_number
        ] = {
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
    messages: list[_SubAgentToolInfo],
    existing_refs: dict[str, int],
    loop_response: LanguageModelStreamResponse,
) -> None:
    start_index = max(existing_refs.values(), default=0) + 1

    for assistant_tool_info in messages:
        assistant_messages = assistant_tool_info["responses"]

        for sequence_number in sorted(assistant_messages):
            message = assistant_messages[sequence_number]

            references = message["references"]
            if len(references) == 0:
                logger.debug(
                    "Message from assistant %s with sequence number %s does not contain any references",
                    assistant_tool_info["display_name"],
                    sequence_number,
                )
                continue

            references = list(sorted(references, key=lambda ref: ref["sequenceNumber"]))
            ref_map = {}
            message_new_refs = []

            for reference in references:
                source_id = reference["sourceId"]
                if source_id not in existing_refs:
                    message_new_refs.append(reference)
                    existing_refs[source_id] = start_index
                    start_index += 1

                reference_num = existing_refs[source_id]
                ref_map[reference["sequenceNumber"]] = reference_num
                reference["sequenceNumber"] = reference_num

            loop_response.message.text = (
                _replace_sub_agent_references_in_main_agent_message(
                    loop_response.message.text,
                    assistant_tool_info["name"],
                    sequence_number,
                    ref_map,
                )
            )
            message["text"] = _replace_references_in_text(message["text"], ref_map)
            message["references"] = message_new_refs


def _replace_sub_agent_references_in_main_agent_message(
    message: str, sub_agent_name: str, sequence_number: int, ref_map: dict[int, int]
) -> str:
    for old_seq_num, new_seq_num in ref_map.items():
        reference = SubAgentTool.get_sub_agent_reference_format(
            name=sub_agent_name,
            sequence_number=sequence_number,
            reference_number=old_seq_num,
        )
        message = re.sub(rf"\s*{reference}", f" <sup>{new_seq_num}</sup>", message)

    # Remove spaces between consecutive references
    message = re.sub(r"</sup>\s*<sup>", "</sup><sup>", message)
    return message
