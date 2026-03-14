"""
Multi-turn session resume: end-to-end test.

Proves that Claude remembers context across turns end-to-end — real API calls,
real ContentService, no mocks for the critical path.

What this test proves:
  (a) Workspace file continuity (T1.1): a file written by Claude in turn 1
      survives the simulated "container restart" and is accessible in turn 2.
  (b) Session resume: continue_conversation=True is enabled for turn 2
      because .claude/ (session state) is preserved in the checkpoint zip.

How it works:
  Turn 1 → write secret.txt → persist checkpoint zip → delete local workspace
  Turn 2 → restore workspace from zip → Claude reads secret.txt → MARKER-XK9

Setup:
    Copy .env.local.example (repo root) to .env.local and fill in credentials.
    Then load before running:

        set -a && source ../.env.local && set +a

Run:
    cd unique_toolkit
    uv run pytest tests/agentic/claude_agent/test_multiturn_e2e.py -v -s

Cost: ~$0.05–0.15 in Claude API credits.
"""

from __future__ import annotations

import logging
from typing import cast

import pytest

# Reuse platform helpers and env loading from test_integration.py
from tests.agentic.claude_agent.test_integration import (
    ANTHROPIC_API_KEY,
    UNIQUE_APP_KEY,
    UNIQUE_TEST_CHAT_ID,
    _init_platform,
    _make_live_runner,
)
from unique_toolkit.agentic.claude_agent.config import ClaudeAgentConfig
from unique_toolkit.agentic.claude_agent.workspace import (
    CHECKPOINT_FILENAME,
    cleanup_workspace,
)
from unique_toolkit.content.service import ContentService

# ─────────────────────────────────────────────────────────────────────────────
# Credentials & skip guard
# ─────────────────────────────────────────────────────────────────────────────

# The platform validates chat access before allowing content uploads, so
# UNIQUE_TEST_CHAT_ID must be a real existing chat on the QA platform.
# Find it in the URL when you open a chat: https://next.qa.unique.app/chat/<chat_id>
needs_multiturn = pytest.mark.skipif(
    not (ANTHROPIC_API_KEY and UNIQUE_APP_KEY and UNIQUE_TEST_CHAT_ID),
    reason="ANTHROPIC_API_KEY + UNIQUE_APP_KEY + UNIQUE_TEST_CHAT_ID all required",
)

LOG = logging.getLogger("multiturn_e2e")


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────


