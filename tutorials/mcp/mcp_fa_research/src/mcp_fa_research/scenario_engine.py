"""scenario_engine.py — the parameterized what-if engine behind the buy-side scenario beat.

``compute_scenario(ticker, fx_eur_move_pct, china_recovery, destocking_end)`` COMPUTES
the impact cascade the analyst would model — revenue → recurring EBIT → EPS by year →
target-price bridge → rating read — from per-name exposure parameters, instead of only
serving canned rows. Calibrated so the seeded hypotheses (seed.SCENARIOS, the note and
the dashboards) are reproduced exactly:

  MC FP  fx +5%              → EPS 26e −3.5% · TP €615 → €595
  MC FP  china q2_26         → EPS 26e +4.0% · TP €615 → €650
  MC FP  destocking fy27     → EPS 26e −5.0% · TP €615 → €580

ALL VALUES ARE SYNTHETIC — DEMO USE ONLY. The model is deliberately transparent (the
``assumption_trail`` lists every parameter used) — that is the demo point: hypotheses
are the analyst's, arithmetic is the machine's.
"""

from __future__ import annotations

import seed

# ---------------------------------------------------------------------------
# Per-name exposure parameters (synthetic, coherent with each name's story)
# fx: share of revenue in non-reporting currencies, EPS beta to a revenue FX move,
#     hedge cover by forecast year (transaction hedges roll off).
# china: EPS beta to the China demand schedule (Swatch = the high-beta name).
# ---------------------------------------------------------------------------
EXPOSURES: dict[str, dict] = {
    "MC FP":   {"nonccy": 0.70, "eps_beta": 1.43, "hedge": [0.30, 0.10, 0.00],
                "china_beta": 1.0, "fx_label": "EUR vs USD & Asia basket",
                "mix_note": "USD 27% / Asia ccys 28% / other 15% of sales; EUR cost base"},
    "KER FP":  {"nonccy": 0.65, "eps_beta": 1.80, "hedge": [0.30, 0.10, 0.00],
                "china_beta": 1.2, "fx_label": "EUR vs USD & Asia basket",
                "mix_note": "aspirational mix amplifies the drop-through (thin margins)"},
    "RMS FP":  {"nonccy": 0.78, "eps_beta": 1.30, "hedge": [0.45, 0.15, 0.00],
                "china_beta": 0.5, "fx_label": "EUR vs USD & Asia basket",
                "mix_note": "production 100% France; pricing power offsets part of the move"},
    "CFR SW":  {"nonccy": 0.92, "eps_beta": 1.60, "hedge": [0.35, 0.10, 0.00],
                "china_beta": 0.8, "fx_label": "CHF vs revenue basket",
                "mix_note": "CHF reporter with ~92% of sales outside CHF — franc strength "
                            "is the perennial drag"},
    "MONC IM": {"nonccy": 0.55, "eps_beta": 1.35, "hedge": [0.30, 0.10, 0.00],
                "china_beta": 1.0, "fx_label": "EUR vs USD & Asia basket",
                "mix_note": "EUR reporter, DTC mix; moderate exposure"},
    "UHR SW":  {"nonccy": 0.90, "eps_beta": 2.50, "hedge": [0.15, 0.05, 0.00],
                "china_beta": 2.5, "fx_label": "CHF vs revenue basket",
                "mix_note": "thin margins + low hedging = the sector's highest FX and "
                            "China gearing"},
}

# China demand schedules: EPS uplift (%) per forecast year at china_beta = 1.0
CHINA_SCHEDULES: dict[str, list[float]] = {
    "none":   [0.0, 0.0, 0.0],
    "q2_26":  [4.0, 4.5, 4.5],
    "q4_26":  [2.0, 4.0, 4.5],
    "fy27":   [0.0, 3.5, 4.0],
}
# TP reacts MORE than EPS on a China inflection (part of the discount closes)
CHINA_TP_MULT = 1.4

# Cognac destocking schedules (MC FP only): EPS impact (%) per forecast year
DESTOCKING_SCHEDULES: dict[str, list[float]] = {
    "h1_26":  [0.0, 0.0, 0.0],      # base case — already in the numbers
    "h2_26":  [-2.0, -1.0, 0.0],
    "fy27":   [-5.0, -3.0, -1.0],
}
DESTOCK_TP_MULT = 1.15              # de-rating risk premium on a second reset
FX_TP_MULT = 0.95                   # PPP mean-reversion in the terminal value

YEARS = ["FY2026e", "FY2027e", "FY2028e"]
BASE_EPS: dict[str, list[float]] = {   # per-name base EPS path (= chart_pack)
    "MC FP": [21.6, 23.9, 26.1], "KER FP": [16.9, 18.6, 20.5],
    "RMS FP": [52.8, 58.3, 64.1], "CFR SW": [6.7, 7.3, 7.9],
    "MONC IM": [2.62, 2.81, 3.02], "UHR SW": [10.3, 12.1, 13.9],
}


