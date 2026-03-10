"""
L2 integration tests for workspace persistence (real ContentService / QA platform).

These tests use a real Unique platform ContentService. No Claude API calls.
They validate: setup_workspace → persist_workspace → setup_workspace roundtrip,
and skill download from a KB scope.

Setup:
    Same as test_integration.py: .env.local or .local-dev/unique.env.qa with
    UNIQUE_APP_KEY, UNIQUE_APP_ID, UNIQUE_API_BASE_URL, UNIQUE_AUTH_COMPANY_ID,
    UNIQUE_AUTH_USER_ID.

    For skills test only: set UNIQUE_TEST_SKILLS_SCOPE_ID to a KB scope that
    contains skill files with keys like "intro/SKILL.md" or "output-format/SKILL.md".
    See .local-dev/claude_sdk_integration/docs/kb-skills-upload-structure.md.

Run:
    set -a && source ../.env.local && set +a
    cd unique_toolkit
    uv run pytest tests/agentic/claude_agent/test_workspace_e2e.py -v

    Run only roundtrip (no skills scope needed):
    uv run pytest tests/agentic/claude_agent/test_workspace_e2e.py -v -k "roundtrip"
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# Reuse env loading from integration tests
from tests.agentic.claude_agent.test_integration import _ENV, _init_platform
from unique_toolkit.agentic.claude_agent import workspace as workspace_module

UNIQUE_APP_KEY = os.environ.get("UNIQUE_APP_KEY", "") or _ENV.get("UNIQUE_APP_KEY", "")
UNIQUE_APP_ID = os.environ.get("UNIQUE_APP_ID", "") or _ENV.get("UNIQUE_APP_ID", "")
UNIQUE_API_BASE_URL = os.environ.get("UNIQUE_API_BASE_URL", "") or _ENV.get(
    "UNIQUE_API_BASE_URL", ""
)
UNIQUE_COMPANY_ID = os.environ.get("UNIQUE_AUTH_COMPANY_ID", "") or _ENV.get(
    "UNIQUE_AUTH_COMPANY_ID", ""
)
UNIQUE_USER_ID = os.environ.get("UNIQUE_AUTH_USER_ID", "") or _ENV.get(
    "UNIQUE_AUTH_USER_ID", ""
)
UNIQUE_TEST_SKILLS_SCOPE_ID = os.environ.get(
    "UNIQUE_TEST_SKILLS_SCOPE_ID", ""
) or _ENV.get("UNIQUE_TEST_SKILLS_SCOPE_ID", "")

needs_platform = pytest.mark.skipif(
    not (
        UNIQUE_APP_KEY and UNIQUE_API_BASE_URL and UNIQUE_COMPANY_ID and UNIQUE_USER_ID
    ),
    reason="UNIQUE_APP_KEY, UNIQUE_API_BASE_URL, UNIQUE_AUTH_COMPANY_ID, UNIQUE_AUTH_USER_ID required",
)
needs_skills_scope = pytest.mark.skipif(
    not UNIQUE_TEST_SKILLS_SCOPE_ID,
    reason="UNIQUE_TEST_SKILLS_SCOPE_ID not set (KB scope with skill files)",
)

# Stable chat_id for workspace tests; checkpoint will remain in your dev KB
WORKSPACE_E2E_CHAT_ID = "test-workspace-persistence-001"
LOG = logging.getLogger("workspace_e2e")


@needs_platform
@pytest.mark.asyncio
async def test_L2_workspace_roundtrip(tmp_path: Path) -> None:
    """Setup → create output file → persist → setup again: checkpoint restores workspace.

    Uses real ContentService. First setup creates empty workspace; we add a file
    in output/ and .claude/, then persist. Second setup restores from the uploaded
    zip; we assert the files are back. Checkpoint remains in KB under WORKSPACE_E2E_CHAT_ID.
    """
    content_service = _init_platform()

    with patch.object(workspace_module, "_TMP_DIR", tmp_path):
        workspace_dir = await workspace_module.setup_workspace(
            content_service=content_service,
            chat_id=WORKSPACE_E2E_CHAT_ID,
            logger=LOG,
            skills_scope_id=None,
        )
    assert workspace_dir.is_dir()
    # Simulate agent writing output and session state
    (workspace_dir / "output").mkdir(exist_ok=True)
    (workspace_dir / "output" / "foo.txt").write_text("hello from e2e")
    (workspace_dir / ".claude").mkdir(exist_ok=True)
    (workspace_dir / ".claude" / "session.json").write_text("{}")

    await workspace_module.persist_workspace(
        workspace_dir=workspace_dir,
        content_service=content_service,
        chat_id=WORKSPACE_E2E_CHAT_ID,
        logger=LOG,
    )

    # Simulate a new turn: fresh setup should restore from checkpoint (same WORKSPACE_BASE)
    with patch.object(workspace_module, "_TMP_DIR", tmp_path):
        workspace_dir2 = await workspace_module.setup_workspace(
            content_service=content_service,
            chat_id=WORKSPACE_E2E_CHAT_ID,
            logger=LOG,
            skills_scope_id=None,
        )
    assert (workspace_dir2 / "output" / "foo.txt").read_text() == "hello from e2e"
    assert (workspace_dir2 / ".claude" / "session.json").read_text() == "{}"


@needs_platform
@needs_skills_scope
@pytest.mark.asyncio
async def test_L2_workspace_skills_download(tmp_path: Path) -> None:
    """Setup with skills_scope_id: .claude/skills/ is populated from KB scope.

    Requires UNIQUE_TEST_SKILLS_SCOPE_ID and at least one skill file in that scope
    with key like "intro/SKILL.md" or "output-format/SKILL.md".
    """
    content_service = _init_platform()

    with patch.object(workspace_module, "_TMP_DIR", tmp_path):
        workspace_dir = await workspace_module.setup_workspace(
            content_service=content_service,
            chat_id=WORKSPACE_E2E_CHAT_ID,
            logger=LOG,
            skills_scope_id=UNIQUE_TEST_SKILLS_SCOPE_ID,
        )

    skills_dir = workspace_dir / ".claude" / "skills"
    assert skills_dir.is_dir()
    skill_subdirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert skill_subdirs, (
        "Expected at least one skill subdirectory under .claude/skills/"
    )
    skill_mds = list(skills_dir.rglob("SKILL.md"))
    assert skill_mds, "Expected at least one SKILL.md under .claude/skills/<name>/"
