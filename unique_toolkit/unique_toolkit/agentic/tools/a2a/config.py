import logging
from typing import Self

from pydantic import Field, model_validator

from unique_toolkit.agentic.tools.a2a.evaluation import SubAgentEvaluationConfig
from unique_toolkit.agentic.tools.a2a.postprocessing import (
    SubAgentDisplayConfig,
    SubAgentResponseDisplayMode,
)
from unique_toolkit.agentic.tools.a2a.tool import SubAgentToolConfig

_LOGGER = logging.getLogger(__name__)


# SubAgentToolConfig with display and evaluation configs
class ExtendedSubAgentToolConfig(SubAgentToolConfig):
    response_display_config: SubAgentDisplayConfig = Field(
        default_factory=SubAgentDisplayConfig,
        description="Configuration for how to display the sub-agent response.",
    )
    evaluation_config: SubAgentEvaluationConfig = Field(
        default_factory=SubAgentEvaluationConfig,
        description="Configuration for handling assessments of the sub-agent response.",
    )

    @model_validator(mode="after")
    def _ensure_response_display_config_off_when_sub_agent_response_passthrough(
        self,
    ) -> Self:
        if (
            self.passthrough_config.enabled
            and self.response_display_config.mode != SubAgentResponseDisplayMode.HIDDEN
        ):
            _LOGGER.warning(
                "SubAgent (assistant_id=%r): `passthrough_config.enabled=True` but `response_display_config.mode` is not HIDDEN. "
                "Overriding `response_display_config.mode` to HIDDEN.",
                self.assistant_id,
            )
            self.response_display_config.mode = SubAgentResponseDisplayMode.HIDDEN
        return self
