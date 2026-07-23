"""Tests for MCP elicitation on destructive delete/reset tools."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_sqlite_excel.db.repository import SqliteCrudRepository
from mcp_sqlite_excel.mcp_sqlite_excel import (
    _elicit_destructive_confirm,
    delete_row,
    reset_from_excel,
)
from mcp_sqlite_excel.models import FieldMap


def _ctx_with_elicit(action: str, data: bool | None) -> MagicMock:
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=SimpleNamespace(action=action, data=data))
    return ctx


@pytest.mark.ai
def test_AI_elicit_destructive_confirm_requires_accept_and_true() -> None:
    """Purpose: only accept+True counts as confirmation.
    Why this matters: decline/cancel/false must not proceed with deletes.
    Setup summary: mock Context.elicit for several outcomes.
    """
    assert asyncio.run(_elicit_destructive_confirm(_ctx_with_elicit("accept", True), message="ok?"))
    assert not asyncio.run(_elicit_destructive_confirm(_ctx_with_elicit("accept", False), message="ok?"))
    assert not asyncio.run(_elicit_destructive_confirm(_ctx_with_elicit("decline", True), message="ok?"))
    assert not asyncio.run(_elicit_destructive_confirm(_ctx_with_elicit("cancel", None), message="ok?"))


@pytest.mark.ai
def test_AI_delete_row_cancels_when_user_declines(
    repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: declined elicitation leaves the row in place.
    Why this matters: delete_row must not mutate on cancel.
    Setup summary: create a row, mock elicit decline, call tool.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", repo)
    created = repo.create_row(
        "positions",
        FieldMap(
            {
                "sleeve": "Equity Long",
                "ticker": "ELIC",
                "instrument": "Elicit Corp",
                "direction": "Long",
                "target_weight": 0.01,
                "position_mm": 10,
                "email": "elicit@example.com",
            }
        ),
    )
    row_id = created.row["row_id"]

    raw = asyncio.run(
        delete_row(
            table="positions",
            row_id=row_id,
            ctx=_ctx_with_elicit("decline", None),
        )
    )
    payload = json.loads(raw)
    assert payload["error"] == "DeleteCancelled"
    assert repo.get_row("positions", row_id).row["ticker"] == "ELIC"


@pytest.mark.ai
def test_AI_delete_row_deletes_when_user_confirms(
    repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: accepted elicitation performs the delete.
    Why this matters: confirmation path must still remove the row.
    Setup summary: create a row, mock elicit accept+True, call tool.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", repo)
    created = repo.create_row(
        "positions",
        FieldMap(
            {
                "sleeve": "Equity Long",
                "ticker": "DEL1",
                "instrument": "Delete Me",
                "direction": "Long",
                "target_weight": 0.01,
                "position_mm": 10,
                "email": "del@example.com",
            }
        ),
    )
    row_id = created.row["row_id"]

    raw = asyncio.run(
        delete_row(
            table="positions",
            row_id=row_id,
            ctx=_ctx_with_elicit("accept", True),
        )
    )
    payload = json.loads(raw)
    assert payload["deleted"]["ticker"] == "DEL1"
    with pytest.raises(KeyError):
        repo.get_row("positions", row_id)


@pytest.mark.ai
def test_AI_reset_from_excel_cancels_when_user_declines(
    repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: declined reset elicitation does not wipe the DB.
    Why this matters: reset_from_excel is fully destructive.
    Setup summary: mock elicit decline and assert cancelled error.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", repo)
    before = repo.list_rows("positions").total_matching

    raw = asyncio.run(reset_from_excel(ctx=_ctx_with_elicit("cancel", None)))
    payload = json.loads(raw)
    assert payload["error"] == "ResetCancelled"
    assert repo.list_rows("positions").total_matching == before
