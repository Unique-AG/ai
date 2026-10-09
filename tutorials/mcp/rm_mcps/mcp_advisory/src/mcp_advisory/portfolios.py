"""Portfolios domain — holdings / performance / risk / transactions / attribution.

Port of the n8n "RM Demo — Portfolios" workflow. Same tool names, descriptions
and output shapes; data is read from Postgres (sql/portfolios.sql) keyed by
client_id instead of inline JS.
"""

from common.db import make_client_tools

SPECS = [
    {
        "name": "get_holdings",
        "table": "holdings",
        "style": "record",
        "meta": {"unique.app/icon": "briefcase"},
        "description": (
            "[PMS 2a] Holdings: account ID, instruments (ISIN/ticker), asset class & sub-class, "
            "quantity/nominal, market value + currency, cost basis, weight %, as-of timestamp; "
            "plus held-away assets. Input: client name or client_id."
        ),
    },
    {
        "name": "get_performance",
        "table": "performance",
        "style": "record",
        "meta": {"unique.app/icon": "chart-line"},
        "description": (
            "[PMS 2c] Performance: period returns gross & net (MTD/QTD/YTD), since-inception/"
            "annualised, benchmark, relative (excess) return, TWR/MWR basis. Input: client name "
            "or client_id."
        ),
    },
    {
        "name": "get_portfolio_transactions",
        "table": "portfolio_transactions",
        "style": "list",
        "field": "items",
        "meta": {"unique.app/icon": "arrow-right-arrow-left"},
        "description": (
            "[PMS 2b] Settled transactions: trade & settlement date, type, instrument+qty+price, "
            "gross/net amount, counterparty, status. Input: client name or client_id."
        ),
    },
    {
        "name": "get_attribution",
        "table": "attribution",
        "style": "record",
        "meta": {"unique.app/icon": "chart-pie"},
        "description": (
            "[PMS 2d] Attribution: contribution by position & asset class, allocation/selection/"
            "currency effects, top contributors/detractors. Input: client name or client_id."
        ),
    },
    {
        "name": "get_risk_exposure",
        "table": "risk_exposure",
        "style": "record",
        "meta": {"unique.app/icon": "gauge"},
        "description": (
            "[PMS 2e] Risk/exposure: asset allocation actual vs target, currency exposure, "
            "concentration, liquidity profile. Input: client name or client_id."
        ),
    },
]


def register(mcp) -> None:
    make_client_tools(mcp, SPECS)
