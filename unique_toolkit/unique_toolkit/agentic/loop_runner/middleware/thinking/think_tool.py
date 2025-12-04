import json
from typing import Annotated

from pydantic import BaseModel, Field, create_model

from unique_toolkit import LanguageModelToolDescription
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

_THINK_TOOL_DESCRIPTION = """
Use this tool in order to think about the next step to take.

Instructions:
- Consider the user input and the context of the conversation.
- Consider any previous tool calls, their results and the instructions related to the available tool calls.
- Consider any failed tool calls.
Goals:
- Output a plan for the next step. It MUST be justified, meaning that you MUST explain why you choose to take this step.
- You MUST recover from any failed tool calls.
- You MUST explain what tool calls to call next and why.
- If ready to answer the user, justify why you have gathered enough information/ tried all possible ways and failed.
- If ready to answer the user, REMEMBER and mention any previous instructions you have in the history. This is a CRUCIAL step.
""".strip()

_DEFAULT_THINKING_PARAM_DESCRIPTION = """
Next step description:
- Decide what to do next.
- Justify it THOROUGLY.
""".strip()


class ThinkToolParametersConfig(BaseModel):
    thinking_param_description: str = Field(
        default=_DEFAULT_THINKING_PARAM_DESCRIPTION,
        description="The description of the thinking parameter.",
    )


class ThinkToolConfig(BaseModel):
    model_config = get_configuration_dict()

    tool_name: str = "think_tool"
    tool_description: str = _THINK_TOOL_DESCRIPTION
    parameters: (
        Annotated[str, Field(title="Custom JSON Schema")]
        | Annotated[ThinkToolParametersConfig, Field(title="Default Configuration")]
    ) = Field(
        default=ThinkToolParametersConfig(),
        description="Configuration for the tool parameters. Can be a string representing a JSON schema object.",
    )


def get_think_tool(config: ThinkToolConfig) -> LanguageModelToolDescription:
    if isinstance(config.parameters, str):
        parameters = json.loads(config.parameters)
    else:
        parameters = create_model(
            config.tool_name + "_parameters",
            thinking=(
                str,
                Field(description=config.parameters.thinking_param_description),
            ),
        ).model_json_schema()

    return LanguageModelToolDescription(
        name=config.tool_name,
        description=config.tool_description,
        parameters=parameters,
    )
