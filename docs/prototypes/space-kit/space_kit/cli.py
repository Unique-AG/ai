import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from space_kit import __version__
from space_kit.api import Transport, UrllibTransport
from space_kit.base import JsonObject, JsonValue, SpaceKitError
from space_kit.diff import diff_spaces, render_rows, short, space_view
from space_kit.env import ENV_FILE_VARIABLE, Target, kit_home, load_kit_config
from space_kit.mcp import McpCatalog, describe_selection, parse_change
from space_kit.paths import flatten, parse_assignment
from space_kit.payload import module_configuration
from space_kit.register import harness_facts
from space_kit.spec import SpaceSpec, load_spec, parse_grant
from space_kit.workflow import (
    PreparedClone,
    Workspace,
    delete_space,
    execute_clone,
    execute_edit,
    prepare_clone,
    prepare_edit,
)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_UNVERIFIED = 2

type Printer = Callable[[str], None]


def _env_arguments(*, parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env", required=True, choices=[t.value for t in Target])
    parser.add_argument("--env-file", type=Path, help="override the env file for --env")


def _plan_arguments(*, parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="PATH=VALUE",
        help="module config, e.g. claude.effort=low or "
        "setup.agentMdInstructions=@file:prompt.md",
    )
    parser.add_argument("--setting", action="append", default=[], metavar="PATH=VALUE")
    parser.add_argument(
        "--space-field",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="alert, chatUpload, languageModel, assistantPrompts, ...",
    )
    parser.add_argument("--explanation")
    parser.add_argument(
        "--mcp",
        action="append",
        default=[],
        metavar="SERVER=all|none|t1,t2",
        help="server name or id; changes the template selection",
    )
    parser.add_argument(
        "--mcp-replace",
        action="store_true",
        help="start from no MCP servers instead of the template's",
    )
    parser.add_argument("--skip-restricted", action="store_true")
    parser.add_argument("--allow-new-keys", action="store_true")
    parser.add_argument("--yes", action="store_true", help="perform the write")


def _register_arguments(*, parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("harness-eval registration (opt-in)")
    group.add_argument("--register", metavar="PROFILE")
    group.add_argument("--derived-from")
    group.add_argument("--changed-key")
    group.add_argument("--comparable-group")
    group.add_argument("--tool-profile")
    group.add_argument("--tag", action="append")
    group.add_argument("--note", default="")
    group.add_argument("--doctor", action="store_true", help="run doctor --live after")


def _clone_parser(
    *,
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",  # pyright: ignore[reportPrivateUsage] -- argparse has no public type for it
) -> None:
    clone = commands.add_parser(
        "clone", help="create a space from a template space (dry run first)"
    )
    clone.add_argument("template", help="template space id")
    clone.add_argument("--name", required=True)
    _env_arguments(parser=clone)
    clone.add_argument("--from-env", choices=[t.value for t in Target])
    clone.add_argument(
        "--mcp-map", action="append", default=[], metavar="SOURCE_ID=TARGET_ID"
    )
    clone.add_argument("--drop-unmapped-mcp", action="store_true")
    clone.add_argument("--keep-project-name", action="store_true")
    clone.add_argument("--allow-duplicate-name", action="store_true")
    clone.add_argument(
        "--grant",
        action="append",
        default=[],
        metavar="USER|GROUP:ID:USE|MANAGE|UPLOAD",
    )
    _plan_arguments(parser=clone)
    _register_arguments(parser=clone)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="space-kit")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("envs", help="show configured env files (no values)")

    mcp = commands.add_parser("mcp", help="list MCP servers on a target")
    _env_arguments(parser=mcp)
    mcp.add_argument("--name", help="case-insensitive substring filter")
    mcp.add_argument("--tools", action="store_true", help="list tool names")
    mcp.add_argument("--json", action="store_true")

    show = commands.add_parser("show", help="flattened view of a space")
    show.add_argument("space_id")
    _env_arguments(parser=show)
    show.add_argument("--prefix", default="", help="only config paths with it")
    show.add_argument("--json", action="store_true", help="raw GET body")

    diff = commands.add_parser("diff", help="compare two spaces")
    diff.add_argument("left")
    diff.add_argument("right")
    _env_arguments(parser=diff)
    diff.add_argument("--env-right", choices=[t.value for t in Target])

    _clone_parser(commands=commands)

    apply = commands.add_parser("apply", help="clone from a YAML spec")
    apply.add_argument("spec", type=Path)
    apply.add_argument("--yes", action="store_true")

    edit = commands.add_parser("edit", help="read-modify-write an existing space")
    edit.add_argument("space_id")
    _env_arguments(parser=edit)
    _plan_arguments(parser=edit)

    grant = commands.add_parser("grant", help="add access entries")
    grant.add_argument("space_id")
    _env_arguments(parser=grant)
    grant.add_argument("--grant", action="append", required=True)
    grant.add_argument("--yes", action="store_true")

    delete = commands.add_parser("delete", help="delete a space")
    delete.add_argument("space_id")
    _env_arguments(parser=delete)
    delete.add_argument("--force-unlisted", action="store_true")
    delete.add_argument("--yes", action="store_true")

    ledger = commands.add_parser("ledger", help="what this machine created")
    ledger.add_argument("--env", choices=[t.value for t in Target])
    return parser


def _assignment_map(*, items: Sequence[str], base_dir: Path) -> dict[str, JsonValue]:
    parsed = [parse_assignment(text=item, base_dir=base_dir) for item in items]
    return {a.path: a.value for a in parsed}


def _mcp_spec(*, args: argparse.Namespace) -> JsonObject:
    servers: JsonObject = {}
    for text in args.mcp:
        change = parse_change(text=text)
        servers[change.server] = (
            change.tools if isinstance(change.tools, str) else list(change.tools)
        )
    mapping = _assignment_map(items=getattr(args, "mcp_map", []), base_dir=Path())
    return {
        "replace": args.mcp_replace,
        "servers": servers,
        "map": {k: str(v) for k, v in mapping.items()},
        "skip_restricted": args.skip_restricted,
        "drop_unmapped": getattr(args, "drop_unmapped_mcp", False),
    }


def _register_spec(*, args: argparse.Namespace) -> JsonObject | None:
    if not getattr(args, "register", None):
        return None
    return {
        "profile": args.register,
        "derived_from": args.derived_from,
        "changed_key": args.changed_key,
        "comparable_group": args.comparable_group,
        "tool_profile": args.tool_profile,
        "tags": args.tag,
        "note": args.note,
        "run_doctor": args.doctor,
    }


def spec_from_args(*, args: argparse.Namespace, name: str, template: str) -> SpaceSpec:
    base_dir = Path.cwd()
    payload: JsonObject = {
        "env": args.env,
        "name": name,
        "template": template,
        "from_env": getattr(args, "from_env", None),
        "explanation": args.explanation,
        "set": _assignment_map(items=args.set, base_dir=base_dir),
        "settings": _assignment_map(items=args.setting, base_dir=base_dir),
        "space": _assignment_map(items=args.space_field, base_dir=base_dir),
        "mcp": _mcp_spec(args=args),
        "access": [
            parse_grant(text=g).model_dump(mode="json")
            for g in getattr(args, "grant", [])
        ],
        "register": _register_spec(args=args),
        "allow_new_keys": args.allow_new_keys,
        "keep_project_name": getattr(args, "keep_project_name", False),
        "allow_duplicate_name": getattr(args, "allow_duplicate_name", False),
    }
    return SpaceSpec.model_validate(payload)


def _print_changes(
    *,
    before: JsonObject,
    after: JsonObject,
    paths: Sequence[str],
    out: Printer,
) -> None:
    left = flatten(data=before)
    right = flatten(data=after)
    out(f"Changed config paths ({len(paths)}):")
    for path in paths:
        out(
            f"  {path}: {short(value=left.get(path), present=path in left)}"
            f" -> {short(value=right.get(path), present=path in right)}"
        )


def print_prepared(*, prepared: PreparedClone, out: Printer) -> None:
    template = prepared.template
    facts = harness_facts(configuration=prepared.built.configuration)
    out(
        f"Template: {template.get('id')} {template.get('name')!r} "
        f"({template.get('uiType')})"
    )
    out(
        f"New space: {prepared.spec.name!r} on {prepared.spec.env} - "
        f"{facts.harness} / {facts.model} / {facts.thinking}"
    )
    _print_changes(
        before=module_configuration(space=template),
        after=prepared.built.configuration,
        paths=prepared.built.changed_paths,
        out=out,
    )
    out("MCP selection:")
    for line in describe_selection(
        selection=prepared.built.selection, catalog=prepared.catalog
    ):
        out(f"  {line}")
    for warning in prepared.warnings:
        out(f"WARNING: {warning}")
    entry = prepared.registry_entry
    if entry is not None and prepared.spec.registration is not None:
        out(
            f"Will register {prepared.spec.registration.profile}: derived_from="
            f"{entry.derived_from} changed_key={entry.changed_key} "
            f"tool_profile={entry.tool_profile} group={entry.comparable_group}"
        )


def run_clone(
    *,
    workspace: Workspace,
    spec: SpaceSpec,
    base_dir: Path,
    yes: bool,
    out: Printer,
) -> int:
    prepared = prepare_clone(workspace=workspace, spec=spec, base_dir=base_dir)
    print_prepared(prepared=prepared, out=out)
    if not yes:
        path = workspace.ledger.write_dry_run(
            name=spec.name, payload=prepared.built.payload
        )
        out(f"Dry run. Payload: {path}. Re-run with --yes to create.")
        return EXIT_OK
    result = execute_clone(workspace=workspace, prepared=prepared, log=out)
    out("Verification (expected vs fetched):")
    for line in render_rows(rows=list(result.verification)):
        out(f"  {line}")
    if result.doctor_exit_code not in (None, 0):
        out(f"doctor --live exited with {result.doctor_exit_code}")
        return EXIT_UNVERIFIED
    return EXIT_UNVERIFIED if result.verification else EXIT_OK


def run_edit(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    target = Target(args.env)
    spec = spec_from_args(args=args, name="(edit)", template=args.space_id)
    prepared = prepare_edit(
        workspace=workspace,
        target=target,
        space_id=args.space_id,
        spec=spec,
        base_dir=Path.cwd(),
    )
    if prepared.registered_as:
        out(
            f"WARNING: {args.space_id} is harness-eval profile "
            f"{prepared.registered_as!r}; editing it changes its fingerprint. "
            "Prefer `clone` for a new variant."
        )
    _print_changes(
        before=module_configuration(space=prepared.space),
        after=prepared.built.configuration,
        paths=prepared.built.changed_paths,
        out=out,
    )
    for warning in prepared.built.warnings:
        out(f"WARNING: {warning}")
    if not args.yes:
        out("Dry run. Re-run with --yes to apply.")
        return EXIT_OK
    rows = execute_edit(workspace=workspace, prepared=prepared, space_id=args.space_id)
    out("Now differs from before:")
    for line in render_rows(rows=rows):
        out(f"  {line}")
    return EXIT_OK


def run_mcp(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    rows = workspace.api(target=Target(args.env)).list_mcp_servers()
    if args.name:
        rows = [r for r in rows if args.name.lower() in str(r.get("name", "")).lower()]
    if args.json:
        out(json.dumps(rows, indent=2))
        return EXIT_OK
    for server in McpCatalog.from_api(rows=rows).servers:
        flags = " restricted" if server.is_space_restricted else ""
        out(f"{server.id}  {server.name}  ({len(server.callable_tools)} tools){flags}")
        if args.tools:
            out(f"    {', '.join(sorted(server.callable_tools))}")
    return EXIT_OK


def run_show(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    space = workspace.api(target=Target(args.env)).get_space(space_id=args.space_id)
    if args.json:
        out(json.dumps(space, indent=2))
        return EXIT_OK
    facts = harness_facts(configuration=module_configuration(space=space))
    out(f"{space.get('id')} {space.get('name')!r} uiType={space.get('uiType')}")
    out(f"harness={facts.harness} model={facts.model} thinking={facts.thinking}")
    for section, values in space_view(space=space).items():
        for path, value in values.items():
            if section == "config" and not path.startswith(args.prefix):
                continue
            out(f"[{section}] {path} = {short(value=value)}")
    return EXIT_OK


def run_diff(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    left = workspace.api(target=Target(args.env)).get_space(space_id=args.left)
    right_target = Target(args.env_right or args.env)
    right = workspace.api(target=right_target).get_space(space_id=args.right)
    for line in render_rows(rows=diff_spaces(left=left, right=right)):
        out(line)
    return EXIT_OK


def run_grant(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    grants = [parse_grant(text=g) for g in args.grant]
    for grant in grants:
        out(f"grant {grant.entityType}:{grant.entityId}:{grant.type}")
    if not args.yes:
        out("Dry run. Re-run with --yes to grant.")
        return EXIT_OK
    access: list[JsonValue] = [g.model_dump(mode="json") for g in grants]
    _ = workspace.api(target=Target(args.env)).add_access(
        space_id=args.space_id, access=access
    )
    out("granted")
    return EXIT_OK


def run_delete(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    if not args.yes:
        out(f"Dry run. Re-run with --yes to delete {args.space_id}.")
        return EXIT_OK
    name = delete_space(
        workspace=workspace,
        target=Target(args.env),
        space_id=args.space_id,
        force_unlisted=args.force_unlisted,
    )
    out(f"deleted {args.space_id} {name!r}")
    return EXIT_OK


def run_ledger(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    for entry in workspace.ledger.entries():
        if args.env and entry.target != args.env:
            continue
        extra = (
            f" profile={entry.registered_profile}" if entry.registered_profile else ""
        )
        out(
            f"{entry.at:%Y-%m-%d %H:%M} {entry.action:<7} {entry.target:<5} "
            f"{entry.space_id} {entry.name!r}{extra}"
        )
    return EXIT_OK


def run_envs(*, workspace: Workspace, out: Printer) -> int:
    for target in Target:
        try:
            path = workspace.env_file(target=target, explicit=None)
            state = "exists" if path.exists() else "MISSING"
            out(f"{target}: {path} ({state})")
        except SpaceKitError as exc:
            out(f"{target}: {exc}")
    return EXIT_OK


def _environ_with_override(
    *, environ: Mapping[str, str], args: argparse.Namespace
) -> dict[str, str]:
    result = dict(environ)
    env_file = getattr(args, "env_file", None)
    if env_file is not None:
        variable = ENV_FILE_VARIABLE.format(target=str(args.env).upper())
        result[variable] = str(env_file)
    return result


def dispatch(*, workspace: Workspace, args: argparse.Namespace, out: Printer) -> int:
    simple = {
        "mcp": run_mcp,
        "show": run_show,
        "diff": run_diff,
        "edit": run_edit,
        "grant": run_grant,
        "delete": run_delete,
        "ledger": run_ledger,
    }
    if args.command in simple:
        return simple[args.command](workspace=workspace, args=args, out=out)
    if args.command == "envs":
        return run_envs(workspace=workspace, out=out)
    if args.command == "apply":
        spec = load_spec(path=args.spec)
        return run_clone(
            workspace=workspace,
            spec=spec,
            base_dir=args.spec.resolve().parent,
            yes=args.yes,
            out=out,
        )
    spec = spec_from_args(args=args, name=args.name, template=args.template)
    return run_clone(
        workspace=workspace,
        spec=spec,
        base_dir=Path.cwd(),
        yes=args.yes,
        out=out,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    transport: Transport | None = None,
    out: Printer = print,
) -> int:
    args = build_parser().parse_args(argv)
    source_environ = os.environ if environ is None else environ
    home = kit_home(environ=source_environ)
    try:
        workspace = Workspace(
            home=home,
            config=load_kit_config(home=home),
            environ=_environ_with_override(environ=source_environ, args=args),
            transport=transport or UrllibTransport(),
        )
        return dispatch(workspace=workspace, args=args, out=out)
    except SpaceKitError as exc:
        print(f"space-kit: {exc}", file=sys.stderr)
        return EXIT_ERROR
