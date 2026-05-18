from __future__ import annotations

import json
from logging import Logger

from unique_skill_tool.service import SkillTool
from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.agentic.tools.tool_manager import (
    ResponsesApiToolManager,
    ToolManager,
)
from unique_toolkit.app.schemas import ChatEventAdditionalParameters
from unique_toolkit.content import Content
from unique_toolkit.language_model.schemas import (
    REASONING_EFFORT_ORDER,
    to_reasoning_effort,
)

from unique_orchestrator.config import UniqueAIConfig


def resolve_other_options(
    config: UniqueAIConfig,
    tool_manager: ToolManager | ResponsesApiToolManager,
    logger: Logger,
) -> dict:
    """Build ``other_options`` for the LLM call.

    Merges ``additional_llm_options`` from config with the highest
    ``thinking_level`` declared across all skills activated in this run.
    The final effort level is the highest value among the config setting
    (if any) and the skill hint (if any).

    Determines the active API first, then reads the effort from the
    matching format and writes the resolved value back in that same format:
    - completions API: ``reasoning_effort: "high"``
    - responses API: ``reasoning: {"effort": "high"}``
    """

    options: dict = dict(config.agent.experimental.additional_llm_options)

    skill_tool = tool_manager.get_tool_by_name(SkillTool.name)
    if not isinstance(skill_tool, SkillTool) or skill_tool.max_thinking_level is None:
        return options

    skill_max: str = skill_tool.max_thinking_level

    use_responses_api: bool = (
        config.agent.experimental.responses_api_config.use_responses_api
        or config.agent.experimental.use_responses_api
    )

    if use_responses_api:
        reasoning_raw = options.get("reasoning")
        if isinstance(reasoning_raw, str):
            try:
                reasoning_dict: dict = json.loads(reasoning_raw)
            except (json.JSONDecodeError, ValueError):
                reasoning_dict = {}
        elif isinstance(reasoning_raw, dict):
            reasoning_dict = reasoning_raw
        else:
            reasoning_dict = {}
        config_effort: str | None = reasoning_dict.get("effort")
    else:
        config_effort = options.get("reasoning_effort")

    valid_config_effort: str | None = None
    if config_effort is not None:
        try:
            valid_config_effort = to_reasoning_effort(config_effort)
        except ValueError:
            logger.warning(
                "additional_llm_options contains an unrecognised "
                "reasoning_effort value %r — cannot compare it with "
                "the skill's thinking_level; using skill minimum %r instead.",
                config_effort,
                skill_max,
            )

    resolved_effort: str = (
        skill_max
        if valid_config_effort is None
        else max([valid_config_effort, skill_max], key=REASONING_EFFORT_ORDER.index)
    )

    supported_efforts = config.space.language_model.supported_reasoning_efforts
    if supported_efforts is not None:
        if len(supported_efforts) == 0:
            logger.warning(
                "Skipping reasoning_effort %r: model %s does not support reasoning_effort.",
                resolved_effort,
                config.space.language_model.name,
            )
            return options
        if resolved_effort not in supported_efforts:
            logger.warning(
                "Skipping reasoning_effort %r: model %s only supports %s.",
                resolved_effort,
                config.space.language_model.name,
                supported_efforts,
            )
            return options

    if use_responses_api:
        existing_reasoning: dict = (
            dict(options["reasoning"])
            if isinstance(options.get("reasoning"), dict)
            else {}
        )
        existing_reasoning["effort"] = resolved_effort
        options["reasoning"] = existing_reasoning
    else:
        options["reasoning_effort"] = resolved_effort

    return options


def filter_uploaded_documents_by_selection(
    documents: list[Content],
    additional_parameters: ChatEventAdditionalParameters | None,
    company_id: str,
) -> list[Content]:
    """Return only the documents the user has actively selected.

    Returns *all* documents unchanged when:
    - the feature flag is disabled for ``company_id``,
    - ``additional_parameters`` is ``None``.
    """
    if not feature_flags.enable_selected_uploaded_files_un_18215.is_enabled(company_id):
        return documents

    if additional_parameters is None:
        return documents

    selected_ids = additional_parameters.selected_uploaded_file_ids
    return [doc for doc in documents if doc.id in selected_ids]
