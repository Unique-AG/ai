from pydantic import Field

from unique_toolkit.agentic.tools.a2a.evaluation import SubAgentEvaluationConfig
from unique_toolkit.agentic.tools.a2a.postprocessing import SubAgentDisplayConfig
from unique_toolkit.agentic.tools.a2a.tool import SubAgentToolConfig


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
