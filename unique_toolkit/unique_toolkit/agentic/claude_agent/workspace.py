"""
Workspace persistence for Claude Agent SDK (WI-4 foundation).

This module will contain helpers for managing a per-chat persistent workspace
directory that survives across user turns:

- fetch_workspace(): downloads claude-agent-workspace.zip from ContentService
  and extracts it to /tmp/claude-agent-workspace/{chat_id}.
- persist_workspace(): zips the workspace dir and upserts it back via
  ContentService with ownerType=CHAT and skip_ingestion=True.
- cleanup_workspace(): removes the local workspace dir after the turn.

ClaudeAgentOptions(cwd=workspace_dir) gives Claude a stable filesystem view
across turns. The zip is keyed by chat_id so workspaces do not leak between
conversations.
"""

from __future__ import annotations
