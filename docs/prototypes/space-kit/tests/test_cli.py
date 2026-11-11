import json
import sys
from pathlib import Path

import pytest

from space_kit.ledger import Ledger
from space_kit.paths import get_path
from tests.conftest import RunCli
from tests.support.fake_api import FakeSpaceServer

pytestmark = pytest.mark.ai

CLONE = ("clone", "assistant_template", "--env", "qa", "--name", "variant-low")


def test_clone_without_yes_writes_nothing_to_the_api(
    run_cli: RunCli, server: FakeSpaceServer, kit_home: Path
) -> None:
    code, lines = run_cli(*CLONE, "--set", "claude.effort=low")

    assert code == 0
    assert server.writes() == []
    assert any("claude.effort: auto -> low" in line for line in lines)
    dry_runs = list((kit_home / "ledger" / "dry-runs").glob("*.json"))
    assert len(dry_runs) == 1
    payload = json.loads(dry_runs[0].read_text(encoding="utf-8"))
    assert payload["uiType"] == "SWAPPABLE_INTELLIGENCE"


def test_clone_with_yes_creates_verifies_and_records(
    run_cli: RunCli, server: FakeSpaceServer, kit_home: Path
) -> None:
    code, lines = run_cli(*CLONE, "--set", "claude.effort=low", "--yes")

    created = server.spaces["assistant_new1"]
    configuration = created["modules"][0]["configuration"]
    assert code == 0, lines
    assert get_path(data=configuration, path="claude.effort") == "low"
    assert created["uiType"] == "SWAPPABLE_INTELLIGENCE"
    assert "  no differences" in lines
    assert Ledger(home=kit_home).live_space_ids(target="qa") == {"assistant_new1"}


def test_clone_refuses_a_name_that_already_exists(
    run_cli: RunCli, server: FakeSpaceServer
) -> None:
    code, _ = run_cli(
        "clone",
        "assistant_template",
        "--env",
        "qa",
        "--name",
        "base-space",
        "--yes",
    )

    assert code == 1
    assert [w for w in server.writes() if w[0] == "POST"] == []


def test_clone_with_a_typo_fails_before_any_write(
    run_cli: RunCli, server: FakeSpaceServer
) -> None:
    code, _ = run_cli(*CLONE, "--set", "claude.efort=low", "--yes")

    assert code == 1
    assert server.writes() == []


def test_clone_grants_access_after_create(
    run_cli: RunCli, server: FakeSpaceServer
) -> None:
    code, _ = run_cli(*CLONE, "--grant", "GROUP:group_1:USE", "--yes")

    assert code == 0
    assert server.access["assistant_new1"] == [
        {"entityId": "group_1", "entityType": "GROUP", "type": "USE"}
    ]


def test_delete_only_touches_spaces_space_kit_created(
    run_cli: RunCli, server: FakeSpaceServer
) -> None:
    refused, _ = run_cli("delete", "assistant_template", "--env", "qa", "--yes")
    _ = run_cli(*CLONE, "--yes")
    deleted, _ = run_cli("delete", "assistant_new1", "--env", "qa", "--yes")

    assert refused == 1
    assert "assistant_template" in server.spaces
    assert deleted == 0
    assert "assistant_new1" not in server.spaces


def test_edit_patches_the_full_config_and_keeps_the_project_name(
    run_cli: RunCli, server: FakeSpaceServer
) -> None:
    code, lines = run_cli(
        "edit",
        "assistant_template",
        "--env",
        "qa",
        "--set",
        "claude.effort=low",
        "--yes",
    )

    method, path, body = server.writes()[0]
    assert code == 0
    assert (method, path) == ("PATCH", "/space/assistant_template")
    assert isinstance(body, dict)
    assert "mcpServers" not in body
    configuration = server.spaces["assistant_template"]["modules"][0]["configuration"]
    assert get_path(data=configuration, path="claude.effort") == "low"
    assert get_path(data=configuration, path="space.projectName") == "base-space"
    assert any("claude.effort" in line for line in lines)


