import json
from typing import Annotated, Any

from pydantic import BaseModel, Field, RootModel, create_model

from unique_toolkit._common.pydantic_helpers import get_configuration_dict

_PLANNING_SCHEMA_DESCRIPTION = """
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

_DEFAULT_PLANNING_PARAM_DESCRIPTION = """
Next step description:
- Decide what to do next.
- Justify it THOROUGLY.
""".strip()


class DefaultPlanningSchemaConfig(BaseModel):
    """
    Configuration for the default planning schema, which is a simple json with a single field: "planning".
    """

    model_config = get_configuration_dict()

    description: str = Field(
        default=_PLANNING_SCHEMA_DESCRIPTION,
        description="Description of the planning schema. This will correspond to the description of the model in the json schema.",
    )
    plan_param_description: str = Field(
        default=_DEFAULT_PLANNING_PARAM_DESCRIPTION,
        description="The description of the `planning` parameter.",
    )


class PlanningSchemaConfig(RootModel[DefaultPlanningSchemaConfig | str]):
    model_config = get_configuration_dict()

    root: (
        Annotated[
            DefaultPlanningSchemaConfig,
            Field(
                description="Configuration for the default planning schema, which is a simple json dict with a single `plan` field.",
                title="Default Planning Schema Config",
            ),
        ]
        | Annotated[
            str,
            Field(
                description="Custom JSON Schema as string for the planning schema.",
                title="Custom Planning Schema Config",
            ),
        ]
    ) = Field(default=DefaultPlanningSchemaConfig())


def get_planning_schema(config: PlanningSchemaConfig) -> dict[str, Any]:
    if isinstance(config.root, DefaultPlanningSchemaConfig):
        return create_model(
            "Planning",
            plan=(
                str,
                Field(description=config.root.plan_param_description),
            ),
            __doc__=config.root.description,
        ).model_json_schema()

    return json.loads(config.root)
