"""Optional, additive registration of a new space in harness-eval.

space-kit never imports harness_eval. It appends one entry to its
`spaces.yaml`, validates the result with harness-eval's own loader in a
subprocess before replacing the file, and can run `doctor --live`.
"""

import os
import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import yaml

from space_kit.base import JsonObject, KitModel, SpaceKitError
from space_kit.paths import get_path

SPACES_FILE = "spaces.yaml"
PROJECT_NAME_PATH = "space.projectName"
TOOLS_KEY = "tools"
VALIDATE_SNIPPET = """
import sys
from pathlib import Path
from harness_eval.profiles.loader import load_spaces, load_tool_profiles
spaces = load_spaces(path=Path(sys.argv[1]))
known = load_tool_profiles(directory=Path("profiles"))
bad = sorted(n for n, s in spaces.items() if s.tool_profile not in known)
if bad:
    raise SystemExit(f"unknown tool_profile for: {bad}")
"""

HARNESS_KEYS: dict[str, tuple[str, str | None]] = {
    "claude_code": ("claude.model", "claude.effort"),
    "codex": ("codex.model", "codex.modelReasoningEffort"),
    "pi_agent": ("piAgent.modelName", "piAgent.thinkingLevel"),
    "cursor_sdk": ("cursorSdk.model", None),
}
STRATEGY_PATH = "strategy"
UNKNOWN = "unknown"


class HarnessFacts(KitModel):
    harness: str
    model: str
    thinking: str


class RegisterRequest(KitModel):
    profile: str
    derived_from: str | None = None
    changed_key: str | None = None
    comparable_group: str | None = None
    tool_profile: str | None = None
    tags: tuple[str, ...] | None = None
    note: str = ""
    run_doctor: bool = False


class RegistryEntry(KitModel):
    assistant_id: str
    target: str
    harness: str
    model: str
    thinking: str
    tags: tuple[str, ...] = ()
    comparable_group: str = ""
    tool_profile: str | None = None
    derived_from: str | None = None
    changed_key: str | None = None
    note: str = ""


def _text_at(*, configuration: JsonObject, path: str | None) -> str:
    if path is None:
        return UNKNOWN
    try:
        value = get_path(data=configuration, path=path)
    except SpaceKitError:
        return UNKNOWN
    return value if isinstance(value, str) and value else UNKNOWN


def harness_facts(*, configuration: JsonObject) -> HarnessFacts:
    harness = _text_at(configuration=configuration, path=STRATEGY_PATH)
    model_path, thinking_path = HARNESS_KEYS.get(harness, (None, None))
    return HarnessFacts(
        harness=harness if harness in HARNESS_KEYS else UNKNOWN,
        model=_text_at(configuration=configuration, path=model_path),
        thinking=_text_at(configuration=configuration, path=thinking_path),
    )


def read_spaces(*, harness_eval_home: Path) -> dict[str, JsonObject]:
    path = harness_eval_home / SPACES_FILE
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        msg = f"cannot read {path}: {exc}"
        raise SpaceKitError(msg) from exc
    spaces = document.get("spaces") if isinstance(document, dict) else None
    if not isinstance(spaces, dict):
        msg = f"{path} has no `spaces` mapping"
        raise SpaceKitError(msg)
    return {str(k): v for k, v in spaces.items() if isinstance(v, dict)}


def profile_for_assistant(
    *, spaces: dict[str, JsonObject], assistant_id: str
) -> str | None:
    return next(
        (n for n, e in spaces.items() if e.get("assistant_id") == assistant_id),
        None,
    )


def suggest_changed_key(*, changed_paths: tuple[str, ...]) -> str | None:
    meaningful = [p for p in changed_paths if p != PROJECT_NAME_PATH]
    if meaningful and all(p.startswith(f"{TOOLS_KEY}[") for p in meaningful):
        return TOOLS_KEY
    if len(meaningful) == 1:
        return meaningful[0]
    return None


def _template_profile(
    *,
    request: RegisterRequest,
    spaces: dict[str, JsonObject],
    template_id: str,
) -> str | None:
    if request.derived_from is None:
        return profile_for_assistant(spaces=spaces, assistant_id=template_id)
    if request.derived_from not in spaces:
        msg = f"--derived-from {request.derived_from!r} is not in spaces.yaml"
        raise SpaceKitError(msg)
    return request.derived_from


