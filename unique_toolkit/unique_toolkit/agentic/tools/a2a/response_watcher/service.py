import datetime
import json
from typing import NamedTuple

import unique_sdk


def _clone_message(
    message: unique_sdk.Space.Message,
) -> unique_sdk.Space.Message:
    # copy.deepcopy does not work for instances of UniqueObject
    return json.loads(json.dumps(message))


class SubAgentResponse(NamedTuple):
    assistant_id: str
    name: str
    sequence_number: int
    message: unique_sdk.Space.Message
    timestamp: datetime.datetime

    def clone(self) -> "SubAgentResponse":
        return SubAgentResponse(
            assistant_id=self.assistant_id,
            name=self.name,
            sequence_number=self.sequence_number,
            message=_clone_message(self.message),
            timestamp=self.timestamp,
        )


class SubAgentResponseWatcher:
    """
    Save and retrieve sub agent responses immutably.
    """

    def __init__(self) -> None:
        self._response_registry: dict[str, list[SubAgentResponse]] = {}

    def notify_response(
        self,
        assistant_id: str,
        name: str,
        sequence_number: int,
        response: unique_sdk.Space.Message,
        timestamp: datetime.datetime,
    ) -> None:
        if assistant_id not in self._response_registry:
            self._response_registry[assistant_id] = []

        response = _clone_message(response)

        self._response_registry[assistant_id].append(
            SubAgentResponse(
                assistant_id=assistant_id,
                name=name,
                sequence_number=sequence_number,
                message=response,
                timestamp=timestamp,
            )
        )

    def get_responses(self, assistant_id: str) -> list[SubAgentResponse]:
        return _sort_responses(  # Always return a consistent order
            [response.clone() for response in self._response_registry.get(assistant_id, [])],
        )

    def get_all_responses(self) -> list[SubAgentResponse]:
        return _sort_responses(
            [
                response.clone()
                for sub_agent_responses in self._response_registry.values()
                for response in sub_agent_responses
            ],
        )


def _sort_responses(
    responses: list[SubAgentResponse],
) -> list[SubAgentResponse]:
    return sorted(
        responses,
        key=lambda response: (
            response.timestamp,
            response.assistant_id,
            response.sequence_number,
        ),
    )
