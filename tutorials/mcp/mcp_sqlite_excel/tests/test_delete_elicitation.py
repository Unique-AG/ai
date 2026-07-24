"""Tests for MCP elicitation on destructive delete/reset tools."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_sqlite_excel import prompts
from mcp_sqlite_excel.db.excel_loader import bootstrap_from_excel
from mcp_sqlite_excel.db.repository import SqliteCrudRepository
from mcp_sqlite_excel.mcp_sqlite_excel import (
    _default_escalate_note,
    _elicit_destructive_confirm,
    _is_escalate_update,
    _split_escalate_meta,
    delete_row,
    escalate_row,
    reset_from_excel,
    update_row,
)
from mcp_sqlite_excel.models import EscalateForm, FieldMap
from mcp_sqlite_excel.settings import AppSettings


def _ctx_with_elicit(action: str, data: object | None) -> MagicMock:
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=SimpleNamespace(action=action, data=data))
    return ctx


@pytest.mark.ai
def test_AI_is_escalate_update_detects_status_and_state() -> None:
    """Purpose: escalate detection matches status/state + escalate values.
    Why this matters: escalate_row uses this to decide whether to default status.
    Setup summary: check several field dicts case-insensitively.
    """
    assert _is_escalate_update({"status": "Escalated"})
    assert _is_escalate_update({"state": "escalate"})
    assert not _is_escalate_update({"status": "Compliant"})
    assert not _is_escalate_update({"direction": "Escalated"})


@pytest.mark.ai
def test_AI_split_escalate_meta_strips_note_and_recipient_from_fields() -> None:
    """Purpose: note/recipient keys are peeled out of fields for the notify email.
    Why this matters: agents often put note inside fields; those are not DB columns.
    Setup summary: split a mixed fields dict and assert meta vs row keys.
    """
    row_fields, note, recipient = _split_escalate_meta(
        {
            "status": "Escalated",
            "note": "Please review adverse media",
            "recipient_email": "compliance@example.com",
            "recommended_action": "Escalate to Compliance",
        }
    )
    assert row_fields == {
        "status": "Escalated",
        "recommended_action": "Escalate to Compliance",
    }
    assert note == "Please review adverse media"
    assert recipient == "compliance@example.com"


@pytest.mark.ai
def test_AI_escalate_form_and_note_defaults() -> None:
    """Purpose: escalate form ships with default recipient and note copy.
    Why this matters: elicitation UI should pre-fill sensible demo values.
    Setup summary: construct EscalateForm() and a contextual note.
    """
    form = EscalateForm()
    assert form.recipient_email == prompts.DEFAULT_ESCALATE_RECIPIENT_EMAIL
    assert form.note == prompts.DEFAULT_ESCALATE_NOTE
    note = _default_escalate_note({"client_name": "Ada Lovelace", "open_issue": "Adverse media hit"})
    assert "Ada Lovelace" in note
    assert "Adverse media hit" in note


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


@pytest.fixture
def account_review_repo(tmp_path) -> SqliteCrudRepository:
    """Repository seeded from the account-review workbook (has status column)."""
    excel = Path(__file__).resolve().parents[1] / "data" / "account_review_dataset.xlsx"
    if not excel.is_file():
        pytest.skip("account_review_dataset.xlsx not present")
    settings = AppSettings(
        excel_path=excel,
        sqlite_path=tmp_path / "account_review.db",
        auth_disabled=True,
    )
    bootstrap_from_excel(settings=settings, replace=True)
    return SqliteCrudRepository(settings=settings)


@pytest.mark.ai
def test_AI_update_row_sets_escalated_without_elicitation(
    account_review_repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: update_row patches status immediately with no elicitation.
    Why this matters: console status menus need a silent write path.
    Setup summary: set Escalated via update_row; DB changes, no ctx required.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", account_review_repo)
    listed = account_review_repo.list_rows(
        "clients",
        filters=FieldMap({"status": "Compliant"}),
        limit=1,
    )
    row_id = listed.rows[0]["row_id"]

    raw = asyncio.run(
        update_row(
            table="clients",
            row_id=row_id,
            fields={"status": "Escalated"},
        )
    )
    payload = json.loads(raw)
    assert payload["row"]["status"] == "Escalated"
    assert "escalation_email" not in payload
    assert account_review_repo.get_row("clients", row_id).row["status"] == "Escalated"


@pytest.mark.ai
def test_AI_escalate_row_cancels_when_user_declines(
    account_review_repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: declining escalate_row form elicitation leaves status unchanged.
    Why this matters: escalate_row is the confirmable path for Compliance handoff.
    Setup summary: pick a Compliant client, mock decline, assert no DB change.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", account_review_repo)
    listed = account_review_repo.list_rows(
        "clients",
        filters=FieldMap({"status": "Compliant"}),
        limit=1,
    )
    assert listed.rows, "expected at least one Compliant client in seed data"
    row_id = listed.rows[0]["row_id"]

    raw = asyncio.run(
        escalate_row(
            table="clients",
            row_id=row_id,
            ctx=_ctx_with_elicit("decline", None),
        )
    )
    payload = json.loads(raw)
    assert payload["error"] == "EscalateCancelled"
    assert account_review_repo.get_row("clients", row_id).row["status"] == "Compliant"


@pytest.mark.ai
def test_AI_escalate_row_updates_and_notifies_when_form_accepted(
    account_review_repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: accepted escalate_row form updates status and records notify email.
    Why this matters: escalation must collect a recipient before applying.
    Setup summary: pick a Compliant client, accept form with email, assert result.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", account_review_repo)
    listed = account_review_repo.list_rows(
        "clients",
        filters=FieldMap({"status": "Compliant"}),
        limit=1,
    )
    row_id = listed.rows[0]["row_id"]
    form = EscalateForm(
        recipient_email="compliance@example.com",
        note="Please review adverse media hit",
    )

    raw = asyncio.run(
        escalate_row(
            table="clients",
            row_id=row_id,
            fields={"status": "escalate"},
            ctx=_ctx_with_elicit("accept", form),
        )
    )
    payload = json.loads(raw)
    assert payload["row"]["status"] == "escalate"
    assert payload["escalation_email"]["to"] == "compliance@example.com"
    assert payload["escalation_email"]["note"] == "Please review adverse media hit"
    assert payload["escalation_email"]["sent"] is True
    assert account_review_repo.get_row("clients", row_id).row["status"] == "escalate"


@pytest.mark.ai
def test_AI_escalate_row_accepts_note_inside_fields_without_unknown_column(
    account_review_repo: SqliteCrudRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Purpose: note stuffed into fields is used for email, not as a DB column.
    Why this matters: LLMs often pass {"note": "..."} in fields and previously failed.
    Setup summary: escalate with fields note only; accept form; assert Escalated + email.
    """
    monkeypatch.setattr("mcp_sqlite_excel.mcp_sqlite_excel.repo", account_review_repo)
    listed = account_review_repo.list_rows(
        "clients",
        filters=FieldMap({"status": "Compliant"}),
        limit=1,
    )
    row_id = listed.rows[0]["row_id"]
    form = EscalateForm(
        recipient_email="compliance@example.com",
        note="LLM-drafted escalation rationale",
    )
    ctx = _ctx_with_elicit("accept", form)

    raw = asyncio.run(
        escalate_row(
            table="clients",
            row_id=row_id,
            fields={"note": "LLM-drafted escalation rationale"},
            ctx=ctx,
        )
    )
    payload = json.loads(raw)
    assert "error" not in payload
    assert payload["row"]["status"] == "Escalated"
    assert payload["escalation_email"]["note"] == "LLM-drafted escalation rationale"
    assert payload["escalation_email"]["sent"] is True
    # Prefill for elicitation should come from the stripped fields note.
    _args, kwargs = ctx.elicit.await_args
    form_type = kwargs.get("response_type") or _args[1]
    assert form_type.model_fields["note"].default == "LLM-drafted escalation rationale"
