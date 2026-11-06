"""Prepare (read-only) and execute (writes) for clone, edit and delete."""

from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from space_kit.api import SpaceApi, Transport
from space_kit.base import JsonObject, JsonValue, KitModel, SpaceKitError
from space_kit.diff import DiffRow, diff_spaces
from space_kit.env import (
    HARNESS_EVAL_HOME_VARIABLE,
    KitConfig,
    Target,
    load_credentials,
    resolve_env_file,
)
from space_kit.ledger import Ledger, LedgerAction, LedgerEntry, now
from space_kit.mcp import (
    McpCatalog,
    attachment_server_ids,
    build_id_map,
    config_server_ids,
)
from space_kit.paths import flatten
from space_kit.payload import (
    BuiltPayload,
    McpContext,
    build_create_payload,
    build_update_payload,
    module_configuration,
)
from space_kit.register import (
    RegistryEntry,
    append_entry,
    build_entry,
    harness_eval_validator,
    read_spaces,
    render_entry,
    run_doctor,
)
from space_kit.spec import SpaceSpec, clone_plan

ENV_SPECIFIC_MARKERS = ("scope_", "Scope", "FolderId")


class Workspace:
    """Composition root: where env files, ledger and harness-eval live."""

    def __init__(
        self,
        *,
        home: Path,
        config: KitConfig,
        environ: Mapping[str, str],
        transport: Transport,
    ) -> None:
        self.home: Path = home
        self.config: KitConfig = config
        self.environ: Mapping[str, str] = environ
        self.transport: Transport = transport
        self.ledger: Ledger = Ledger(home=home)

    def env_file(self, *, target: Target, explicit: Path | None) -> Path:
        return resolve_env_file(
            target=target,
            explicit=explicit,
            environ=self.environ,
            config=self.config,
        )

    def api(self, *, target: Target, explicit: Path | None = None) -> SpaceApi:
        credentials = load_credentials(
            target=target,
            env_file=self.env_file(target=target, explicit=explicit),
        )
        return SpaceApi(credentials=credentials, transport=self.transport)

    def harness_eval_home(self) -> Path:
        configured = self.environ.get(HARNESS_EVAL_HOME_VARIABLE)
        if configured:
            return Path(configured)
        if self.config.harness_eval_home is not None:
            return self.config.harness_eval_home
        msg = (
            f"registration needs the harness-eval folder: set "
            f"{HARNESS_EVAL_HOME_VARIABLE} or harness_eval_home in envs.yaml"
        )
        raise SpaceKitError(msg)


class PreparedClone(KitModel):
    spec: SpaceSpec
    template: JsonObject
    built: BuiltPayload
    catalog: McpCatalog
    registry_entry: RegistryEntry | None = None
    warnings: tuple[str, ...] = ()


class CloneResult(KitModel):
    space_id: str
    verification: tuple[DiffRow, ...]
    registered_profile: str = ""
    doctor_exit_code: int | None = None


def _env_specific_paths(*, configuration: JsonObject) -> list[str]:
    return [
        path
        for path, value in flatten(data=configuration).items()
        if value not in (None, "", [], {})
        and any(marker in path for marker in ENV_SPECIFIC_MARKERS)
    ]


def _mcp_context(
    *,
    spec: SpaceSpec,
    template: JsonObject,
    target_catalog: McpCatalog,
    source_catalog: McpCatalog | None,
) -> tuple[McpContext, list[str]]:
    if source_catalog is None:
        return McpContext(catalog=target_catalog, id_map=dict(spec.mcp.map)), []
    source_ids = attachment_server_ids(space=template) | config_server_ids(
        configuration=module_configuration(space=template)
    )
    id_map, unmapped = build_id_map(
        source_ids=source_ids,
        source=source_catalog,
        target=target_catalog,
        explicit=dict(spec.mcp.map),
    )
    if unmapped and not spec.mcp.drop_unmapped:
        msg = (
            "MCP servers without a unique match on the target: "
            + "; ".join(unmapped)
            + ". Map them (--mcp-map source=target) or --drop-unmapped-mcp."
        )
        raise SpaceKitError(msg)
    dropped = frozenset(source_ids - set(id_map))
    warnings = [f"MCP server dropped (no match): {u}" for u in unmapped]
    context = McpContext(catalog=target_catalog, id_map=id_map, drop_servers=dropped)
    return context, warnings


def _registry_entry(
    *,
    workspace: Workspace,
    spec: SpaceSpec,
    built: BuiltPayload,
) -> RegistryEntry | None:
    if spec.registration is None:
        return None
    home = workspace.harness_eval_home()
    entry = build_entry(
        request=spec.registration,
        spaces=read_spaces(harness_eval_home=home),
        template_id=spec.template,
        target=spec.env.value,
        configuration=built.configuration,
        changed_paths=built.changed_paths,
    )
    probe = entry.model_copy(update={"assistant_id": "assistant_space_kit_probe"})
    text = render_entry(
        profile=spec.registration.profile,
        entry=probe,
        template_id=spec.template,
        today=date.today(),
    )
    _validate_only(home=home, text=text)
    return entry


