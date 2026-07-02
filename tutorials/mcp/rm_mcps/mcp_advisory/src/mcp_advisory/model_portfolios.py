"""Model Portfolios domain — catalogue (list/get) + per-client recommendation.

Port of the n8n "RM Demo — Model Portfolios" workflow. The catalogue (bank-wide)
lives in `model_catalog` (the list blob) + `model_portfolios` (per-code detail);
the per-client recommendation lives in `model_recommend` (sql/model_portfolios.sql).
"""

import json
from typing import Annotated

from pydantic import Field

from common.db import make_client_tools, query_all, query_one
from common.tool_prompts import tool_meta

_LIST_DESC = (
    "[MDL 1a] Model-portfolio catalogue: code, name, risk band, reference currency, expected "
    "return, volatility, expected max drawdown, rebalancing cadence. No arguments."
)
_GET_DESC = (
    "[MDL 1b] A model portfolio in full: code, name, risk band, reference currency, target "
    "allocation (asset class + weight %), expected return, volatility, expected max drawdown, "
    "rebalancing cadence, eligibility. Input: a model code (CP-1, BI-3, BG-5, GR-7) or name."
)
_RECOMMEND_SPEC = {
    "name": "recommend_model",
    "table": "model_recommend",
    "style": "record",
    "meta": {"unique.app/icon": "wand-sparkles"},
    "description": (
        "[MDL 1c] Recommend a model for a client by mapping their captured risk profile/objective "
        "(CRM mandate) to the model ladder. Returns recommended model code, the model, and a "
        "suitability note. Input: client name or client_id."
    ),
}


def register(mcp) -> None:
    @mcp.tool(
        name="list_model_portfolios",
        title="List Model Portfolios",
        description=_LIST_DESC,
        meta=tool_meta("list_model_portfolios", {"unique.app/icon": "list"}),
    )
    def list_model_portfolios() -> str:
        row = query_one("SELECT data FROM model_catalog WHERE id = 1")
        return json.dumps(row["data"] if row else {"count": 0, "models": []})

    @mcp.tool(
        name="get_model_portfolio",
        title="Get Model Portfolio",
        description=_GET_DESC,
        meta=tool_meta("get_model_portfolio", {"unique.app/icon": "file-chart-column"}),
    )
    def get_model_portfolio(
        input: Annotated[str, Field(description="Model code (CP-1, BI-3, BG-5, GR-7) or name.")] = "",
        code: Annotated[str, Field(description="Model code (alternative to input).")] = "",
        model: Annotated[str, Field(description="Model name (alternative to input).")] = "",
    ) -> str:
        raw = (input or code or model or "").strip()
        rows = query_all("SELECT code, data FROM model_portfolios ORDER BY code")
        if not raw:
            return json.dumps({"error": "Provide a model code or name.",
                               "available": [r["code"] for r in rows]})
        up, low = raw.upper(), raw.lower()
        hit = next((r for r in rows if r["code"].upper() == up), None)
        if hit is None:
            hit = next((r for r in rows
                        if low in str(r["data"].get("name", "")).lower()
                        or low in str(r["data"].get("code", "")).lower()), None)
        if hit is None:
            return json.dumps({"error": "Unknown model.",
                               "available": [r["code"] for r in rows]})
        return json.dumps(hit["data"])

    make_client_tools(mcp, [_RECOMMEND_SPEC])
