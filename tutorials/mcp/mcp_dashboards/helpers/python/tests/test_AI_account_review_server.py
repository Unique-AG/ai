from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def _load_account_review_server() -> Any:
    app_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
        / "app.py"
    )
    # Ensure dataset-local imports resolve the same way as `python app.py`.
    dataset_root = str(app_path.parent)
    if dataset_root not in sys.path:
        sys.path.insert(0, dataset_root)
    spec = importlib.util.spec_from_file_location(
        "account_review_app_for_test", app_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.ai
def test_AI_account_review_server__uses_dataset_local_paths__for_excel_and_sqlite() -> (
    None
):
    """
    Purpose: Verify the generated account-review FastMCP app owns its Excel and SQLite paths.
    Why this matters: Dataset apps must be isolated from shared helper state and from other datasets.
    Setup summary: Import the server module by file path and assert its configured paths live under fastmcp/data.
    """
    module = _load_account_review_server()
    dataset_root = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
    )

    assert (
        module.settings.excel_path
        == dataset_root / "data" / "account_review_dataset.xlsx"
    )
    assert (
        module.settings.sqlite_path
        == dataset_root / "data" / "account_review.sqlite"
    )


@pytest.mark.ai
def test_AI_account_review_storage__splits_clients_into_domain_tables__and_joins_for_reads() -> (
    None
):
    """
    Purpose: Verify curated storage uses 1:1 domain tables and joined list/update still work.
    Why this matters: A ~100-column clients row is unusable in admin; satellites must stay in sync.
    Setup summary: Reset from Excel, assert table set, list joined rows, patch status via update_client_fields.
    """
    module = _load_account_review_server()
    module.repo.reset_from_excel()
    tables = set(module.repo.list_tables())
    assert {
        "clients",
        "contacts",
        "portfolios",
        "compliance",
        "review_schedules",
        "suitability",
        "case_actions",
        "figure_metrics",
    }.issubset(tables)

    clients_schema = module.repo.get_table_schema("clients")
    assert "name" in clients_schema.column_names
    assert "identity_name" not in clients_schema.column_names
    assert "case_action_status" not in clients_schema.column_names

    listed = module.repo.list_client_rows(limit=5)
    assert listed.total_matching >= 1
    row = listed.rows[0]
    assert "identity_name" in row
    assert "case_action_status" in row
    assert "compliance_risk_level" in row

    pk = int(row["id"])
    updated = module.repo.update_client_fields(
        pk, {"case_action_status": "Compliant"}
    )
    assert updated["case_action_status"] == "Compliant"
    assert module.repo.get_row("case_actions", pk).row["status"] == "Compliant"


@pytest.mark.ai
def test_AI_email_draft_elicit_model__omits_nullable_unions__for_platform_elicitation() -> (
    None
):
    """
    Purpose: Verify email elicitation schemas never emit Status | null for new_status.
    Why this matters: Unique platform elicitation rejects nullable union types and fails send_email.
    Setup summary: Build client and compliance draft forms and assert JSON Schema has no null.
    """
    module = _load_account_review_server()
    Status = module.Status
    Audience = module.Audience
    OutboundEmailDraft = module.OutboundEmailDraft
    client = SimpleNamespace(
        case_action=SimpleNamespace(status=Status.Screening_hit),
    )

    for audience, expected_default in (
        (Audience.client, Status.Screening_hit),
        (Audience.compliance, Status.Escalated),
    ):
        proposed = OutboundEmailDraft(
            audience=audience,
            to="to@example.com",
            subject="Subject",
            body="Body",
            new_status=Status.Escalated if audience is Audience.compliance else None,
        )
        form = module._email_draft_elicit_model(
            proposed=proposed, client=client, audience=audience
        )
        schema = form.model_json_schema()
        encoded = json.dumps(schema)
        assert "null" not in encoded, schema
        new_status = schema["properties"]["new_status"]
        assert "anyOf" not in new_status
        assert "oneOf" not in new_status
        assert form.model_fields["new_status"].default == expected_default
        assert form.model_fields["to"].default == "to@example.com"


@pytest.mark.ai
def test_AI_email_str__unwraps_email_address_root_model__as_plain_address() -> None:
    """
    Purpose: Verify EmailAddress RootModel values serialize to plain addresses.
    Why this matters: str(EmailAddress) yields root='a@b.com', which broke elicitation defaults.
    Setup summary: Format a RootModel address and a raw string through `_email_str`.
    """
    module = _load_account_review_server()
    email = module.OutboundEmailDraft(
        audience=module.Audience.compliance,
        to="compliance@unique.ai",
        subject="s",
        body="b",
    ).to

    assert module._email_str(email) == "compliance@unique.ai"
    assert module._email_str("plain@unique.ai") == "plain@unique.ai"
    assert "root=" not in module._email_str(email)


