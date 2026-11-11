"""Declarative recipe for one space (`apply spec.yaml`). CLI flags build
the same `SpaceSpec`, so both paths share one pipeline."""

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import ConfigDict, Field

from space_kit.base import JsonObject, JsonValue, KitModel, SpaceKitError
from space_kit.env import Target
from space_kit.mcp import ALL_TOOLS, NO_TOOLS, McpChange, McpPlan
from space_kit.paths import Assignment, resolve_value
from space_kit.payload import ClonePlan
from space_kit.register import RegisterRequest


class EntityType(StrEnum):
    USER = "USER"
    GROUP = "GROUP"


class AccessType(StrEnum):
    USE = "USE"
    MANAGE = "MANAGE"
    UPLOAD = "UPLOAD"


class AccessGrant(KitModel):
    entityId: str
    entityType: EntityType
    type: AccessType


class McpSpec(KitModel):
    replace: bool = False
    servers: dict[str, str | list[str]] = Field(default_factory=dict)
    map: dict[str, str] = Field(default_factory=dict)
    skip_restricted: bool = False
    drop_unmapped: bool = False


class SpaceSpec(KitModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    env: Target
    name: str
    template: str
    from_env: Target | None = None
    explanation: str | None = None
    assignments: dict[str, JsonValue] = Field(default_factory=dict, alias="set")
    settings: dict[str, JsonValue] = Field(default_factory=dict)
    space: JsonObject = Field(default_factory=dict)
    mcp: McpSpec = McpSpec()
    access: tuple[AccessGrant, ...] = ()
    registration: RegisterRequest | None = Field(default=None, alias="register")
    allow_new_keys: bool = False
    keep_project_name: bool = False
    allow_duplicate_name: bool = False


def parse_grant(*, text: str) -> AccessGrant:
    parts = text.split(":")
    if len(parts) != 3:
        msg = f"expected USER|GROUP:<id>:USE|MANAGE|UPLOAD, got {text!r}"
        raise SpaceKitError(msg)
    entity_type, entity_id, access_type = parts
    try:
        return AccessGrant(
            entityId=entity_id,
            entityType=EntityType(entity_type.upper()),
            type=AccessType(access_type.upper()),
        )
    except ValueError as exc:
        msg = f"invalid grant {text!r}: {exc}"
        raise SpaceKitError(msg) from exc


def _change(*, server: str, tools: str | list[str]) -> McpChange:
    if isinstance(tools, str):
        if tools not in {ALL_TOOLS, NO_TOOLS}:
            msg = f"mcp server {server!r}: use all, none or a list of tools"
            raise SpaceKitError(msg)
        return McpChange(server=server, tools=tools)
    return McpChange(server=server, tools=tuple(tools))


def mcp_plan(*, spec: McpSpec) -> McpPlan:
    return McpPlan(
        replace=spec.replace,
        changes=tuple(
            _change(server=server, tools=tools)
            for server, tools in spec.servers.items()
        ),
        id_map=dict(spec.map),
        skip_restricted=spec.skip_restricted,
        drop_unmapped=spec.drop_unmapped,
    )


def _assignments(
    *, values: dict[str, JsonValue], base_dir: Path
) -> tuple[Assignment, ...]:
    return tuple(
        Assignment(path=path, value=resolve_value(value=value, base_dir=base_dir))
        for path, value in values.items()
    )


def clone_plan(*, spec: SpaceSpec, base_dir: Path) -> ClonePlan:
    return ClonePlan(
        name=spec.name,
        template_id=spec.template,
        explanation=spec.explanation,
        assignments=_assignments(values=spec.assignments, base_dir=base_dir),
        settings=_assignments(values=spec.settings, base_dir=base_dir),
        space_fields=spec.space,
        mcp=mcp_plan(spec=spec.mcp),
        allow_new_keys=spec.allow_new_keys,
        keep_project_name=spec.keep_project_name,
    )


def load_spec(*, path: Path) -> SpaceSpec:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        msg = f"cannot read spec {path}: {exc}"
        raise SpaceKitError(msg) from exc
    try:
        return SpaceSpec.model_validate(payload)
    except ValueError as exc:
        msg = f"spec {path} is invalid: {exc}"
        raise SpaceKitError(msg) from exc
