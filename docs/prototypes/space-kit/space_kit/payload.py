"""Turns a template space (GET /space/{id}) plus a plan into request bodies."""

import copy

from pydantic import Field

from space_kit.base import (
    JsonObject,
    JsonValue,
    KitModel,
    SpaceKitError,
    as_list,
    as_object,
    text_or_empty,
)
from space_kit.mcp import (
    McpCatalog,
    McpPlan,
    Selection,
    apply_changes,
    check_restricted,
    sync_config_tools,
    template_selection,
    to_request,
)
from space_kit.paths import Assignment, flatten, get_path, set_path

CONDUCT_UI_TYPE = "SWAPPABLE_INTELLIGENCE"
PROJECT_NAME_PATH = "space.projectName"

COPIED_FIELDS = (
    "explanation",
    "alert",
    "chatUpload",
    "languageModel",
    "isExternal",
    "isPinned",
    "allowModelSwitching",
    "uiType",
    "settings",
    "isSubAgent",
    "subAgentSettings",
)
SPACE_FIELD_OVERRIDES = frozenset(
    {
        "explanation",
        "alert",
        "chatUpload",
        "languageModel",
        "isExternal",
        "isPinned",
        "allowModelSwitching",
        "switchableLanguageModels",
        "assistantPrompts",
    }
)
MODULE_FIELDS = (
    "name",
    "description",
    "weight",
    "isExternal",
    "isCustomInstructionEnabled",
    "toolDefinition",
)
NOT_COPIED = {
    "scopeRules": "scope rules (GraphQL only; set them in the admin UI)",
    "subAgents": "sub-agent links",
    "briefing": "the briefing link",
    "title": "title",
    "subtitle": "subtitle",
    "goals": "goals",
    "inputPlaceholder": "input placeholder",
}


class ClonePlan(KitModel):
    name: str
    template_id: str
    explanation: str | None = None
    assignments: tuple[Assignment, ...] = ()
    settings: tuple[Assignment, ...] = ()
    space_fields: JsonObject = Field(default_factory=dict)
    mcp: McpPlan = McpPlan()
    allow_new_keys: bool = False
    keep_project_name: bool = False


class McpContext(KitModel):
    catalog: McpCatalog
    id_map: dict[str, str] = Field(default_factory=dict)
    drop_servers: frozenset[str] = frozenset()
    space_id: str | None = None


class BuiltPayload(KitModel):
    payload: JsonObject
    configuration: JsonObject
    selection: Selection
    changed_paths: tuple[str, ...]
    warnings: tuple[str, ...]


def fallback_module(*, space: JsonObject) -> JsonObject:
    modules = [
        m
        for m in as_list(value=space.get("modules"), what="modules")
        if isinstance(m, dict)
    ]
    wanted = space.get("fallbackModule")
    named = [m for m in modules if m.get("name") == wanted]
    if len(named) == 1:
        return named[0]
    if len(modules) == 1:
        return modules[0]
    msg = (
        f"cannot find the fallback module {wanted!r} among "
        f"{[m.get('name') for m in modules]}"
    )
    raise SpaceKitError(msg)


def module_configuration(*, space: JsonObject) -> JsonObject:
    module = fallback_module(space=space)
    return as_object(
        value=module.get("configuration") or {}, what="module configuration"
    )


def apply_assignments(
    *,
    data: JsonObject,
    assignments: tuple[Assignment, ...],
    allow_new_keys: bool,
) -> JsonObject:
    result = data
    for assignment in assignments:
        result = set_path(
            data=result, assignment=assignment, allow_new_keys=allow_new_keys
        )
    return result


def _with_project_name(
    *, configuration: JsonObject, name: str, keep: bool
) -> JsonObject:
    if keep:
        return configuration
    try:
        _ = get_path(data=configuration, path=PROJECT_NAME_PATH)
    except SpaceKitError:
        return configuration
    return set_path(
        data=configuration,
        assignment=Assignment(path=PROJECT_NAME_PATH, value=name),
        allow_new_keys=False,
    )


def changed_paths(*, before: JsonObject, after: JsonObject) -> tuple[str, ...]:
    left = flatten(data=before)
    right = flatten(data=after)
    return tuple(
        sorted(
            path
            for path in left.keys() | right.keys()
            if left.get(path) != right.get(path) or (path in left) != (path in right)
        )
    )


def _prompt_requests(*, value: JsonValue) -> list[JsonValue]:
    prompts: list[JsonValue] = []
    for item in as_list(value=value, what="assistantPrompts"):
        if not isinstance(item, dict):
            continue
        prompt: JsonObject = {
            "title": item.get("title"),
            "prompt": item.get("prompt"),
        }
        if isinstance(item.get("order"), int):
            prompt["order"] = item.get("order")
        prompts.append(prompt)
    return prompts


def _switchable_models(*, value: JsonValue) -> list[JsonValue]:
    keep = (
        "displayName",
        "languageModel",
        "temperature",
        "additionalLLMOptions",
    )
    return [
        {key: item[key] for key in keep if item.get(key) is not None}
        for item in as_list(value=value, what="switchableLanguageModels")
        if isinstance(item, dict)
    ]


def copied_fields(*, template: JsonObject) -> JsonObject:
    fields: JsonObject = {
        key: copy.deepcopy(template[key])
        for key in COPIED_FIELDS
        if template.get(key) is not None
    }
    models = _switchable_models(value=template.get("switchableLanguageModels"))
    if models:
        fields["switchableLanguageModels"] = models
    prompts = _prompt_requests(value=template.get("assistantPrompts"))
    if prompts:
        fields["assistantPrompts"] = prompts
    return fields


