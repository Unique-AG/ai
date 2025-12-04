from pydantic import BaseModel, Field, create_model

from unique_toolkit._common.pydantic_helpers import get_configuration_dict

_THINKING_SCHEMA_DESCRIPTION = """
Think about the next step to take.

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

IMPORTANT:
- Tools will be available after the planning step.
""".strip()

_DEFAULT_THINKING_PARAM_DESCRIPTION = """
Next step description:
- Decide what to do next.
- Justify it THOROUGLY.
""".strip()


class ThinkingSchemaConfig(BaseModel):
    model_config = get_configuration_dict()

    description: str = Field(
        default=_THINKING_SCHEMA_DESCRIPTION,
        description="The description of the thinking schema.",
    )
    thinking_param_description: str = Field(
        default=_DEFAULT_THINKING_PARAM_DESCRIPTION,
        description="The description of the thinking parameter.",
    )


def get_thinking_schema(config: ThinkingSchemaConfig) -> type[BaseModel]:
    return create_model(
        "thinking",
        thinking=(
            str,
            Field(description=config.thinking_param_description),
        ),
        __doc__=config.description,
    )
