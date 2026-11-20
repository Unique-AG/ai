"""Shared constants for the account_review FastMCP app."""

from __future__ import annotations

import logging
from typing import Literal

import paths as _paths  # noqa: F401
from generated.models import Status

logger = logging.getLogger("account_review_mcp")

MAX_PAGE_SIZE = 500

ESCALATION_STATUSES = {
    Status.Escalated.value,
    Status.Screening_hit.value,
    Status.Regulatory_breach.value,
    Status.Regulatory_change.value,
}
BREACH_STATUS = Status.Limit_exceeded.value
DEADLINE_STATUS = Status.Deadline_approaching.value
COMPLIANT_STATUS = Status.Compliant.value
ESCALATED_STATUS = Status.Escalated.value
# Attention rail: open work only — Compliant is cleared, Escalated is with Compliance.
ATTENTION_EXCLUDED_STATUSES = {COMPLIANT_STATUS, ESCALATED_STATUS}
# Compliance escalation inbox (demo send is simulated; no real SMTP).
COMPLIANCE_INBOX = "compliance@unique.ai"

# Storage is split across domain tables; the repository JOIN projects flat
# aliases (`identity_name`, `case_action_status`, …). These four short names are
# the filter/update aliases the dashboard sends.
FILTER_ALIASES: dict[str, str] = {
    "status": "case_action.status",
    "risk_level": "compliance.risk_level",
    "segment": "identity.segment",
    "criticality": "compliance.criticality",
}
CountColumn = Literal[
    "case_action.status",
    "compliance.risk_level",
    "compliance.criticality",
    "identity.segment",
    "identity.type",
    "compliance.mandate_type",
]
SEARCH_COLUMNS = [
    "identity_name",
    "identity_reference",
    "case_action_open_issue",
    "case_action_recommended_action",
]
