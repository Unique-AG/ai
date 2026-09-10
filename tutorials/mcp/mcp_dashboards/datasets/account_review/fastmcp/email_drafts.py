"""Email draft elicitation helpers for account_review tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context
from pydantic import BaseModel, EmailStr, Field, create_model

import paths as _paths  # noqa: F401
from constants import COMPLIANCE_INBOX
from domain import apply_client_update, client_binding_rows
from generated.models import (
    Audience,
    Client,
    ClientUpdate,
    EmailAddress,
    NewStatus,
    OutboundEmailDraft,
    SendEmailResult,
    Status,
)
from mcp_dashboards.elicitation import elicit_form


def email_str(value: Any) -> str:
    """Plain address text from an EmailAddress RootModel or raw string.

    ``str(EmailAddress(...))`` yields ``root='a@b.com'``, which breaks elicitation
    defaults and confirm copy — always unwrap via ``.root`` first.
    """
    if value is None:
        return ""
    root = getattr(value, "root", None)
    if root is not None:
        return str(root)
    return str(value)


def email_address(value: Any) -> EmailAddress:
    return EmailAddress(root=email_str(value))


def new_status(value: Any) -> NewStatus | None:
    if value is None:
        return None
    if isinstance(value, NewStatus):
        return value
    return NewStatus(str(value))


def normalize_signer_name(signer_name: str) -> str:
    name = signer_name.strip()
    if not name:
        raise ValueError(
            "signer_name is required — pass the logged-in user's display name."
        )
    return name


def default_email_draft(
    client: Client,
    audience: Audience = Audience.client,
    *,
    signer_name: str,
) -> OutboundEmailDraft:
    signer = normalize_signer_name(signer_name)
    issue = client.case_action.open_issue or "account review item"
    title = client.case_action.title or issue
    action = (
        client.case_action.recommended_action
        or "Please contact your relationship manager."
    )
    signature = f"Kind regards,\n{signer}"

    if audience is Audience.compliance:
        return OutboundEmailDraft(
            audience=Audience.compliance,
            to=email_address(COMPLIANCE_INBOX),
            subject=(
                f"Escalation: {client.identity.name} "
                f"({client.identity.reference}) — {title}"
            ),
            body=(
                f"Compliance team,\n\n"
                f"Please review the following client for escalation:\n\n"
                f"- Client: {client.identity.name} (`{client.identity.reference}`)\n"
                f"- Status: {client.case_action.status}\n"
                f"- Rule: {client.case_action.rule_code or '—'}\n"
                f"- Issue: {issue}\n"
                f"- Recommended action: {action}\n"
                f"- Criticality: {client.compliance.criticality}\n"
                f"- Risk: {client.compliance.risk_level}\n\n"
                f"{signature}"
            ),
            # Resolving a screening/regulatory hit by escalating → Escalated.
            new_status=NewStatus.Escalated,
        )

    email = email_str(client.contact.email)
    if not email:
        raise ValueError(
            f"Client {client.identity.name} has no contact email on file; "
            "cannot draft a client email."
        )
    return OutboundEmailDraft(
        audience=Audience.client,
        to=email_address(email),
        subject=f"Action required: {title}",
        body=(
            f"Dear {client.identity.name},\n\n"
            f"We are writing regarding {issue}.\n\n"
            f"{action}\n\n"
            f"{signature}"
        ),
    )


def normalize_audience(audience: Audience | str | None) -> Audience:
    if audience is None:
        return Audience.client
    if isinstance(audience, Audience):
        return audience
    return Audience(str(audience))


def email_draft_elicit_model(
    *,
    proposed: OutboundEmailDraft,
    client: Client,
    audience: Audience,
) -> type[BaseModel]:
    """Elicitation form for email drafts.

    Platform elicitation rejects nullable union types (``Status | None``), so
    ``new_status`` is a plain enum with a concrete default: Escalated for
    Compliance, otherwise the client's current status (accept = no change).
    """
    if proposed.new_status is not None:
        status_default = (
            proposed.new_status
            if isinstance(proposed.new_status, Status)
            else Status(str(proposed.new_status))
        )
    elif audience is Audience.compliance:
        status_default = Status.Escalated
    else:
        current = client.case_action.status
        status_default = (
            current if isinstance(current, Status) else Status(str(current))
        )

    return create_model(
        "EmailDraftForm",
        __base__=BaseModel,
        to=(
            EmailStr,
            Field(
                default=email_str(proposed.to),
                description="Recipient email address.",
            ),
        ),
        subject=(
            str,
            Field(default=proposed.subject, description="Email subject line."),
        ),
        body=(
            str,
            Field(default=proposed.body, description="Email body text."),
        ),
        new_status=(
            Status,
            Field(
                default=status_default,
                description=(
                    "Workflow status to apply after accept. Keep the current status "
                    "for no change; Compliance escalations default to Escalated."
                ),
            ),
        ),
    )


async def elicit_email_draft(
    *,
    ctx: Context,
    client: Client,
    audience: Audience,
    send: bool,
    signer_name: str,
) -> OutboundEmailDraft | None:
    """Elicit an email draft. Returns ``None`` when the user cancels review."""
    proposed = default_email_draft(client, audience, signer_name=signer_name)
    audience_label = "Compliance" if audience is Audience.compliance else "the client"
    verb = "send" if send else "keep as a draft"
    EmailDraftForm = email_draft_elicit_model(
        proposed=proposed, client=client, audience=audience
    )
    accepted = await elicit_form(
        ctx,
        f"Review the {audience.value} email for **{client.identity.name}** "
        f"(`{client.identity.reference}`) to {audience_label}. "
        f"Edit fields as needed, then accept to {verb}."
        + (
            " Sending to Compliance will set status to Escalated unless you change new_status."
            if audience is Audience.compliance
            else ""
        ),
        EmailDraftForm,
    )
    if accepted is None:
        return None
    accepted_data: Any = accepted
    return OutboundEmailDraft(
        audience=audience,
        to=email_address(
            email_str(getattr(accepted_data, "to", None)) or email_str(proposed.to)
        ),
        subject=getattr(accepted_data, "subject", None) or proposed.subject,
        body=getattr(accepted_data, "body", None) or proposed.body,
        new_status=new_status(getattr(accepted_data, "new_status", None)),
    )


def send_email_payload(
    *,
    client: Client,
    draft: OutboundEmailDraft,
    sent: bool,
    status_updated: bool,
    message_id: str | None,
    delivery_message: str,
) -> dict[str, Any]:
    """Build the JSON tool result; always answers whether the mail was sent."""
    result = SendEmailResult(
        client=client,
        draft=draft,
        sent=sent,
        status_updated=status_updated,
        message_id=message_id,
        delivery_message=delivery_message,
    )
    payload = result.model_dump(mode="json")
    payload["client"] = client_binding_rows([client])[0]
    return payload


def apply_optional_status(
    pk: int, client: Client, new_status_value: Any
) -> tuple[Client, bool]:
    if new_status_value is None:
        return client, False
    status_value = (
        new_status_value
        if isinstance(new_status_value, Status)
        else Status(str(new_status_value))
    )
    if status_value == client.case_action.status:
        return client, False
    return apply_client_update(pk, ClientUpdate(status=status_value)), True
