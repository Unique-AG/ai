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
    harness_facts,
    render_entry,
    suggest_changed_key,
)
from tests.support.fake_api import conduct_template

pytestmark = pytest.mark.ai

SPACES = {
    "base-space": {
        "assistant_id": "assistant_template",
        "target": "qa",
        "harness": "claude_code",
        "tags": ["code_execution", "memory_off"],
        "comparable_group": "perf-s55",
        "tool_profile": "eval_tools_v2",
    }
}


def test_harness_facts_read_model_and_effort_per_strategy() -> None:
    configuration = module_configuration(space=conduct_template())

    claude = harness_facts(configuration=configuration)
    codex = harness_facts(configuration={**configuration, "strategy": "codex"})
    pi = harness_facts(configuration={**configuration, "strategy": "pi_agent"})

    assert (claude.model, claude.thinking) == (
        "anthropic-claude-sonnet-5-5",
        "auto",
    )
    assert (codex.model, codex.thinking) == (
        "AZURE_GPT_56_SOL_2026_0709",
        "medium",
    )
    assert pi.thinking == "high"


def test_suggest_changed_key_ignores_the_project_name() -> None:
    assert (
        suggest_changed_key(changed_paths=("claude.effort", "space.projectName"))
        == "claude.effort"
    )
    assert (
        suggest_changed_key(changed_paths=("tools[a].isEnabled", "tools[b].isEnabled"))
        == "tools"
    )
    assert suggest_changed_key(changed_paths=("a.b", "c.d")) is None


def test_build_entry_inherits_from_the_template_profile() -> None:
    entry = build_entry(
        request=RegisterRequest(profile="variant-low"),
        spaces=SPACES,
        template_id="assistant_template",
        target="qa",
        configuration=module_configuration(space=conduct_template()),
        changed_paths=("claude.effort", "space.projectName"),
    )

    assert entry.derived_from == "base-space"
    assert entry.changed_key == "claude.effort"
    assert entry.tool_profile == "eval_tools_v2"
    assert entry.tags == ("code_execution", "memory_off")
    assert entry.comparable_group == "perf-s55"


def test_build_entry_needs_a_changed_key_when_several_paths_changed() -> None:
    with pytest.raises(SpaceKitError, match="Pass --changed-key"):
        _ = build_entry(
            request=RegisterRequest(profile="x"),
            spaces=SPACES,
            template_id="assistant_template",
            target="qa",
            configuration={},
            changed_paths=("a.b", "c.d"),
        )


def test_build_entry_refuses_an_existing_profile_name() -> None:
    with pytest.raises(SpaceKitError, match="already exists"):
        _ = build_entry(
            request=RegisterRequest(profile="base-space"),
            spaces=SPACES,
            template_id="assistant_template",
            target="qa",
            configuration={},
            changed_paths=(),
        )


def test_render_entry_appends_as_valid_yaml_under_spaces(
    tmp_path: Path,
) -> None:
    entry = build_entry(
        request=RegisterRequest(profile="variant-low", note="Effort low."),
        spaces=SPACES,
        template_id="assistant_template",
        target="qa",
        configuration=module_configuration(space=conduct_template()),
        changed_paths=("claude.effort",),
    ).model_copy(update={"assistant_id": "assistant_new"})
    home = tmp_path
    _ = (home / "spaces.yaml").write_text(
        "# header comment\nspaces:\n  base-space:\n"
        "    assistant_id: assistant_template\n    harness: claude_code\n",
        encoding="utf-8",
    )
    text = render_entry(
        profile="variant-low",
        entry=entry,
        template_id="assistant_template",
        today=date(2026, 10, 22),
    )

    path = append_entry(harness_eval_home=home, text=text, validator=lambda _: None)

    content = path.read_text(encoding="utf-8")
    document = yaml.safe_load(content)
    assert content.startswith("# header comment")
    assert document["spaces"]["variant-low"]["assistant_id"] == "assistant_new"
    assert document["spaces"]["variant-low"]["changed_key"] == "claude.effort"
    assert set(document["spaces"]) == {"base-space", "variant-low"}


def test_append_entry_leaves_the_file_untouched_when_validation_fails(
    tmp_path: Path,
) -> None:
    original = "spaces: {}\n"
    _ = (tmp_path / "spaces.yaml").write_text(original, encoding="utf-8")

    def reject(_: Path) -> None:
        raise SpaceKitError("rejected")

    with pytest.raises(SpaceKitError, match="rejected"):
        _ = append_entry(harness_eval_home=tmp_path, text="  x: {}\n", validator=reject)

    assert (tmp_path / "spaces.yaml").read_text(encoding="utf-8") == original
    assert list(tmp_path.iterdir()) == [tmp_path / "spaces.yaml"]
