"""Registry entries checked by harness-eval's own loader, on a copy."""

import shutil
from datetime import date
from pathlib import Path

import pytest
import yaml

from space_kit.base import SpaceKitError
from space_kit.payload import module_configuration
from space_kit.register import (
    RegisterRequest,
    append_entry,
    build_entry,
    harness_eval_validator,
    render_entry,
)
from tests.support.fake_api import conduct_template

pytestmark = pytest.mark.ai

HARNESS_EVAL = Path(__file__).resolve().parents[2] / "harness-eval"


@pytest.fixture
def copied_home(tmp_path: Path) -> Path:
    if not (HARNESS_EVAL / "spaces.yaml").is_file():
        pytest.skip("harness-eval is not next to space-kit")
    home = tmp_path / "harness-eval"
    home.mkdir()
    (home / "harness_eval").symlink_to(HARNESS_EVAL / "harness_eval")
    (home / "profiles").symlink_to(HARNESS_EVAL / "profiles")
    _ = shutil.copy(HARNESS_EVAL / "spaces.yaml", home / "spaces.yaml")
    return home


def _claude_parent(home: Path) -> str:
    spaces = yaml.safe_load((home / "spaces.yaml").read_text("utf-8"))
    for name, entry in spaces["spaces"].items():
        if entry.get("harness") == "claude_code" and not entry.get("historical"):
            return name
    pytest.skip("no current claude_code space in spaces.yaml")


def _entry_text(*, home: Path, tool_profile: str | None) -> str:
    parent = _claude_parent(home)
    spaces = yaml.safe_load((home / "spaces.yaml").read_text("utf-8"))
    entry = build_entry(
        request=RegisterRequest(
            profile="space-kit-contract-probe",
            derived_from=parent,
            changed_key="claude.effort",
            tool_profile=tool_profile,
        ),
        spaces=spaces["spaces"],
        template_id=spaces["spaces"][parent]["assistant_id"],
        target="qa",
        configuration=module_configuration(space=conduct_template()),
        changed_paths=("claude.effort",),
    ).model_copy(update={"assistant_id": "assistant_spacekitprobe0001"})
    return render_entry(
        profile="space-kit-contract-probe",
        entry=entry,
        template_id=spaces["spaces"][parent]["assistant_id"],
        today=date(2026, 10, 22),
    )


def test_harness_eval_accepts_an_appended_entry(copied_home: Path) -> None:
    text = _entry_text(home=copied_home, tool_profile=None)

    path = append_entry(
        harness_eval_home=copied_home,
        text=text,
        validator=harness_eval_validator(harness_eval_home=copied_home),
    )

    spaces = yaml.safe_load(path.read_text("utf-8"))["spaces"]
    assert spaces["space-kit-contract-probe"]["assistant_id"] == (
        "assistant_spacekitprobe0001"
    )


def test_harness_eval_rejects_an_unknown_tool_profile(
    copied_home: Path,
) -> None:
    before = (copied_home / "spaces.yaml").read_text("utf-8")
    text = _entry_text(home=copied_home, tool_profile="eval_tools_v999")

    with pytest.raises(SpaceKitError, match="unknown tool_profile"):
        _ = append_entry(
            harness_eval_home=copied_home,
            text=text,
            validator=harness_eval_validator(harness_eval_home=copied_home),
        )

    assert (copied_home / "spaces.yaml").read_text("utf-8") == before


def test_the_real_spaces_file_is_never_touched(copied_home: Path) -> None:
    real = HARNESS_EVAL / "spaces.yaml"
    before = real.read_bytes()

    _ = append_entry(
        harness_eval_home=copied_home,
        text=_entry_text(home=copied_home, tool_profile=None),
        validator=harness_eval_validator(harness_eval_home=copied_home),
    )

    assert real.read_bytes() == before