def test_apply_reads_a_spec_with_file_values(
    run_cli: RunCli, server: FakeSpaceServer, tmp_path: Path
) -> None:
    _ = (tmp_path / "agent.md").write_text("Batch searches.", encoding="utf-8")
    spec = tmp_path / "spec.yaml"
    _ = spec.write_text(
        "env: qa\nname: variant-searchpar2\ntemplate: assistant_template\n"
        "set:\n  setup.agentMdInstructions: '@file:agent.md'\n"
        "mcp:\n  servers:\n    yahoo-finance: [get_quote]\n",
        encoding="utf-8",
    )

    code, lines = run_cli("apply", str(spec), "--yes")

    created = server.spaces["assistant_new1"]
    configuration = created["modules"][0]["configuration"]
    assert code == 0, lines
    assert get_path(data=configuration, path="setup.agentMdInstructions") == (
        "Batch searches."
    )
    yahoo = next(
        a for a in created["assistantMcpServers"] if a["mcpServerId"] == "mcp_yahoo"
    )
    assert [t["name"] for t in yahoo["tools"] if t["isEnabled"]] == ["get_quote"]


def test_restricted_server_stops_the_clone_with_guidance(
    run_cli: RunCli, server: FakeSpaceServer
) -> None:
    code, _ = run_cli(*CLONE, "--mcp", "Elicitation Tester=all", "--yes")

    assert code == 1
    assert server.writes() == []


def _fake_harness_eval(tmp_path: Path) -> Path:
    home = tmp_path / "harness-eval"
    package = home / "harness_eval" / "profiles"
    package.mkdir(parents=True)
    _ = (home / "harness_eval" / "__init__.py").write_text("", encoding="utf-8")
    _ = (package / "__init__.py").write_text("", encoding="utf-8")
    _ = (package / "loader.py").write_text(
        "import yaml\n"
        "class _S:\n"
        "    def __init__(self, e): self.tool_profile = e.get('tool_profile', 'eval_tools_v1')\n"
        "def load_spaces(*, path):\n"
        "    spaces = yaml.safe_load(path.read_text())['spaces']\n"
        "    ids = [e['assistant_id'] for e in spaces.values()]\n"
        "    assert len(ids) == len(set(ids)), 'duplicate id'\n"
        "    return {n: _S(e) for n, e in spaces.items()}\n"
        "def load_tool_profiles(*, directory):\n"
        "    return {p.stem: p for p in directory.glob('eval_tools_*.yaml')}\n",
        encoding="utf-8",
    )
    (home / "profiles").mkdir()
    _ = (home / "profiles" / "eval_tools_v2.yaml").write_text(
        "x: 1\n", encoding="utf-8"
    )
    _ = (home / "spaces.yaml").write_text(
        "spaces:\n  base-space:\n    assistant_id: assistant_template\n"
        "    harness: claude_code\n    tool_profile: eval_tools_v2\n"
        "    comparable_group: perf-s55\n",
        encoding="utf-8",
    )
    return home


def test_register_appends_a_derived_entry_after_create(
    run_cli: RunCli, tmp_path: Path
) -> None:
    home = _fake_harness_eval(tmp_path)

    code, lines = run_cli(
        *CLONE,
        "--set",
        "claude.effort=low",
        "--register",
        "variant-low",
        "--yes",
        environ={"SPACE_KIT_HARNESS_EVAL_HOME": str(home)},
    )

    text = (home / "spaces.yaml").read_text(encoding="utf-8")
    assert code == 0, lines
    assert "assistant_new1" in text
    assert "derived_from: base-space" in text
    assert "changed_key: claude.effort" in text
    assert "tool_profile: eval_tools_v2" in text


def test_register_problems_fail_before_the_space_exists(
    run_cli: RunCli, server: FakeSpaceServer, tmp_path: Path
) -> None:
    home = _fake_harness_eval(tmp_path)
    before = (home / "spaces.yaml").read_text(encoding="utf-8")

    code, _ = run_cli(
        *CLONE,
        "--set",
        "claude.effort=low",
        "--set",
        "claude.maxBudgetUsd=5",
        "--register",
        "variant-low",
        "--yes",
        environ={"SPACE_KIT_HARNESS_EVAL_HOME": str(home)},
    )

    assert code == 1
    assert server.writes() == []
    assert (home / "spaces.yaml").read_text(encoding="utf-8") == before


def test_cli_never_prints_the_api_key(
    run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    _, lines = run_cli(*CLONE, "--yes")
    _, show = run_cli("show", "assistant_new1", "--env", "qa")
    captured = capsys.readouterr()

    everything = "\n".join([*lines, *show, captured.out, captured.err])
    assert "test-key-not-real" not in everything


def test_python_dash_m_entry_point_shows_help() -> None:
    import subprocess

    completed = subprocess.run(
        [sys.executable, "-m", "space_kit", "--help"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "clone" in completed.stdout
