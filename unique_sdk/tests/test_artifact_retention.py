"""Unit tests for integration artifact retention pruning."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.integration.conftest import prune_artifact_runs


@pytest.mark.ai
@pytest.mark.unit
def test_prune_artifact_runs__removes_older_than_max_age(tmp_path: Path) -> None:
    """
    Purpose: Verify runs older than max_age are deleted.
    Why this matters: Artifact dirs must not grow unbounded on disk.
    Setup summary: Create old and new run dirs, prune with 2-day max age.
    """
    now = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)
    old = tmp_path / "20260809T120000000000Z"
    new = tmp_path / "20260812T110000000000Z"
    old.mkdir()
    new.mkdir()

    old_ts = (now - timedelta(days=3)).timestamp()
    new_ts = now.timestamp()
    os.utime(old, (old_ts, old_ts))
    os.utime(new, (new_ts, new_ts))

    removed = prune_artifact_runs(
        tmp_path,
        max_age=timedelta(days=2),
        max_keep=20,
        now=now,
    )

    assert old in removed
    assert not old.exists()
    assert new.exists()


@pytest.mark.ai
@pytest.mark.unit
def test_prune_artifact_runs__keeps_only_max_per_test(tmp_path: Path) -> None:
    """
    Purpose: Verify only the newest max_keep runs are retained.
    Why this matters: Caps disk use when tests run frequently.
    Setup summary: Create 25 fresh run dirs, prune with max_keep=20.
    """
    now = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)
    for i in range(25):
        (tmp_path / f"20260812T{i:06d}000000Z").mkdir()

    removed = prune_artifact_runs(
        tmp_path,
        max_age=timedelta(days=2),
        max_keep=20,
        now=now,
    )

    remaining = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(remaining) == 20
    assert len(removed) == 5
    assert "20260812T000024000000Z" in remaining
    assert "20260812T000000000000Z" not in remaining
