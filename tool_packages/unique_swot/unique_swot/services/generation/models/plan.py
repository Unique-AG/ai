from enum import StrEnum

from pydantic import Field

from unique_swot.utils import StructuredOutputResult, StructuredOutputWithNotification


class GenerationPlanCommandType(StrEnum):
    CREATE_SECTION = "create_section"
    UPDATE_SECTION = "update_section"


class GenerationPlanCommand(StructuredOutputResult):
    reasoning: str = Field(
        description="The reasoning that led to the command. Need to be concise and backed with evidence."
    )
    command: GenerationPlanCommandType

    instruction: str = Field(
        description="The complete instruction to be executed. Should contain all the necessary details to ensure the command is executed correctly."
    )
    target_section_id: str | None = Field(
        description="The ID of the section to be executed. This is only used if the command is update_section"
    )
    source_facts_ids: list[str] = Field(
        description="The IDs of the source facts of similar nature that need to go into the section to be updated or created."
    )


class GenerationPlan(StructuredOutputWithNotification):
    commands: list[GenerationPlanCommand] = Field(
        description="The commands to be executed. The commands should be executed in order. Each command should target a specific section to be updated or created."
    )
