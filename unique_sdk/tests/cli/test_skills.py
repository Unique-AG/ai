"""Guard tests for the bundled unique-cli skill docs.

The runner on the Unique platform copies these ``SKILL.md`` files out of the
installed ``unique_sdk`` wheel and feeds each skill's front-matter description
to the agent so it knows which command to reach for. Two invariants matter for
the uploaded-document search feature (UN-21780):

1. ``unique-cli-uploaded-search`` is its **own** skill, so the monorepo can
   gate it on the ``UploadedSearch`` synthetic tool and hide it entirely when a
   space has no uploaded files / the feature is off.
2. The always-on ``unique-cli-search`` skill must **not** mention
   ``uploaded-search`` — otherwise the agent is told about the uploaded path
   even when it is gated off, which defeats the clean off-switch.

These are file-content assertions on purpose: the skills ship as data in the
wheel, and a regression here is invisible to ordinary import/CLI tests.
"""

from __future__ import annotations

from pathlib import Path

import unique_sdk.cli

_SKILLS_DIR = Path(unique_sdk.cli.__file__).parent / "skills"


def _read_skill(name: str) -> str:
    skill = _SKILLS_DIR / name / "SKILL.md"
    assert skill.is_file(), f"missing skill: {skill}"
    return skill.read_text(encoding="utf-8")


def test_uploaded_search_skill_exists_and_is_named() -> None:
    text = _read_skill("unique-cli-uploaded-search")
    assert "name: unique-cli-uploaded-search" in text
    # It must document the command it exists for and the shared citation rule.
    assert "unique-cli uploaded-search" in text
    assert "[sourceN]" in text


def test_uploaded_search_skill_is_self_contained() -> None:
    """The gated skill may be copied without the shared search skill (a space
    can have uploads but no InternalSearch tool), so it must carry its own
    citation contract rather than defer to unique-cli-search."""
    text = _read_skill("unique-cli-uploaded-search")
    assert "<sourceN>" in text
    assert "web-search" in text  # namespace-separation rule is spelled out


def test_search_skill_does_not_reference_uploaded_search() -> None:
    """De-pointer guard: the always-on search skill must not advertise the
    gated uploaded-search command (any casing/spelling of the token)."""
    text = _read_skill("unique-cli-search").lower()
    assert "uploaded-search" not in text
    assert "searching uploaded documents" not in text


def test_agentic_table_skill_exists_and_documents_read_commands() -> None:
    """The agentic-table skill is ungated (Tier 0 reads, server-side access
    enforcement), so it ships in every workspace. It must name itself and
    document each read command the CLI exposes."""
    text = _read_skill("unique-cli-agentic-table")
    assert "name: unique-cli-agentic-table" in text
    for command in (
        "agentic-table get-sheet",
        "agentic-table get-cell",
        "agentic-table cell-history",
        "agentic-table list-exports",
    ):
        assert command in text, f"skill does not document `{command}`"


def test_agentic_table_skill_is_read_only() -> None:
    """Guard against write commands leaking into the ungated read skill: writes
    have side-effects/authz needs and must live in a separate gated skill."""
    text = _read_skill("unique-cli-agentic-table").lower()
    assert "read-only" in text
    for write_command in ("set-cell", "set_cell", "update-cell", "delete"):
        assert write_command not in text, (
            f"ungated read skill must not document write command `{write_command}`"
        )
