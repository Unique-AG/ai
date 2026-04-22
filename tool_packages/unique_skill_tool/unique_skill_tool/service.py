from __future__ import annotations

import jinja2
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

from unique_skill_tool.config import SkillToolConfig
from unique_skill_tool.schemas import (
    SkillDefinition,
)
from unique_skill_tool.utils import (
    format_skill_listing,
    normalize_skill_name,
)


class SkillTool(Tool[SkillToolConfig]):
    """Tool that lets the agent activate a named skill.

    The agent calls this with a ``skill_name`` it sees in the skill listing
    (system prompt).  The tool looks up the skill in the skill registry
    and returns its full content as the tool response so the agent can
    follow those instructions.
    """

    name = "Skill"

    def __init__(
        self,
        event: ChatEvent,
        skill_registry: dict[str, SkillDefinition],
        config: SkillToolConfig,
    ) -> None:
        super().__init__(config, event)
        self._skill_registry = skill_registry

    @property
    def skill_registry(self) -> dict[str, SkillDefinition]:
        return self._skill_registry

    def display_name(self) -> str:
        return "Skill"

    def tool_description(self) -> LanguageModelToolDescription:
        skill_names = list(self._skill_registry.keys())

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
        """Static instructions for the system prompt.

        The skill listing is intentionally NOT rendered here. It is
        injected per-turn as a ``<system-reminder>`` block via
        ``SkillTool`` prompt / system-reminder split).
        """
        return self.config.tool_description_for_system_prompt

    def tool_description_for_user_prompt(self) -> str:
        return self.config.tool_description_for_user_prompt

    def tool_system_reminder(self) -> str:
        """Per-turn ``<system-reminder>`` block listing available skills.

        Renders :attr:`SkillToolConfig.tool_system_reminder_for_user_message` as a
        Jinja template with the budget-aware ``skill_list``. Returned
        verbatim by the orchestrator as a ``{"type": "text"}`` part
        on the latest user message every loop iteration (see
        ``unique_orchestrator._builders.inject_tool_reminders``), so
        the listing cannot go stale. Returns an empty string when the
        skill registry is empty or the reminder template is unset.
        """
        skills = list(self._skill_registry.values())
        if not skills or not self.config.tool_system_reminder_for_user_message:
            return ""

        listing = format_skill_listing(skills=skills, config=self.config)
        return jinja2.Template(
            self.config.tool_system_reminder_for_user_message
        ).render(skill_list=listing)

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
        skill = self._skill_registry.get(skill_name)

        if skill is None:
            available = ", ".join(sorted(self._skill_registry.keys()))
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                error_message=(
                    f"Unknown skill: '{skill_name}'. Available skills: {available}"
                ),
            )

        content_parts = [
            f"<skill_loaded>{skill_name}</skill_loaded>",
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