def _base_tp(tk: str) -> float:
    ov = seed.OVERNIGHT.get(tk) or {}
    row = next(c for c in seed.COVERAGE if c["ticker"] == tk)
    return float(ov.get("new_target_price") or row["target_price"])


def _round5(v: float) -> float:
    return round(v / 5.0) * 5.0


def compute(ticker: str, fx_eur_move_pct: float = 0.0,
            china_recovery: str = "none", destocking_end: str = "h1_26") -> dict:
    tk = seed.resolve(ticker)
    if not tk:
        return {"error": f"unknown name {ticker!r}"}
    if china_recovery not in CHINA_SCHEDULES:
        return {"error": f"china_recovery must be one of {sorted(CHINA_SCHEDULES)}"}
    if destocking_end not in DESTOCKING_SCHEDULES:
        return {"error": f"destocking_end must be one of {sorted(DESTOCKING_SCHEDULES)}"}
    if abs(fx_eur_move_pct) > 15:
        return {"error": "fx_eur_move_pct outside the sane range (±15)"}
    exp = EXPOSURES[tk]
    row = next(c for c in seed.COVERAGE if c["ticker"] == tk)
    ccy_sym = {"EUR": "€", "CHF": "CHF ", "USD": "$"}.get(row["ccy"], "")
    base_tp = _base_tp(tk)
    base_eps = BASE_EPS[tk]

    # --- the cascade, per axis, per year ------------------------------------
    fx_rev = [-fx_eur_move_pct * exp["nonccy"]] * 3                       # translation
    fx_eps = [-fx_eur_move_pct * exp["nonccy"] * exp["eps_beta"] * (1 - h)
              for h in exp["hedge"]]                                      # + transaction, net of hedges
    china_eps = [u * exp["china_beta"] for u in CHINA_SCHEDULES[china_recovery]]
    destock_eps = (DESTOCKING_SCHEDULES[destocking_end]
                   if tk == "MC FP" else [0.0, 0.0, 0.0])

    eps_delta = [fx_eps[i] + china_eps[i] + destock_eps[i] for i in range(3)]
    rev_delta = [fx_rev[i] + china_eps[i] * 0.55 + destock_eps[i] * 0.45 for i in range(3)]
    ebit_delta = [eps_delta[i] * 0.90 for i in range(3)]
    eps_new = [base_eps[i] * (1 + eps_delta[i] / 100) for i in range(3)]

    # --- target-price bridge -------------------------------------------------
    tp_delta = (fx_eps[0] * FX_TP_MULT
                + (china_eps[0] + china_eps[1]) / 2 * CHINA_TP_MULT
                + destock_eps[0] * DESTOCK_TP_MULT)
    new_tp = _round5(base_tp * (1 + tp_delta / 100))
    price = row["price"]
    upside = (new_tp / price - 1) * 100

    # --- narrative bits -------------------------------------------------------
    parts = []
    if fx_eur_move_pct:
        parts.append(f"{exp['fx_label']} {fx_eur_move_pct:+.1f}%")
    if china_recovery != "none":
        parts.append(f"China recovery from {china_recovery.replace('_', '-').upper()}")
    if destocking_end != "h1_26" and tk == "MC FP":
        parts.append(f"cognac destocking ends {destocking_end.replace('_', '-').upper()}")
    label = " + ".join(parts) if parts else "base case (no shock)"

    trail = [f"Revenue currency mix: non-{row['ccy']} share {exp['nonccy']:.0%} — {exp['mix_note']}",
             f"EPS beta to a revenue FX move: {exp['eps_beta']:.2f}× (cost-base mismatch)",
             f"Hedge cover rolls off: {exp['hedge'][0]:.0%} FY26e → {exp['hedge'][1]:.0%} "
             f"FY27e → {exp['hedge'][2]:.0%} FY28e (translation is never hedged)",
             f"China gearing: {exp['china_beta']:.1f}× the sector demand schedule",
             "TP bridge: FX carries PPP mean-reversion in the terminal value (0.95×); a "
             "China inflection closes part of the discount (1.4×); a second cognac reset "
             "adds a de-rating premium (1.15×)"]

    def pct(v):
        return f"{v:+.1f}%" if abs(v) >= 0.05 else "—"

    table = {"header": ["vs base case", *YEARS],
             "rows": [["Revenue", *[pct(v) for v in rev_delta]],
                      ["Rec. EBIT", *[pct(v) for v in ebit_delta]],
                      ["EPS", *[pct(v) for v in eps_delta]],
                      [f"EPS, new ({row['ccy']})", *[f"{v:,.2f}" for v in eps_new]]]}

    rating = row["rating"]
    rating_note = (f"{rating} retained — the shock moves the numbers, not the thesis."
                   if abs(tp_delta) < 8 else
                   f"{rating} under review — a move of this size would trigger a formal "
                   f"rating committee discussion.")

    return {
        "ticker": tk, "name": row["name"], "scenario_label": label,
        "inputs": {"fx_eur_move_pct": fx_eur_move_pct, "china_recovery": china_recovery,
                   "destocking_end": destocking_end},
        "base": {"tp_label": f"{ccy_sym}{base_tp:,.0f}", "eps": dict(zip(YEARS, base_eps)),
                 "price_label": f"{ccy_sym}{price:,.0f}"},
        "table": table,
        "tp": {"old_label": f"{ccy_sym}{base_tp:,.0f}", "new_label": f"{ccy_sym}{new_tp:,.0f}",
               "delta_label": pct(tp_delta), "upside_label": f"{upside:+.1f}% vs last close"},
        "rating_note": rating_note,
        "assumption_trail": trail,
        "summary": (f"{row['name']} ({tk}) — {label}: EPS {pct(eps_delta[0])} FY26e / "
                    f"{pct(eps_delta[1])} FY27e; TP {ccy_sym}{base_tp:,.0f} → "
                    f"{ccy_sym}{new_tp:,.0f} ({pct(tp_delta)}); {rating_note}"),
        "note": "SYNTHETIC demo engine — analyst hypotheses (exposures, betas, schedules) "
                "with machine-computed arithmetic. Cross-check: seeded hypothesis cases in "
                "get_scenarios are reproduced by this engine.",
    }


