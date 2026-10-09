"""Lombard Coverage domain — pre-computed facility coverage scenarios.

Port of the n8n "RM Demo — Lombard Coverage" workflow. Static, read-only demo
data covering one facility (Markus Brunner, party 50318) across five restoration
scenarios (sql/lombard.sql). The party/scenario fuzzy-resolution mirrors n8n.
"""

import json
from typing import Annotated

from pydantic import Field

from common.db import query_one
from common.tool_prompts import tool_meta

# Markus is keyed 50318 in the coverage store; bridge the ids/names the agent may pass.
PARTY_ALIASES = {
    "50318": "50318",
    "ch-pb-0049217": "50318",
    "lmb 50318.001.0001": "50318",
    "markus": "50318",
    "brunner": "50318",
    "markus brunner": "50318",
    "markus andreas brunner": "50318",
}
SCENARIOS = ["baseline", "cash_topup_100k", "partial_repay_200k", "trim_collateral_200k", "hold"]

_DESC = (
    "[Lombard] Static, pre-computed Lombard-facility coverage projection under a named restoration "
    "scenario. Read-only — never books a trade or moves cash. Returns baseline vs projected "
    "coverage %, band (margin/warning/safe), headroom, narrative, compliance notes and the option "
    "menu. Demo data covers client_id 50318 (Markus Brunner). scenario_id: baseline | "
    "cash_topup_100k | partial_repay_200k | trim_collateral_200k | hold."
)


def _resolve_party(v: str) -> str:
    s = str(v or "").strip().lower()
    if s in PARTY_ALIASES:
        return PARTY_ALIASES[s]
    if "50318" in s:
        return "50318"
    hit = next((k for k in PARTY_ALIASES if len(k) > 3 and k in s), None)
    return PARTY_ALIASES[hit] if hit else ""


def _resolve_scenario(v: str) -> str:
    s = str(v or "").strip().lower().replace(" ", "_").replace("-", "_")
    if s in SCENARIOS:
        return s
    if "top" in s or "cash" in s:
        return "cash_topup_100k"
    if "repay" in s:
        return "partial_repay_200k"
    if "trim" in s or "collateral" in s or "concentr" in s:
        return "trim_collateral_200k"
    if "hold" in s or "monitor" in s or "noaction" in s or "no_action" in s:
        return "hold"
    return ""


def register(mcp) -> None:
    @mcp.tool(
        name="get_coverage_scenario",
        title="Get Lombard Coverage Scenario",
        description=_DESC,
        meta=tool_meta("get_coverage_scenario", {"unique.app/icon": "scale-balanced"}),
    )
    def get_coverage_scenario(
        client_id: Annotated[str, Field(description="Client id / name / facility id.")] = "",
        scenario_id: Annotated[str, Field(description="One of: baseline | cash_topup_100k | "
                                          "partial_repay_200k | trim_collateral_200k | hold.")] = "baseline",
        client: Annotated[str, Field(description="Client name (alternative to client_id).")] = "",
        reporting_ccy: Annotated[str, Field(description="Reporting currency override (echoed only).")] = "",
        as_of: Annotated[str, Field(description="As-of timestamp override (echoed only).")] = "",
    ) -> str:
        # A non-empty client that doesn't resolve is an error — don't silently serve
        # Markus Brunner's record. Empty/omitted input defaults to the only demo party.
        raw = str(client_id or client or "").strip()
        party = _resolve_party(raw)
        if raw and not party:
            return json.dumps({"error": f"Unknown client '{raw}'. Demo data covers client_id "
                               "50318 (Markus Brunner).", "available_parties": [50318]})
        party = party or "50318"
        scen = _resolve_scenario(scenario_id)
        if scen == "":
            return json.dumps({"error": "Unknown scenario_id. Use one of: " + " | ".join(SCENARIOS) + ".",
                               "client_id": int(party)})
        row = query_one(
            "SELECT data FROM lombard_coverage WHERE party = %s AND scenario_id = %s", (party, scen)
        )
        if row is None:
            return json.dumps({"error": f"No coverage record for {party}::{scen}. "
                               f"Demo data covers client_id 50318 (Markus Brunner).",
                               "available_parties": [50318]})
        out = dict(row["data"])
        if as_of:
            out["as_of"] = str(as_of)
        if reporting_ccy:
            out["reporting_ccy"] = str(reporting_ccy).upper()
            if out["reporting_ccy"] != "CHF":
                out["fx_note"] = ("Reporting currency override echoed only — demo figures remain "
                                  "CHF (no FX applied).")
        return json.dumps(out)
