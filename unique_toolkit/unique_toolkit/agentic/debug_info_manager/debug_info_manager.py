from collections import defaultdict
from typing import Any, Required, TypedDict

from unique_toolkit.agentic.tools.openai_builtin import OpenAICodeInterpreterTool
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    ArtifactsDebugInfo,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool_manager import ToolManager
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
    LanguageModelTokenUsage,
    ResponsesLanguageModelStreamResponse,
)


class AnalyticsTool(TypedDict, total=False):
    name: Required[str]
    display_name: Required[str]
    is_forced: bool
    is_exclusive: bool
    is_sub_agent: bool
    is_mcp: bool
    loop_iteration: int


class AnalyticsSkill(TypedDict):
    name: str
    content_id: str
    is_forced: bool


class AnalyticsLanguageModel(TypedDict):
    name: str
    family: str
    provider: str


class AnalyticsToolName(TypedDict):
    name: str
    display_name: str


class AnalyticsTokenUsage(TypedDict):
    model_name: str
    completion_tokens: int | None
    prompt_tokens: int | None
    total_tokens: int | None
    reasoning_tokens: int | None
    cached_tokens: int | None
    cache_write_tokens: int | None


class Analytics(TypedDict):
    answer_length: int
    artifacts_created_count: int | None
    artifacts_created_filetype: list[str] | None
    context_memory_updated: bool | None
    language_model: AnalyticsLanguageModel
    loop_iteration_count: int
    mcp_tool_names_used: list[AnalyticsToolName]
    # Total size of artifacts/files created this turn, in MiB. None when Code
    # Interpreter did not run; 0.0 when it ran but produced nothing.
    output_size: float | None
    references_count: int
    skills_used: list[AnalyticsSkill]
    subagent_names_used: list[AnalyticsToolName]
    tokens: list[AnalyticsTokenUsage]
    tool_call_count: int
    tools_used: list[AnalyticsTool]
    total_time_to_answer_ms: int | None
    user_prompt_length: int


class DebugInfoManager:
    def __init__(self):
        self.debug_info: dict[str, Any] = {"tools": []}

    def extract_tool_debug_info(
        self,
        tool_call_responses: list[ToolCallResponse],
        loop_iteration_index: int | None = None,
    ) -> None:
        for tool_call_response in tool_call_responses:
            debug_info = (
                tool_call_response.debug_info.copy()
                if tool_call_response.debug_info
                else {}
            )
            tool_info: dict[str, Any] = {
                "name": tool_call_response.name,
                "info": debug_info,
            }
            if debug_info.get("mcp_server"):
                tool_info["mcp_server"] = debug_info["mcp_server"]
            if loop_iteration_index is not None:
                tool_info["info"]["loop_iteration"] = loop_iteration_index
            self.debug_info["tools"].append(tool_info)

    def extract_builtin_tool_debug_info(
        self,
        stream_response: LanguageModelStreamResponse,
        tool_manager: ToolManager,
        loop_iteration_index: int | None = None,
    ) -> None:
        self.debug_info["tools"].extend(
            _extract_tool_calls_from_stream_response(
                stream_response, tool_manager, loop_iteration_index
            )
        )

    def add(self, key: str, value: Any) -> None:
        self.debug_info = self.debug_info | {key: value}

    def get(self) -> dict[str, Any]:
        return self.debug_info

    def add_analytics(
        self,
        skills: list[dict[str, Any]],
        language_model: AnalyticsLanguageModel,
        tool_display_names: dict[str, str],
        references: int = 0,
        user_prompt_length: int = 0,
        answer_length: int = 0,
        loop_iteration_count: int = 0,
        total_time_to_answer_ms: int | None = None,
        artifacts: ArtifactsDebugInfo | None = None,
        context_memory_updated: bool | None = None,
        invocations: list[LanguageModelInvocationStats] | None = None,
    ) -> None:
        """Add a stable 'analytics' snapshot for downstream ROI/usage reporting.

        Copies the current `tools` list (with each tool's info reduced to
        attribution fields only), the given `skills` list, usage counts, prompt
        and answer lengths, and language-model attribution into a new
        `analytics` key. Later appends to `debug_info["tools"]` (e.g. from
        extract_tool_debug_info) can't leak into the frozen snapshot. Existing
        top-level keys (`tools`, `skills`, ...) are left untouched, so this is
        additive for consumers reading the old shape.
        """
        analytics_tools = [
            _to_analytics_tool_entry(tool, tool_display_names)
            for tool in self.debug_info.get("tools", [])
        ]
        # Artifacts are recorded at the postprocessor seam (Code Interpreter's
        # DisplayCodeInterpreterFilesPostProcessor) into debug_info["artifacts"].
        # Absent when no Code Interpreter ran this turn → artifact fields stay
        # None, preserving the always-present, null-when-unknown contract.
        analytics = Analytics(
            tools_used=analytics_tools,
            tool_call_count=len(analytics_tools),
            skills_used=[
                AnalyticsSkill(
                    name=skill["name"],
                    content_id=skill["content_id"],
                    is_forced=skill["is_forced"],
                )
                for skill in skills
            ],
            references_count=references,
            user_prompt_length=user_prompt_length,
            answer_length=answer_length,
            language_model=language_model.copy(),
            loop_iteration_count=loop_iteration_count,
            subagent_names_used=_unique_tool_names(analytics_tools, "is_sub_agent"),
            mcp_tool_names_used=_unique_tool_names(analytics_tools, "is_mcp"),
            tokens=_aggregate_tokens_by_model(invocations or []),
            total_time_to_answer_ms=total_time_to_answer_ms,
            artifacts_created_count=artifacts["count"] if artifacts else None,
            artifacts_created_filetype=artifacts["filetypes"] if artifacts else None,
            output_size=artifacts["output_size"] if artifacts else None,
            # None when the user-memory postprocessor is not activated for this
            # turn; True/False when it ran and did/didn't update the profile.
            context_memory_updated=context_memory_updated,
        )
        self.add("analytics", analytics)


