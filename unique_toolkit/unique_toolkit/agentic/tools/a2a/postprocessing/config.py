from enum import StrEnum

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict


class SubAgentResponseDisplayMode(StrEnum):
    HIDDEN = "hidden"
    DETAILS_OPEN = "details_open"
    DETAILS_CLOSED = "details_closed"
    PLAIN = "plain"


class SubAgentDisplayConfig(BaseModel):
    model_config = get_configuration_dict()

    mode: SubAgentResponseDisplayMode = Field(
        default=SubAgentResponseDisplayMode.HIDDEN,
        description="Controls how to display the sub agent response.",
    )
    remove_from_history: bool = Field(
        default=True,
        description="If set, sub agent responses will be removed from the history on subsequent calls to the assistant.",
    )
    add_quote_border: bool = Field(
        default=True,
        description="If set, the sub agent response will be displayed as a quote.",
    )
    add_block_border: bool = Field(
        default=False,
        description="If set, the sub agent response will be displayed as a quote.",
    )