def fx_grid(ticker: str, moves=(-5.0, -2.5, 2.5, 5.0)) -> dict:
    """The buy-side anticipation grid: FX move → EPS 26e/27e + TP, one row per move."""
    tk = seed.resolve(ticker)
    rows = []
    for m in moves:
        r = compute(tk, fx_eur_move_pct=m)
        rows.append([f"{m:+.1f}%", r["table"]["rows"][2][1], r["table"]["rows"][2][2],
                     r["tp"]["new_label"], r["tp"]["delta_label"]])
    exp = EXPOSURES[tk]
    return {"title": f"FX sensitivity — {exp['fx_label']}",
            "header": ["FX move", "EPS 26e", "EPS 27e", "Target price", "TP Δ"],
            "rows": rows}


def china_grid(ticker: str) -> dict:
    tk = seed.resolve(ticker)
    rows = []
    for timing, lbl in (("q2_26", "Recovery from Q2-26"), ("q4_26", "Recovery from Q4-26"),
                        ("fy27", "Recovery only in FY27"), ("none", "No recovery (base)")):
        r = compute(tk, china_recovery=timing)
        rows.append([lbl, r["table"]["rows"][2][1], r["table"]["rows"][2][2],
                     r["tp"]["new_label"], r["tp"]["delta_label"]])
    return {"title": "China recovery timing",
            "header": ["Scenario", "EPS 26e", "EPS 27e", "Target price", "TP Δ"],
            "rows": rows}


def combined_matrix(ticker: str) -> dict:
    """FX × China matrix of target prices — the one-glance anticipation table."""
    tk = seed.resolve(ticker)
    fx_moves = (-5.0, -2.5, 0.0, 2.5, 5.0)
    timings = (("none", "No China recovery"), ("q4_26", "China from Q4-26"),
               ("q2_26", "China from Q2-26"))
    rows = []
    for timing, lbl in timings:
        row = [lbl]
        for m in fx_moves:
            r = compute(tk, fx_eur_move_pct=m, china_recovery=timing)
            row.append(r["tp"]["new_label"])
        rows.append(row)
    return {"title": "Target price — FX move × China timing",
            "header": ["", *[f"FX {m:+.1f}%" for m in fx_moves]],
            "rows": rows}