def _validate_only(*, home: Path, text: str) -> None:
    original = (home / "spaces.yaml").read_text(encoding="utf-8")
    candidate = home / ".spaces.yaml.space-kit-probe"
    _ = candidate.write_text(original.rstrip("\n") + "\n\n" + text, encoding="utf-8")
    try:
        harness_eval_validator(harness_eval_home=home)(candidate)
    finally:
        candidate.unlink(missing_ok=True)


def prepare_clone(
    *, workspace: Workspace, spec: SpaceSpec, base_dir: Path
) -> PreparedClone:
    """Reads only. Builds and validates everything a create needs."""
    target_api = workspace.api(target=spec.env)
    source_api = (
        workspace.api(target=spec.from_env)
        if spec.from_env is not None and spec.from_env is not spec.env
        else None
    )
    template = (source_api or target_api).get_space(space_id=spec.template)
    target_catalog = McpCatalog.from_api(rows=target_api.list_mcp_servers())
    source_catalog = (
        McpCatalog.from_api(rows=source_api.list_mcp_servers()) if source_api else None
    )
    context, warnings = _mcp_context(
        spec=spec,
        template=template,
        target_catalog=target_catalog,
        source_catalog=source_catalog,
    )
    built = build_create_payload(
        template=template,
        plan=clone_plan(spec=spec, base_dir=base_dir),
        context=context,
    )
    if source_api is not None:
        warnings.extend(
            f"environment-specific value copied as is: {path}"
            for path in _env_specific_paths(configuration=built.configuration)
        )
    return PreparedClone(
        spec=spec,
        template=template,
        built=built,
        catalog=target_catalog,
        registry_entry=_registry_entry(workspace=workspace, spec=spec, built=built),
        warnings=(*built.warnings, *warnings),
    )


def _expected_space(*, prepared: PreparedClone, created: JsonObject) -> JsonObject:
    """What GET should return: the fetched space with every field the
    payload set replaced by the payload value."""
    payload = prepared.built.payload
    expected: JsonObject = {
        **created,
        **{
            key: value
            for key, value in payload.items()
            if key not in ("modules", "mcpServers")
        },
    }
    wanted_module = payload.get("fallbackModule")
    modules = created.get("modules")
    expected["modules"] = [
        {**module, "configuration": prepared.built.configuration}
        if isinstance(module, dict) and module.get("name") == wanted_module
        else module
        for module in (modules if isinstance(modules, list) else [])
    ]
    return expected


def verify_created(*, prepared: PreparedClone, fetched: JsonObject) -> list[DiffRow]:
    rows = diff_spaces(
        left=_expected_space(prepared=prepared, created=fetched), right=fetched
    )
    if fetched.get("uiType") != prepared.template.get("uiType"):
        rows.append(
            DiffRow(
                section="space",
                path="uiType",
                left=prepared.template.get("uiType"),
                right=fetched.get("uiType"),
            )
        )
    rows.extend(_mcp_mismatches(prepared=prepared, fetched=fetched))
    return rows


def _mcp_mismatches(*, prepared: PreparedClone, fetched: JsonObject) -> list[DiffRow]:
    wanted: dict[str, JsonValue] = {
        k: list[JsonValue](sorted(v)) for k, v in prepared.built.selection.items()
    }
    actual: dict[str, JsonValue] = {}
    attachments = fetched.get("assistantMcpServers")
    for attachment in attachments if isinstance(attachments, list) else []:
        if not isinstance(attachment, dict):
            continue
        tools = attachment.get("tools")
        names: list[JsonValue] = list[JsonValue](
            sorted(
                str(t.get("name"))
                for t in (tools if isinstance(tools, list) else [])
                if isinstance(t, dict) and t.get("isEnabled") is True
            )
        )
        enabled = attachment.get("isEnabled") is True
        actual[str(attachment.get("mcpServerId"))] = names if enabled else []
    return [
        DiffRow(
            section="mcp",
            path=server_id,
            left=wanted.get(server_id, []),
            right=actual.get(server_id, []),
        )
        for server_id in sorted(wanted.keys() | actual.keys())
        if wanted.get(server_id, []) != actual.get(server_id, [])
    ]


def _refuse_duplicate_name(*, api: SpaceApi, spec: SpaceSpec) -> None:
    if spec.allow_duplicate_name:
        return
    existing = api.find_spaces_by_name(name=spec.name)
    if existing:
        ids = ", ".join(str(space.get("id")) for space in existing)
        msg = (
            f"a space named {spec.name!r} already exists on {spec.env} "
            f"({ids}); pick another name or pass --allow-duplicate-name"
        )
        raise SpaceKitError(msg)