def _aggregate_tokens_by_model(
    invocations: list[LanguageModelInvocationStats],
) -> list[AnalyticsTokenUsage]:
    usages_by_model: dict[str, list[LanguageModelTokenUsage]] = defaultdict(list)
    for invocation in invocations:
        usages_by_model[str(invocation.model_name)].append(invocation.token_usage)

    totals: list[AnalyticsTokenUsage] = []
    for model_name in sorted(usages_by_model):
        usage = LanguageModelTokenUsage.sum_usages(usages_by_model[model_name])
        if usage is None:
            continue
        totals.append(
            AnalyticsTokenUsage(
                model_name=model_name,
                completion_tokens=usage.completion_tokens,
                prompt_tokens=usage.prompt_tokens,
                total_tokens=usage.total_tokens,
                reasoning_tokens=usage.reasoning_tokens,
                cached_tokens=usage.cached_tokens,
                cache_write_tokens=usage.cache_write_tokens,
            )
        )
    return totals


def _unique_tool_names(
    analytics_tools: list[AnalyticsTool], flag: str
) -> list[AnalyticsToolName]:
    """Dedupe the tools carrying `flag` into `{name, display_name}` entries.

    Keyed on the stable `name` so downstream reporting can join on a stable
    identifier while still carrying the user-facing `display_name` for labels.
    """
    unique: dict[str, AnalyticsToolName] = {}
    for tool in analytics_tools:
        if tool.get(flag) and tool["name"] not in unique:
            unique[tool["name"]] = AnalyticsToolName(
                name=tool["name"],
                display_name=tool["display_name"],
            )
    return list(unique.values())


def _to_analytics_tool_entry(
    tool: dict[str, Any], tool_display_names: dict[str, str]
) -> AnalyticsTool:
    """Return an analytics-safe copy of a tool debug-info entry.

    Keeps only tool attribution fields.
    """
    info = tool.get("info") or {}
    name = tool["name"]
    analytics_tool = AnalyticsTool(
        name=name,
        display_name=tool_display_names.get(name) or name,
    )
    if "is_forced" in info:
        analytics_tool["is_forced"] = info["is_forced"]
    if "is_exclusive" in info:
        analytics_tool["is_exclusive"] = info["is_exclusive"]
    if info.get("is_sub_agent"):
        analytics_tool["is_sub_agent"] = True
    if info.get("is_mcp") or tool.get("mcp_server"):
        analytics_tool["is_mcp"] = True
    if "loop_iteration" in info:
        analytics_tool["loop_iteration"] = info["loop_iteration"]
    return analytics_tool


def _extract_tool_calls_from_stream_response(
    stream_response: LanguageModelStreamResponse,
    tool_manager: ToolManager,
    loop_iteration_index: int | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(stream_response, ResponsesLanguageModelStreamResponse):
        return []

    seen = set()
    tool_infos = []

    for code_interpreter_call in stream_response.code_interpreter_calls:
        if code_interpreter_call.id in seen:
            continue

        seen.add(code_interpreter_call.id)
        tool_name = OpenAIBuiltInToolName.CODE_INTERPRETER

        is_exclusive = tool_name in tool_manager.get_exclusive_tools()
        is_forced = tool_name in tool_manager.get_tool_choices()

        debug_info = OpenAICodeInterpreterTool.get_debug_info(code_interpreter_call)

        if loop_iteration_index is not None:
            debug_info["loop_iteration"] = loop_iteration_index
        debug_info["is_exclusive"] = is_exclusive
        debug_info["is_forced"] = is_forced

        tool_infos.append(
            {
                "name": tool_name,
                "info": debug_info,
            }
        )

    return tool_infos
