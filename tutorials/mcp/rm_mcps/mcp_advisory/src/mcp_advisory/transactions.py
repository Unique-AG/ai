"""Transactions domain — corporate actions / elections / orders / tax lots / monitoring.

Port of the n8n "RM Demo — Transactions" workflow. Data from sql/transactions.sql.
"""

from common.db import make_client_tools

SPECS = [
    {
        "name": "get_corporate_actions",
        "table": "corporate_actions",
        "style": "list",
        "field": "items",
        "meta": {"unique.app/icon": "calendar-clock"},
        "description": (
            "[T&T 7a] Corporate actions: event type, affected security, terms, key dates, "
            "mandatory/voluntary, election options, per-client entitlement. Input: client name "
            "or client_id."
        ),
    },
    {
        "name": "get_elections",
        "table": "elections",
        "style": "list",
        "field": "items",
        "meta": {"unique.app/icon": "check-square"},
        "description": (
            "[T&T 7b] Elections/instructions: captured client election, validation status, "
            "internal cut-off vs market deadline, capture timestamp & channel. Input: client "
            "name or client_id."
        ),
    },
    {
        "name": "get_orders",
        "table": "orders",
        "style": "list",
        "field": "items",
        "meta": {"unique.app/icon": "receipt"},
        "description": (
            "[T&T 7c] Orders/trades: proposed/actual order, estimated cost/price, pre-trade "
            "compliance result, execution status. Input: client name or client_id."
        ),
    },
    {
        "name": "get_tax_lots",
        "table": "tax_lots",
        "style": "record",
        "meta": {"unique.app/icon": "calculator"},
        "description": (
            "[T&T 7d] Tax-lot & cost: tax lots (date/cost/qty), unrealised gain/loss, estimated "
            "transaction cost, estimated tax impact. Input: client name or client_id."
        ),
    },
    {
        "name": "get_transaction_monitoring",
        "table": "transaction_monitoring",
        "style": "record",
        "meta": {"unique.app/icon": "shield-check"},
        "description": (
            "[T&T 7e] Transaction monitoring: actual activity summary, expected activity profile, "
            "anomaly/deviation flags. Input: client name or client_id."
        ),
    },
]


def register(mcp) -> None:
    make_client_tools(mcp, SPECS)