def _register(
    *,
    workspace: Workspace,
    prepared: PreparedClone,
    space_id: str,
    log: Callable[[str], None],
) -> tuple[str, int | None]:
    request = prepared.spec.registration
    if request is None or prepared.registry_entry is None:
        return "", None
    home = workspace.harness_eval_home()
    entry = prepared.registry_entry.model_copy(update={"assistant_id": space_id})
    text = render_entry(
        profile=request.profile,
        entry=entry,
        template_id=prepared.spec.template,
        today=date.today(),
    )
    path = append_entry(
        harness_eval_home=home,
        text=text,
        validator=harness_eval_validator(harness_eval_home=home),
    )
    log(f"registered {request.profile} in {path}")
    if not request.run_doctor:
        return request.profile, None
    env_file = workspace.env_file(target=prepared.spec.env, explicit=None)
    code = run_doctor(
        harness_eval_home=home, env_file=env_file, profile=request.profile
    )
    return request.profile, code


def execute_clone(
    *,
    workspace: Workspace,
    prepared: PreparedClone,
    log: Callable[[str], None],
) -> CloneResult:
    spec = prepared.spec
    api = workspace.api(target=spec.env)
    _refuse_duplicate_name(api=api, spec=spec)
    created = api.create_space(payload=prepared.built.payload)
    space_id = str(created.get("id") or "")
    if not space_id:
        msg = "the API created a space but returned no id"
        raise SpaceKitError(msg)
    workspace.ledger.append(
        entry=LedgerEntry(
            at=now(),
            action=LedgerAction.CREATED,
            target=spec.env.value,
            space_id=space_id,
            name=spec.name,
            template_id=spec.template,
            source_target=spec.from_env.value if spec.from_env else "",
            changed_paths=prepared.built.changed_paths,
            registered_profile=spec.registration.profile if spec.registration else "",
        )
    )
    log(f"created {space_id} on {spec.env}")
    if spec.access:
        grants: list[JsonValue] = [
            grant.model_dump(mode="json") for grant in spec.access
        ]
        _ = api.add_access(space_id=space_id, access=grants)
        log(f"granted {len(spec.access)} access entr(y/ies)")
    fetched = api.get_space(space_id=space_id)
    verification = verify_created(prepared=prepared, fetched=fetched)
    profile, doctor_code = _register(
        workspace=workspace, prepared=prepared, space_id=space_id, log=log
    )
    return CloneResult(
        space_id=space_id,
        verification=tuple(verification),
        registered_profile=profile,
        doctor_exit_code=doctor_code,
    )


class PreparedEdit(KitModel):
    target: Target
    space: JsonObject
    built: BuiltPayload
    registered_as: str | None = None


def prepare_edit(
    *,
    workspace: Workspace,
    target: Target,
    space_id: str,
    spec: SpaceSpec,
    base_dir: Path,
) -> PreparedEdit:
    api = workspace.api(target=target)
    space = api.get_space(space_id=space_id)
    catalog = McpCatalog.from_api(rows=api.list_mcp_servers())
    context = McpContext(catalog=catalog, space_id=space_id)
    built = build_update_payload(
        space=space,
        plan=clone_plan(spec=spec, base_dir=base_dir),
        context=context,
    )
    registered_as = None
    try:
        spaces = read_spaces(harness_eval_home=workspace.harness_eval_home())
        registered_as = next(
            (n for n, e in spaces.items() if e.get("assistant_id") == space_id),
            None,
        )
    except SpaceKitError:
        registered_as = None
    return PreparedEdit(
        target=target, space=space, built=built, registered_as=registered_as
    )


def execute_edit(
    *, workspace: Workspace, prepared: PreparedEdit, space_id: str
) -> list[DiffRow]:
    api = workspace.api(target=prepared.target)
    _ = api.update_space(space_id=space_id, payload=prepared.built.payload)
    workspace.ledger.append(
        entry=LedgerEntry(
            at=now(),
            action=LedgerAction.EDITED,
            target=prepared.target.value,
            space_id=space_id,
            name=str(prepared.space.get("name") or ""),
            changed_paths=prepared.built.changed_paths,
        )
    )
    return diff_spaces(left=prepared.space, right=api.get_space(space_id=space_id))


def delete_space(
    *,
    workspace: Workspace,
    target: Target,
    space_id: str,
    force_unlisted: bool,
) -> str:
    if not force_unlisted and space_id not in workspace.ledger.live_space_ids(
        target=target.value
    ):
        msg = (
            f"{space_id} was not created by space-kit on {target} (see "
            "`ledger`); pass --force-unlisted to delete it anyway"
        )
        raise SpaceKitError(msg)
    api = workspace.api(target=target)
    name = str(api.get_space(space_id=space_id).get("name") or "")
    api.delete_space(space_id=space_id)
    workspace.ledger.append(
        entry=LedgerEntry(
            at=now(),
            action=LedgerAction.DELETED,
            target=target.value,
            space_id=space_id,
            name=name,
        )
    )
    return name