@needs_multiturn
@pytest.mark.asyncio
async def test_multiturn_session_resume() -> None:
    """Workspace checkpoint + session resume: full end-to-end proof.

    Turn 1: Claude writes secret.txt containing 'MARKER-XK9'.
            Workspace is persisted as a checkpoint zip in ContentService.
            Local workspace directory is deleted (simulates container restart).

    Between turns: test verifies the zip is in ContentService and the local
            directory is gone.

    Turn 2: New runner with same chat_id. setup_workspace() restores the
            directory from the zip. Claude reads secret.txt and returns MARKER-XK9.
    """
    content_service = cast(ContentService, _init_platform())
    chat_id = UNIQUE_TEST_CHAT_ID

    claude_config = ClaudeAgentConfig(
        enable_workspace_persistence=True,
        enable_code_execution=True,
        permission_mode="bypassPermissions",
        max_turns=5,
        system_prompt_override=(
            "You are a coding assistant. "
            "Always use the Write tool to create files and relative paths "
            "(e.g. ./secret.txt, never /tmp/)."
        ),
    )

    # ── Turn 1 ────────────────────────────────────────────────────────────────

    print("\n\n=== TURN 1: Claude writes secret.txt ===")

    runner1, _chunks1 = _make_live_runner(
        claude_config=claude_config,
        content_service=content_service,
        chat_id=chat_id,
    )

    workspace_dir = await runner1._setup_workspace()
    assert workspace_dir is not None, "setup_workspace() returned None"
    print(f"Workspace dir: {workspace_dir}")

    options1 = runner1._build_options(
        system_prompt=claude_config.system_prompt_override,
        workspace_dir=workspace_dir,
    )

    print("\n--- Turn 1 Claude output ---")
    result1 = await runner1._run_claude_loop(
        prompt=(
            "Use the Write tool to create a file called secret.txt in your current "
            "working directory containing only the text 'MARKER-XK9'. "
            "Then read it back and confirm its exact contents."
        ),
        options=options1,
    )
    print(f"\n--- Turn 1 done ({len(result1)} chars) ---\n")

    # Verify Claude confirmed writing the file
    assert "secret.txt" in result1.lower() or "MARKER" in result1, (
        f"Turn 1: Claude did not confirm writing secret.txt. Response: {result1!r}"
    )

    # Verify secret.txt was actually created in the local workspace
    secret_file = workspace_dir / "secret.txt"
    assert secret_file.exists(), (
        f"secret.txt not found in workspace {workspace_dir}. "
        f"Contents: {sorted(str(p) for p in workspace_dir.rglob('*'))}"
    )
    assert "MARKER-XK9" in secret_file.read_text(), (
        f"secret.txt exists but does not contain MARKER-XK9. "
        f"Contents: {secret_file.read_text()!r}"
    )
    print(f"✓ secret.txt confirmed locally: {secret_file.read_text()!r}")

    # Persist workspace → uploads checkpoint zip to ContentService
    await runner1._save_workspace_checkpoint(workspace_dir)
    print("✓ Workspace persisted to ContentService")

    # Verify the checkpoint zip landed in ContentService
    chat_files = await content_service.search_contents_async(
        where={"ownerId": {"equals": chat_id}},
        chat_id=chat_id,
    )
    zip_keys = [f.key for f in chat_files]
    assert CHECKPOINT_FILENAME in zip_keys, (
        f"Checkpoint zip '{CHECKPOINT_FILENAME}' not found in ContentService. "
        f"Files found under chat_id={chat_id!r}: {zip_keys}"
    )
    print(f"✓ Checkpoint zip confirmed in ContentService: {zip_keys}")

    # ── Simulate container restart ─────────────────────────────────────────────

    print("\n=== SIMULATING CONTAINER RESTART: deleting local workspace ===")
    cleanup_workspace(workspace_dir, LOG)
    assert not workspace_dir.exists(), (
        f"Expected workspace to be deleted, but it still exists: {workspace_dir}"
    )
    print(f"✓ Local workspace deleted: {workspace_dir}")

    # ── Turn 2 ────────────────────────────────────────────────────────────────

    print("\n=== TURN 2: New runner — workspace restored from checkpoint ===")

    runner2, _chunks2 = _make_live_runner(
        claude_config=claude_config,
        content_service=content_service,
        chat_id=chat_id,
    )

    # setup_workspace() downloads and extracts the checkpoint zip
    workspace_dir2 = await runner2._setup_workspace()
    assert workspace_dir2 is not None, "Turn 2 setup_workspace() returned None"
    print(f"Workspace dir (turn 2): {workspace_dir2}")

    # Verify secret.txt was restored from the checkpoint
    restored_secret = workspace_dir2 / "secret.txt"
    assert restored_secret.exists(), (
        f"secret.txt was NOT restored from checkpoint in {workspace_dir2}. "
        f"Workspace contents: {sorted(str(p) for p in workspace_dir2.rglob('*'))}"
    )
    print(f"✓ secret.txt restored from checkpoint: {restored_secret.read_text()!r}")

    options2 = runner2._build_options(
        system_prompt=claude_config.system_prompt_override,
        workspace_dir=workspace_dir2,
    )

    # Verify session resume is enabled (requires .claude/ to exist in restored workspace)
    assert options2.get("continue_conversation") is True, (
        "Expected continue_conversation=True for turn 2. "
        "This requires .claude/ to be present in the restored workspace, which means "
        "the checkpoint zip must include it. Check that Claude wrote to .claude/ in turn 1."
    )
    print("✓ continue_conversation=True confirmed for turn 2")

    print("\n--- Turn 2 Claude output ---")
    result2 = await runner2._run_claude_loop(
        prompt="What is the exact content of secret.txt in your working directory?",
        options=options2,
    )
    print(f"\n--- Turn 2 done ({len(result2)} chars) ---\n")

    # Core assertion: Claude can read the restored file and return the marker
    assert "MARKER-XK9" in result2, (
        f"Turn 2: Expected 'MARKER-XK9' in response but did not find it. "
        f"Response: {result2!r}"
    )
    print("✓ MARKER-XK9 confirmed in turn 2 response — workspace persistence proven!")

    # Cleanup
    cleanup_workspace(workspace_dir2, LOG)
    print("✓ Turn 2 workspace cleaned up")