@pytest.mark.ai
def test_AI_default_email_draft__signs_with_signer_and_uses_unique_compliance_inbox() -> (
    None
):
    """
    Purpose: Verify drafts sign with signer_name and Compliance goes to compliance@unique.ai.
    Why this matters: Hardcoded Elena Maltseva / schroders.demo were wrong for the Unique demo.
    Setup summary: Build a minimal client stub and draft client + compliance emails.
    """
    module = _load_account_review_server()
    Status = module.Status
    Audience = module.Audience
    client = SimpleNamespace(
        identity=SimpleNamespace(name="Ada Lovelace", reference="CH-1"),
        contact=SimpleNamespace(email="ada@example.com"),
        compliance=SimpleNamespace(criticality="AMBER", risk_level="High"),
        case_action=SimpleNamespace(
            status=Status.Screening_hit,
            title="PEP hit",
            open_issue="PEP match",
            recommended_action="Escalate to Compliance",
            rule_code="R-SCR-PEP",
        ),
    )

    compliance = module._default_email_draft(
        client, Audience.compliance, signer_name="Cedric Demo"
    )
    assert compliance.to.root == "compliance@unique.ai"
    assert "Cedric Demo" in compliance.body
    assert "Elena Maltseva" not in compliance.body
    assert "Relationship Manager" not in compliance.body

    client_mail = module._default_email_draft(
        client, Audience.client, signer_name="Cedric Demo"
    )
    assert module._email_str(client_mail.to) == "ada@example.com"
    assert client_mail.body.endswith("Cedric Demo")


@pytest.mark.ai
def test_AI_send_email_payload__reports_sent_and_not_sent__with_delivery_message() -> (
    None
):
    """
    Purpose: Verify send_email facade results always answer whether mail was sent.
    Why this matters: Agents must relay sent vs not-sent; cancel must not be a bare ToolError.
    Setup summary: Load one real client from the dataset DB and assert both sent payloads.
    """
    module = _load_account_review_server()
    Audience = module.Audience
    OutboundEmailDraft = module.OutboundEmailDraft
    module.repo.ensure_ready()
    row = module.repo.list_client_rows(limit=1).rows[0]
    client = module._client_from_row(
        row, module.DashboardFigures(**module._empty_figure_groups())
    )
    draft = OutboundEmailDraft(
        audience=Audience.client,
        to="ada@example.com",
        subject="Action required",
        body="Please renew your passport.",
    )

    sent_payload = module._send_email_payload(
        client=client,
        draft=draft,
        sent=True,
        status_updated=True,
        message_id="msg-1-client-abc",
        delivery_message=(
            "Email sent to ada@example.com (the client) — simulated delivery "
            "(facade; message_id=msg-1-client-abc)."
        ),
    )
    assert sent_payload["sent"] is True
    assert sent_payload["message_id"] == "msg-1-client-abc"
    assert "sent" in sent_payload["delivery_message"].lower()
    assert sent_payload["status_updated"] is True

    not_sent = module._send_email_payload(
        client=client,
        draft=draft,
        sent=False,
        status_updated=False,
        message_id=None,
        delivery_message=(
            "Email not sent — send confirmation was cancelled. "
            "No message was delivered to ada@example.com."
        ),
    )
    assert not_sent["sent"] is False
    assert not_sent["message_id"] is None
    assert "not sent" in not_sent["delivery_message"].lower()
    assert not_sent["status_updated"] is False


@pytest.mark.ai
def test_AI_send_email__sends_after_draft_accept__without_second_elicitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify accepting the editable email form is enough to send the demo email.
    Why this matters: RMs should not have to confirm twice after reviewing the complete form.
    Setup summary: Patch draft elicitation to return an accepted draft and fail the test if confirm is called.
    """
    module = _load_account_review_server()
    mcp_tools = module._mcp_tools
    Audience = module.Audience
    OutboundEmailDraft = module.OutboundEmailDraft
    module.repo.ensure_ready()
    row = module.repo.list_client_rows(limit=1).rows[0]
    client = module._client_from_row(
        row, module.DashboardFigures(**module._empty_figure_groups())
    )
    draft = OutboundEmailDraft(
        audience=Audience.client,
        to="ada@example.com",
        subject="Action required",
        body="Please renew your passport.",
    )
    calls = SimpleNamespace(draft=0, confirm=0)

    async def fake_elicit_email_draft(**kwargs: Any) -> Any:  # noqa: ARG001
        calls.draft += 1
        return draft

    async def fail_if_confirmed(*args: Any, **kwargs: Any) -> bool:  # noqa: ARG001
        calls.confirm += 1
        raise AssertionError("send_email should not ask for a second confirmation")

    # Patches must target mcp_tools: send_email resolves helpers in that module.
    monkeypatch.setattr(mcp_tools, "client_by_pk", lambda pk: client)
    monkeypatch.setattr(mcp_tools, "elicit_email_draft", fake_elicit_email_draft)
    monkeypatch.setattr(mcp_tools, "elicit_confirm", fail_if_confirmed)
    monkeypatch.setattr(
        mcp_tools,
        "apply_optional_status",
        lambda pk, current, status: (current, False),
    )

    result = asyncio.run(
        module.send_email(1, signer_name="Cedric Demo", ctx=SimpleNamespace())
    )

    assert calls.draft == 1
    assert calls.confirm == 0
    assert result["sent"] is True
    assert result["draft"]["subject"] == "Action required"


@pytest.mark.ai
def test_AI_normalize_due_date__coerces_workbook_values_to_iso_dates() -> None:
    """
    Purpose: Verify remediation due dates are normalized to ISO 8601 full-date text at import time.
    Why this matters: Mixed workbook strings break typed contracts, filters, and dashboard display.
    Setup summary: Import the dataset import plan and call `_normalize_due_date` on legacy and ISO inputs.
    """
    import_plan_path = (
        Path(__file__).resolve().parents[3]
        / "datasets"
        / "account_review"
        / "fastmcp"
        / "import_plan.py"
    )
    spec = importlib.util.spec_from_file_location(
        "account_review_import_plan_for_test", import_plan_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._normalize_due_date("2026-08-03") == "2026-08-03"
    assert module._normalize_due_date(None) is None
    assert module._normalize_due_date("—") is None

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        module._normalize_due_date("Escalated 2026-07-14")