def not_copied_notices(*, template: JsonObject) -> list[str]:
    return [
        f"not copied: {label}"
        for key, label in NOT_COPIED.items()
        if template.get(key) not in (None, "", [], {})
    ]


def _check_space_fields(*, fields: JsonObject) -> None:
    unknown = set(fields) - SPACE_FIELD_OVERRIDES
    if unknown:
        msg = (
            f"unsupported space field(s) {sorted(unknown)}; allowed: "
            f"{sorted(SPACE_FIELD_OVERRIDES)}"
        )
        raise SpaceKitError(msg)


def module_requests(
    *, template: JsonObject, configuration: JsonObject
) -> list[JsonValue]:
    fallback = fallback_module(space=template)
    requests: list[JsonValue] = []
    for module in as_list(value=template.get("modules"), what="modules"):
        if not isinstance(module, dict):
            continue
        request: JsonObject = {
            key: copy.deepcopy(module[key])
            for key in MODULE_FIELDS
            if module.get(key) is not None
        }
        is_fallback = module.get("name") == fallback.get("name")
        request["configuration"] = (
            configuration
            if is_fallback
            else copy.deepcopy(module.get("configuration") or {})
        )
        requests.append(request)
    return requests


def build_selection(
    *, template: JsonObject, plan: McpPlan, context: McpContext
) -> tuple[Selection, list[str]]:
    warnings: list[str] = []
    selection: Selection = {}
    if not plan.replace:
        base = template_selection(
            space=template, catalog=context.catalog, id_map=context.id_map
        )
        selection = base.selection
        warnings.extend(base.warnings)
    selection = apply_changes(
        selection=selection, changes=plan.changes, catalog=context.catalog
    )
    checked = check_restricted(
        selection=selection,
        catalog=context.catalog,
        space_id=context.space_id,
        skip=plan.skip_restricted,
    )
    warnings.extend(checked.warnings)
    return checked.selection, warnings


def build_configuration(
    *,
    template: JsonObject,
    plan: ClonePlan,
    selection: Selection,
    context: McpContext,
) -> JsonObject:
    configuration = _with_project_name(
        configuration=module_configuration(space=template),
        name=plan.name,
        keep=plan.keep_project_name,
    )
    configuration = sync_config_tools(
        configuration=configuration,
        selection=selection,
        catalog=context.catalog,
        id_map=context.id_map,
        drop_servers=context.drop_servers,
        disable_unselected=plan.mcp.replace,
    )
    return apply_assignments(
        data=configuration,
        assignments=plan.assignments,
        allow_new_keys=plan.allow_new_keys,
    )


def build_settings(
    *, template: JsonObject, assignments: tuple[Assignment, ...]
) -> tuple[JsonObject, list[str]]:
    settings = as_object(value=template.get("settings") or {}, what="space settings")
    new_keys = [a.path for a in assignments if a.path.split(".")[0] not in settings]
    warnings = [f"new settings key: {path}" for path in new_keys]
    updated = apply_assignments(
        data=settings, assignments=assignments, allow_new_keys=True
    )
    return updated, warnings


def build_create_payload(
    *, template: JsonObject, plan: ClonePlan, context: McpContext
) -> BuiltPayload:
    _check_space_fields(fields=plan.space_fields)
    selection, warnings = build_selection(
        template=template, plan=plan.mcp, context=context
    )
    configuration = build_configuration(
        template=template, plan=plan, selection=selection, context=context
    )
    settings, settings_warnings = build_settings(
        template=template, assignments=plan.settings
    )
    payload: JsonObject = {
        **copied_fields(template=template),
        **copy.deepcopy(plan.space_fields),
        "name": plan.name,
        "fallbackModule": text_or_empty(value=template.get("fallbackModule"))
        or text_or_empty(value=fallback_module(space=template).get("name")),
        "modules": module_requests(template=template, configuration=configuration),
        "mcpServers": to_request(selection=selection),
    }
    if settings:
        payload["settings"] = settings
    if plan.explanation is not None:
        payload["explanation"] = plan.explanation
    return BuiltPayload(
        payload=payload,
        configuration=configuration,
        selection=selection,
        changed_paths=changed_paths(
            before=module_configuration(space=template), after=configuration
        ),
        warnings=(
            *warnings,
            *settings_warnings,
            *not_copied_notices(template=template),
        ),
    )


def build_update_payload(
    *, space: JsonObject, plan: ClonePlan, context: McpContext
) -> BuiltPayload:
    """PATCH body for an existing space. The module configuration is
    replaced as a whole by the API, so the full edited copy is sent."""
    _check_space_fields(fields=plan.space_fields)
    selection, warnings = build_selection(
        template=space, plan=plan.mcp, context=context
    )
    edited = plan.model_copy(update={"keep_project_name": True})
    configuration = build_configuration(
        template=space, plan=edited, selection=selection, context=context
    )
    settings, settings_warnings = build_settings(
        template=space, assignments=plan.settings
    )
    module = fallback_module(space=space)
    payload: JsonObject = {
        **copy.deepcopy(plan.space_fields),
        "modules": [{"moduleId": module.get("id"), "configuration": configuration}],
    }
    if plan.mcp.changes or plan.mcp.replace:
        payload["mcpServers"] = to_request(selection=selection)
    if plan.settings:
        payload["settings"] = settings
    if plan.explanation is not None:
        payload["explanation"] = plan.explanation
    return BuiltPayload(
        payload=payload,
        configuration=configuration,
        selection=selection,
        changed_paths=changed_paths(
            before=module_configuration(space=space), after=configuration
        ),
        warnings=(*warnings, *settings_warnings),
    )