@needs_multiturn
@pytest.mark.asyncio
async def test_multiturn_conversational_memory() -> None:
    """Conversational memory via native session resume: end-to-end proof.

    Turn 1: Claude is told the secret code ALPHA-7 verbally and asked NOT to
            write it anywhere. Workspace is persisted (captures .claude/ session
            state). Local workspace directory is deleted (simulates container restart).

    Turn 2: New runner with same chat_id. setup_workspace() restores the
            directory from the zip. Claude recalls ALPHA-7 from session memory —
            no file access possible because it was never written to disk.
    """
    content_service = cast(ContentService, _init_platform())
    chat_id = UNIQUE_TEST_CHAT_ID

    claude_config = ClaudeAgentConfig(
        enable_workspace_persistence=True,
        enable_code_execution=True,
        permission_mode="bypassPermissions",
        max_turns=5,
    )

    # ── Turn 1 ────────────────────────────────────────────────────────────────

    print("\n\n=== TURN 1: Tell Claude the secret code (no file write) ===")

    runner1, _chunks1 = _make_live_runner(
        claude_config=claude_config,
        content_service=content_service,
        chat_id=chat_id,
    )

    workspace_dir = await runner1._setup_workspace()
    assert workspace_dir is not None, "setup_workspace() returned None"
    print(f"Workspace dir: {workspace_dir}")

    options1 = runner1._build_options(
        system_prompt=claude_config.system_prompt_override,
        workspace_dir=workspace_dir,
    )

    print("\n--- Turn 1 Claude output ---")
    result1 = await runner1._run_claude_loop(
        prompt=(
            "The secret code is ALPHA-7. "
            "Do not write this anywhere, just keep it in mind. "
            "Confirm you have noted it."
        ),
        options=options1,
    )
    print(f"\n--- Turn 1 done ({len(result1)} chars) ---\n")

    assert "ALPHA-7" in result1, (
        f"Turn 1: Claude did not confirm noting ALPHA-7. Response: {result1!r}"
    )
    print("✓ Claude confirmed ALPHA-7 in turn 1")

    # Persist workspace → uploads checkpoint zip (including .claude/ session state)
    await runner1._save_workspace_checkpoint(workspace_dir)
    print("✓ Workspace persisted to ContentService")

    # ── Simulate container restart ─────────────────────────────────────────────

    print("\n=== SIMULATING CONTAINER RESTART: deleting local workspace ===")
    cleanup_workspace(workspace_dir, LOG)
    assert not workspace_dir.exists(), (
        f"Expected workspace to be deleted, but it still exists: {workspace_dir}"
    )
    print(f"✓ Local workspace deleted: {workspace_dir}")

    # ── Turn 2 ────────────────────────────────────────────────────────────────

    print("\n=== TURN 2: New runner — Claude must recall from session memory ===")

    runner2, _chunks2 = _make_live_runner(
        claude_config=claude_config,
        content_service=content_service,
        chat_id=chat_id,
    )

    workspace_dir2 = await runner2._setup_workspace()
    assert workspace_dir2 is not None, "Turn 2 setup_workspace() returned None"
    print(f"Workspace dir (turn 2): {workspace_dir2}")

    options2 = runner2._build_options(
        system_prompt=claude_config.system_prompt_override,
        workspace_dir=workspace_dir2,
    )

    assert options2.get("continue_conversation") is True, (
        "Expected continue_conversation=True for turn 2. "
        "This requires .claude/ to be present in the restored workspace."
    )
    print("✓ continue_conversation=True confirmed for turn 2")

    print("\n--- Turn 2 Claude output ---")
    result2 = await runner2._run_claude_loop(
        prompt="What was the secret code I told you in our previous conversation?",
        options=options2,
    )
    print(f"\n--- Turn 2 done ({len(result2)} chars) ---\n")

    # Core assertion: Claude recalls from session memory, not from any file
    assert "ALPHA-7" in result2, (
        f"Turn 2: Expected 'ALPHA-7' in response but did not find it. "
        f"Response: {result2!r}"
    )
    print("✓ ALPHA-7 confirmed in turn 2 response — conversational memory proven!")

    # Cleanup
    cleanup_workspace(workspace_dir2, LOG)
    print("✓ Turn 2 workspace cleaned up")
