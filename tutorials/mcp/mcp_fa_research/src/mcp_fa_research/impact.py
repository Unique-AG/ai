"""impact.py — normalized OVERNIGHT EVENT IMPACT (old → new → Δ per event).

Single source for the three surfaces that show "what changed because of tonight's
events, keeping the previous values":
  · overnight-impact.html   (canvases.py — the desk-level impact report canvas)
  · the models' Summary     (models.py — 'Event impact' block, OLD kept next to NEW)
  · the impact PDF          (sandbox build_impact_pdf.py)

For each seed.OVERNIGHT event: severity/headline/name chip + diff rows
[{metric, old, new, delta}]. LVMH pulls the full NEW/OLD/Δ estimate table from
note_pack.forecast_changes; names with a revised TP get the TP bridge row; watch/
info items state explicitly that estimates are unchanged (early-warning stage).
SYNTHETIC — DEMO USE ONLY.
"""

from __future__ import annotations

import note_pack
import seed

_CCY = {"EUR": "€", "CHF": "CHF "}


def _fmt(v, ccy):
    return f"{_CCY.get(ccy, '')}{v:,.0f}"


def events() -> list[dict]:
    out = []
    ov_map = seed.current_overnight()
    coverage = seed.current_coverage()
    keys = [k for k in seed.OVERNIGHT_ORDER if k in ov_map]
    keys += [k for k in ov_map if k not in keys]
    for key in keys:
        ov = ov_map[key]
        cov = next((c for c in coverage if c["ticker"] == key), None)
        rows: list[dict] = []
        if cov and ov.get("new_target_price"):
            old, new = cov["target_price"], ov["new_target_price"]
            rows.append({"metric": "12m target price",
                         "old": _fmt(old, cov["ccy"]), "new": _fmt(new, cov["ccy"]),
                         "delta": f"{new / old - 1:+.1%}"})
        if key == "MC FP":
            fc = note_pack._MC_FP["forecast_changes"]
            for r in fc["rows"]:
                if r[0] in ("Rec. EBIT (rep.)", "EPS (€)", "Revenue (EURm)"):
                    rows.append({"metric": f"{r[0]} 2026e",
                                 "old": r[2], "new": r[1], "delta": r[3]})
        status = {
            "alert": "Model, note and buy-side pack updated overnight — post-view in control.",
            "positive": "Estimates under review — upside; raise via the financial model.",
            "watch": "No estimate change yet — early-warning stage.",
            "info": "Informational — no impact on estimates or target price.",
        }[ov["severity"]]
        name_label = ("European Luxury · all covered names" if key == "SECTOR"
                      else f"{ov['name']} · {key}")
        out.append({
            "key": key, "name_label": name_label, "severity": ov["severity"],
            "severity_label": {"alert": "ALERT", "positive": "UPSIDE",
                               "watch": "WATCH", "info": "NOTE"}[ov["severity"]],
            "headline": ov["headline"], "detail": ov["detail"],
            "valuation_impact": ov["valuation_impact"],
            "rows": rows, "status": status,
            "no_change": not rows,
        })
    return out
