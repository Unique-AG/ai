from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.generation.agentic.executor import ExecutionMode
from unique_swot.services.generation.agentic.prompts.config import AgenticPromptsConfig


class AgenticGeneratorConfig(BaseModel):
    model_config = get_configuration_dict()

    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.CONCURRENT,
        description="The execution mode to use for the agentic generator.",
    )
    max_concurrent_tasks: int = Field(
        default=10,
        description="The maximum number of concurrent tasks to use for the agentic generator. Only used if execution mode is concurrent.",
    )
    prompts_config: AgenticPromptsConfig = Field(
        default=AgenticPromptsConfig(),
        description="The prompts config for the agentic generator.",
    )
