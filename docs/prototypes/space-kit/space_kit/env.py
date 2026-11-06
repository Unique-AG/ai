from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import Field

from space_kit.base import KitModel, SpaceKitError

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
QA_LABEL = "qa"
QA_DOMAIN = "example.com"
ENV_FILE_VARIABLE = "SPACE_KIT_ENV_FILE_{target}"
HOME_VARIABLE = "SPACE_KIT_HOME"
HARNESS_EVAL_HOME_VARIABLE = "SPACE_KIT_HARNESS_EVAL_HOME"
ENVS_FILE_NAME = "envs.yaml"

KEY_ALIASES: Mapping[str, tuple[str, ...]] = {
    "api_base": ("UNIQUE_API_BASE_URL", "UNIQUE_API_BASE"),
    "api_key": ("UNIQUE_APP_KEY", "UNIQUE_API_KEY"),
    "app_id": ("UNIQUE_APP_ID",),
    "user_id": ("UNIQUE_AUTH_USER_ID", "UNIQUE_USER_ID"),
    "company_id": ("UNIQUE_AUTH_COMPANY_ID", "UNIQUE_COMPANY_ID"),
}
OPTIONAL_ON_LOCAL = frozenset({"api_key", "app_id"})


class Target(StrEnum):
    LOCAL = "local"
    QA = "qa"


class Credentials(KitModel):
    target: Target
    env_file: Path
    api_base: str
    api_key: str
    app_id: str
    user_id: str
    company_id: str

    def __repr__(self) -> str:
        return f"Credentials(target={self.target}, env_file={self.env_file})"

    __str__ = __repr__


class KitConfig(KitModel):
    env_files: dict[Target, Path] = Field(default_factory=dict)
    harness_eval_home: Path | None = None


def kit_home(*, environ: Mapping[str, str]) -> Path:
    configured = environ.get(HOME_VARIABLE)
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent


def load_kit_config(*, home: Path) -> KitConfig:
    path = home / ENVS_FILE_NAME
    if not path.exists():
        return KitConfig()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return KitConfig.model_validate(payload)
    except ValueError as exc:
        msg = f"{path} is invalid: {exc}"
        raise SpaceKitError(msg) from exc


def target_for_api_base(*, api_base: str) -> Target:
    host = (urlparse(api_base).hostname or "").lower()
    if host in LOCAL_HOSTS:
        return Target.LOCAL
    labels = host.split(".")
    if host.endswith(f".{QA_DOMAIN}") and QA_LABEL in labels:
        return Target.QA
    msg = (
        f"refusing API host {host!r}: space-kit only writes to localhost "
        f"or a '{QA_LABEL}' host under {QA_DOMAIN}"
    )
    raise SpaceKitError(msg)


def resolve_env_file(
    *,
    target: Target,
    explicit: Path | None,
    environ: Mapping[str, str],
    config: KitConfig,
) -> Path:
    if explicit is not None:
        return explicit
    variable = ENV_FILE_VARIABLE.format(target=target.value.upper())
    from_environ = environ.get(variable)
    if from_environ:
        return Path(from_environ)
    configured = config.env_files.get(target)
    if configured is not None:
        return configured
    msg = (
        f"no env file for target {target}: pass --env-file, set {variable}, "
        f"or add env_files.{target} to {ENVS_FILE_NAME}"
    )
    raise SpaceKitError(msg)


def parse_env_file(*, path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        msg = f"cannot read env file {path}: {exc.strerror}"
        raise SpaceKitError(msg) from exc
    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        values[key] = value.strip().strip('"').strip("'")
    return values


def _pick(*, values: Mapping[str, str], field: str) -> str:
    for key in KEY_ALIASES[field]:
        found = values.get(key, "")
        if found:
            return found
    return ""


def load_credentials(*, target: Target, env_file: Path) -> Credentials:
    values = parse_env_file(path=env_file)
    picked = {field: _pick(values=values, field=field) for field in KEY_ALIASES}
    if picked["api_base"]:
        actual = target_for_api_base(api_base=picked["api_base"])
        if actual is not target:
            msg = (
                f"{env_file} points at target {actual}, but the command "
                f"asked for {target}"
            )
            raise SpaceKitError(msg)
    missing = [
        " or ".join(KEY_ALIASES[field])
        for field, value in picked.items()
        if not value and not (target is Target.LOCAL and field in OPTIONAL_ON_LOCAL)
    ]
    if missing:
        msg = f"{env_file} lacks: {', '.join(missing)}"
        raise SpaceKitError(msg)
    return Credentials(target=target, env_file=env_file, **picked)