def _inherited_list(*, entry: JsonObject, key: str) -> tuple[str, ...]:
    value = entry.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _inherited_text(*, entry: JsonObject, key: str) -> str | None:
    value = entry.get(key)
    return value if isinstance(value, str) else None


def check_request(*, request: RegisterRequest, spaces: dict[str, JsonObject]) -> None:
    if request.profile in spaces:
        msg = f"profile {request.profile!r} already exists in spaces.yaml"
        raise SpaceKitError(msg)


def _changed_key(
    *,
    request: RegisterRequest,
    derived_from: str | None,
    paths: tuple[str, ...],
) -> str | None:
    if derived_from is None:
        return None
    key = request.changed_key or suggest_changed_key(changed_paths=paths)
    if key is None:
        msg = (
            f"cannot pick one changed_key for a space derived from "
            f"{derived_from!r}; changed paths: {list(paths) or 'none'}. "
            "Pass --changed-key."
        )
        raise SpaceKitError(msg)
    return key


def build_entry(
    *,
    request: RegisterRequest,
    spaces: dict[str, JsonObject],
    template_id: str,
    target: str,
    configuration: JsonObject,
    changed_paths: tuple[str, ...],
) -> RegistryEntry:
    check_request(request=request, spaces=spaces)
    derived_from = _template_profile(
        request=request, spaces=spaces, template_id=template_id
    )
    parent = spaces.get(derived_from or "", {})
    facts = harness_facts(configuration=configuration)
    tags = request.tags
    if tags is None:
        tags = _inherited_list(entry=parent, key="tags")
    group = request.comparable_group
    if group is None:
        group = _inherited_text(entry=parent, key="comparable_group") or ""
    return RegistryEntry(
        assistant_id="assistant_pending",
        target=target,
        harness=facts.harness,
        model=facts.model,
        thinking=facts.thinking,
        tags=tags,
        comparable_group=group,
        tool_profile=request.tool_profile
        or _inherited_text(entry=parent, key="tool_profile"),
        derived_from=derived_from,
        changed_key=_changed_key(
            request=request, derived_from=derived_from, paths=changed_paths
        ),
        note=request.note,
    )


def render_entry(
    *, profile: str, entry: RegistryEntry, template_id: str, today: date
) -> str:
    body = entry.model_dump(exclude_none=True)
    body["tags"] = list(entry.tags)
    for key in ("comparable_group", "note"):
        if not body.get(key):
            body.pop(key, None)
    dumped = yaml.safe_dump(
        {profile: body}, sort_keys=False, allow_unicode=True, width=78
    )
    indented = "".join(f"  {line}\n" for line in dumped.splitlines())
    header = (
        f"  # space-kit {today.isoformat()}: created from {template_id} "
        "through the public API.\n"
    )
    return header + indented


type Validator = Callable[[Path], None]


def harness_eval_validator(*, harness_eval_home: Path) -> Validator:
    def validate(candidate: Path) -> None:
        completed = subprocess.run(
            [sys.executable, "-c", VALIDATE_SNIPPET, str(candidate)],
            cwd=harness_eval_home,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout).strip()[-800:]
            msg = f"harness-eval rejected the new spaces.yaml: {tail}"
            raise SpaceKitError(msg)

    return validate


def append_entry(*, harness_eval_home: Path, text: str, validator: Validator) -> Path:
    path = harness_eval_home / SPACES_FILE
    original = path.read_text(encoding="utf-8")
    candidate = path.with_name(f".{SPACES_FILE}.space-kit-candidate")
    _ = candidate.write_text(original.rstrip("\n") + "\n\n" + text, encoding="utf-8")
    try:
        validator(candidate)
    except SpaceKitError:
        candidate.unlink(missing_ok=True)
        raise
    os.replace(candidate, path)
    return path


def run_doctor(*, harness_eval_home: Path, env_file: Path, profile: str) -> int:
    environ = {**os.environ, "HARNESS_EVAL_ENV_FILE": str(env_file)}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness_eval",
            "doctor",
            "--live",
            "--profiles",
            profile,
        ],
        cwd=harness_eval_home,
        env=environ,
        check=False,
    )
    return completed.returncode
