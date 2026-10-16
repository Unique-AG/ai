"""House Views domain — CIO house view / themes / tactical calls (bank-wide).

Port of the n8n "RM Demo — House Views" workflow. Same three tool names,
descriptions and output shapes; data lives in Postgres (sql/house_views.sql:
house_view_meta / house_view / cio_themes / tactical_calls) and is read via the
shared common.db helpers — like every other domain.
"""

import json
from typing import Annotated

from pydantic import Field

from common.db import query_all, query_one
from common.tool_prompts import tool_meta

HOUSE_VIEW_DESCRIPTION = (
    "[HV 1a] CIO house view: per-asset-class stance (Overweight/Neutral/Underweight/Selective), "
    "conviction score, rationale, as-of and valid-until. Bank-wide (not per client). Call with no "
    "arguments for the full view, or pass an asset class (equities, fixed income, alternatives, "
    "fx, cash) to filter."
)
CIO_THEMES_DESCRIPTION = (
    "[HV 1b] CIO investment themes / convictions: theme, horizon, conviction, rationale. Bank-wide. "
    "No arguments."
)
TACTICAL_CALLS_DESCRIPTION = (
    "[HV 1c] Tactical allocation calls: dimension, call (over/under-weight/hedge), detail, "
    "magnitude, conviction, rationale. Bank-wide. No arguments."
)


def _meta() -> dict:
    row = query_one(
        "SELECT house, to_char(as_of, 'YYYY-MM-DD') AS as_of, "
        "to_char(valid_until, 'YYYY-MM-DD') AS valid_until FROM house_view_meta WHERE id = 1"
    )
    return row or {"house": "ABC Wealth Management — CIO Office", "as_of": "", "valid_until": ""}


def _house_view(arg: str) -> dict:
    arg = str(arg or "all").strip().lower()
    meta = _meta()
    views = query_all("SELECT asset_class, stance, score AS conviction, rationale "
                      "FROM house_view ORDER BY position")
    if arg in ("", "all", "current", "house", "house view"):
        return {"house": meta["house"], "as_of": meta["as_of"],
                "valid_until": meta["valid_until"], "count": len(views), "views": views}

    def matches(v: dict) -> bool:
        a = v["asset_class"].lower()
        return (a in arg or arg in a
                or (arg == "bonds" and "fixed" in a)
                or (arg == "equity" and "equit" in a)
                or (arg == "alts" and "altern" in a))

    hit = next((v for v in views if matches(v)), None)
    if hit:
        return {"house": meta["house"], "as_of": meta["as_of"],
                "valid_until": meta["valid_until"], **hit}
    return {"error": "Unknown asset class.", "available": [v["asset_class"] for v in views]}


def _cio_themes() -> dict:
    meta = _meta()
    themes = query_all("SELECT theme, horizon, conviction, rationale FROM cio_themes ORDER BY position")
    return {"house": meta["house"], "as_of": meta["as_of"], "valid_until": meta["valid_until"],
            "count": len(themes), "themes": themes}


def _tactical_calls() -> dict:
    meta = _meta()
    calls = query_all('SELECT dimension, "call", detail, magnitude, conviction, rationale '
                      "FROM tactical_calls ORDER BY position")
    return {"house": meta["house"], "as_of": meta["as_of"], "valid_until": meta["valid_until"],
            "count": len(calls), "calls": calls}


def register(mcp) -> None:
    @mcp.tool(name="get_house_view", title="Get House View",
              description=HOUSE_VIEW_DESCRIPTION,
              meta=tool_meta("get_house_view", {"unique.app/icon": "compass"}))
    def get_house_view(
        asset_class: Annotated[str, Field(description="Omit for the full house view, or pass an asset "
                                          "class to filter: equities / fixed income / alternatives / "
                                          "fx / cash.")] = "",
    ) -> str:
        return json.dumps(_house_view(asset_class))

    @mcp.tool(name="get_cio_themes", title="Get CIO Themes",
              description=CIO_THEMES_DESCRIPTION,
              meta=tool_meta("get_cio_themes", {"unique.app/icon": "lightbulb"}))
    def get_cio_themes() -> str:
        return json.dumps(_cio_themes())

    @mcp.tool(name="get_tactical_calls", title="Get Tactical Calls",
              description=TACTICAL_CALLS_DESCRIPTION,
              meta=tool_meta("get_tactical_calls", {"unique.app/icon": "target"}))
    def get_tactical_calls() -> str:
        return json.dumps(_tactical_calls())
