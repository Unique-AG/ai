from __future__ import annotations

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.experimental.skill_tool.config import SkillToolConfig
from unique_toolkit.agentic.tools.experimental.skill_tool.prompt import (
    format_skill_listing,
)
from unique_toolkit.agentic.tools.experimental.skill_tool.schemas import (
    SkillDefinition,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

SKILL_ALREADY_LOADED_TAG = "skill_loaded"


def normalize_skill_name(skill: str) -> str:
    """Strip whitespace and a leading ``/`` from a skill name."""
    skill = skill.strip()
    if skill.startswith("/"):
        return skill[1:]
    return skill


class SkillTool(Tool[SkillToolConfig]):
    """Tool that lets the agent activate a named skill.

    The agent calls this with a ``skill_name`` it sees in the skill listing
    (system prompt).  The tool looks up the skill in the registry and returns
    its full content as the tool response so the agent can follow those
    instructions.
    """

    name = "Skill"

    def __init__(
        self,
        event: ChatEvent,
        registry: dict[str, SkillDefinition],
        config: SkillToolConfig,
    ) -> None:
        super().__init__(config, event)
        self._registry = registry

    @property
    def registry(self) -> dict[str, SkillDefinition]:
        return self._registry

    def display_name(self) -> str:
        return "Skill"

    def tool_description(self) -> LanguageModelToolDescription:
        skill_names = list(self._registry.keys())

        skill_name_schema: dict = {
            "type": "string",
            "description": self.config.tool_parameter_description_skill_name,
        }
        if skill_names:
            skill_name_schema["enum"] = skill_names

        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": skill_name_schema,
                    "arguments": {
                        "type": "string",
                        "description": self.config.tool_parameter_description_arguments,
                    },
                },
                "required": ["skill_name"],
            },
        )

    def tool_description_for_system_prompt(self) -> str:
        listing = format_skill_listing(
            skills=list(self._registry.values()),
            config=self.config,
        )
        parts = [self.config.tool_description_for_system_prompt]
        if listing:
            parts.append(f"\nAvailable skills:\n{listing}")
        return "\n".join(parts)

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        args = tool_call.arguments or {}
        raw_skill_name: str = args.get("skill_name", "")
        arguments: str = args.get("arguments", "")

        if not raw_skill_name or not raw_skill_name.strip():
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message="skill_name must be a non-empty string.",
            )

        skill_name = normalize_skill_name(raw_skill_name)
        skill = self._registry.get(skill_name)

        if skill is None:
            available = ", ".join(sorted(self._registry.keys()))
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message=(
                    f"Unknown skill: '{skill_name}'. "
                    f"Available skills: {available}"
                ),
            )

        content_parts = [
            f"<{SKILL_ALREADY_LOADED_TAG}>{skill_name}</{SKILL_ALREADY_LOADED_TAG}>",
            f"Skill '{skill_name}' is now active. Follow the instructions below.",
            "",
            skill.content,
        ]
        if arguments:
            content_parts.append(f"\nUser-provided arguments: {arguments}")

        return ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content="\n".join(content_parts),
            system_reminder=(
                f"The skill '{skill_name}' has been loaded. "
                "Follow its instructions now. Do NOT call the Skill tool "
                "again for the same skill in this turn."
            ),
        )

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []


ToolFactory.register_tool(SkillTool, SkillToolConfig)