# ---------------------------------------------------------------------------
# Scenario board — display-ready presets + grids for the Scenario Lab canvas
# (script-free: rows are DICTS with formatted fields, payloads server-prepared)
# ---------------------------------------------------------------------------
PRESETS: list[dict] = [
    {"key": "base", "title": "Base case — trough and stabilise",
     "args": {}, "tag": "BASE · 55%"},
    {"key": "fx_up5", "title": "Currency shock — EUR +5%",
     "args": {"fx_eur_move_pct": 5.0}, "tag": "FX"},
    {"key": "fx_dn5", "title": "Currency tailwind — EUR −5%",
     "args": {"fx_eur_move_pct": -5.0}, "tag": "FX"},
    {"key": "china_q2", "title": "China recovery from Q2-26",
     "args": {"china_recovery": "q2_26"}, "tag": "DEMAND"},
    {"key": "china_q4", "title": "China recovery from Q4-26",
     "args": {"china_recovery": "q4_26"}, "tag": "DEMAND"},
    {"key": "destock_h2", "title": "Destocking slips to H2-26",
     "args": {"destocking_end": "h2_26"}, "tag": "COGNAC"},
    {"key": "destock_fy27", "title": "Destocking extends into FY27",
     "args": {"destocking_end": "fy27"}, "tag": "COGNAC"},
    {"key": "bull", "title": "Bull — EUR −2.5% + China Q2-26",
     "args": {"fx_eur_move_pct": -2.5, "china_recovery": "q2_26"}, "tag": "COMBINED"},
    {"key": "bear", "title": "Bear — EUR +5% + destocking FY27",
     "args": {"fx_eur_move_pct": 5.0, "destocking_end": "fy27"}, "tag": "COMBINED"},
]


def board(ticker: str) -> dict:
    tk = seed.resolve(ticker)
    if not tk:
        return {"error": f"unknown name {ticker!r}"}
    row = next(c for c in seed.COVERAGE if c["ticker"] == tk)
    presets = []
    for p in PRESETS:
        if "destocking_end" in p["args"] and tk != "MC FP":
            continue
        r = compute(tk, **p["args"])
        eps = r["table"]["rows"][2]  # ["EPS", 26e, 27e, 28e]
        tp_move = abs(float(r["tp"]["delta_label"].replace("%", "").replace("—", "0") or 0))
        d = ("flat" if r["tp"]["delta_label"] == "—"
             else ("up" if r["tp"]["delta_label"].startswith("+") else "dn"))
        presets.append({
            "key": p["key"], "title": p["title"], "tag": p["tag"],
            "scenario_label": r["scenario_label"],
            "eps26_label": eps[1], "eps27_label": eps[2], "eps28_label": eps[3],
            "tp_arrow": f"{r['tp']['old_label']} → {r['tp']['new_label']}",
            "tp_delta_label": r["tp"]["delta_label"],
            "upside_label": r["tp"]["upside_label"],
            "rating_note": r["rating_note"], "dir": d,
            "big_move": tp_move >= 8.0,
            "explain_payload": __import__("json").dumps({
                "prompt": f"Run compute_scenario on {row['name']} ({tk}) with "
                          f"{p['args'] or 'the base case (no shock)'} and walk me through "
                          "the full cascade — revenue, EBIT and EPS by year, the "
                          "target-price bridge and every assumption used."}),
        })
    fx = fx_grid(tk)
    cn = china_grid(tk)
    mx = combined_matrix(tk)
    fx_rows = [{"move": r[0], "eps26": r[1], "eps27": r[2], "tp": r[3], "tpd": r[4],
                "dir": "dn" if r[4].startswith("-") else "up"} for r in fx["rows"]]
    cn_rows = [{"scenario": r[0], "eps26": r[1], "eps27": r[2], "tp": r[3], "tpd": r[4],
                "dir": "flat" if r[4] == "—" else ("dn" if r[4].startswith("-") else "up")}
               for r in cn["rows"]]
    mx_rows = [{"scenario": r[0], "m1": r[1], "m2": r[2], "m3": r[3], "m4": r[4], "m5": r[5]}
               for r in mx["rows"]]
    exp = EXPOSURES[tk]
    return {
        "ticker": tk, "name": row["name"], "as_of": seed.AS_OF,
        "base_tp_label": f"{ {'EUR': '€', 'CHF': 'CHF '}.get(row['ccy'], '') }{_base_tp(tk):,.0f}",
        "presets": presets,
        "fx_title": fx["title"], "fx_rows": fx_rows,
        "china_rows": cn_rows,
        "matrix_header": mx["header"], "matrix_rows": mx_rows,
        "trail": compute(tk, fx_eur_move_pct=5.0)["assumption_trail"],
        "exposure_note": exp["mix_note"],
        "note": "SYNTHETIC demo — every figure computed by the scenario engine at call time.",
    }


if __name__ == "__main__":  # calibration self-check against the seeded hypotheses
    r = compute("MC FP", fx_eur_move_pct=5.0)
    assert r["table"]["rows"][2][1] == "-3.5%" and r["tp"]["new_label"] == "€595", r["summary"]
    r = compute("MC FP", china_recovery="q2_26")
    assert r["table"]["rows"][2][1] == "+4.0%" and r["tp"]["new_label"] == "€650", r["summary"]
    r = compute("MC FP", destocking_end="fy27")
    assert r["table"]["rows"][2][1] == "-5.0%" and r["tp"]["new_label"] == "€580", r["summary"]
    print("calibration OK — engine reproduces the three seeded hypothesis cases")
    print(compute("UHR SW", china_recovery="q2_26")["summary"])
