"""chart_pack.py — multi-year financials + chart series for the coverage dashboards.

``get_financials(ticker)`` serves, for EVERY covered name, the numbers behind the
Exane-style dashboard figures: a key-financials table (FY23→FY28e) and chart series
with DISPLAY-READY labels *and* precomputed bar geometry (pct heights, shared
positive/negative scale) so a script-free canvas can render bars from attributes
alone. The nightly review build (build_reviews.py) bakes the same data — single
source of truth. ALL VALUES ARE SYNTHETIC — DEMO USE ONLY.

Raw per-name series (FY2023 … FY2028e; first ``n_actuals`` are actuals):
sales (bn), organic growth (%), recurring EBIT margin (%), EPS, DPS, FCF (bn).
MC FP mirrors note_pack.py / seed.py (post-warning base: TP EUR615, FY25 trough).
"""

from __future__ import annotations

YEARS = ["2023", "2024", "2025", "2026e", "2027e", "2028e"]
N_ACTUALS = 3  # 2023-25 printed; 2026e+ are estimates

_RAW: dict[str, dict] = {
    "MC FP": {
        "ccy": "EUR",
        "sales":   [86.15, 84.68, 78.90, 81.29, 85.76, 90.59],
        "organic": [13.3, 1.0, -4.3, 2.6, 5.0, 5.2],
        "margin":  [26.5, 23.1, 21.2, 21.8, 22.6, 23.2],
        "eps":     [30.3, 25.1, 20.4, 21.6, 23.9, 26.1],
        "dps":     [13.00, 13.00, 12.75, 13.30, 14.70, 16.00],
        "fcf":     [8.1, 10.4, 9.0, 9.9, 11.3, 12.8],
        "extra_charts": [
            {"key": "ws_sales", "title": "Wines & Spirits sales (EURbn) — the cognac reset, then recovery",
             "values": [6.64, 5.86, 4.91, 5.11, 5.57, 6.02], "fmt": "{:.1f}"},
            {"key": "sephora", "title": "Selective Retailing sales (EURbn) — Sephora compounds through the cycle",
             "values": [17.89, 18.26, 18.98, 19.93, 21.13, 22.39], "fmt": "{:.1f}"},
        ],
    },
    "KER FP": {
        "ccy": "EUR",
        "sales":   [19.57, 17.19, 16.41, 16.24, 16.69, 17.36],
        "organic": [-4.0, -12.0, -4.5, -1.0, 2.8, 4.0],
        "margin":  [23.5, 19.0, 17.6, 18.5, 19.4, 20.3],
        "eps":     [22.2, 16.4, 15.3, 16.9, 18.6, 20.5],
        "dps":     [14.00, 6.00, 6.00, 6.50, 7.00, 7.50],
        "fcf":     [3.3, 1.4, 1.2, 1.4, 1.7, 2.0],
    },
    "RMS FP": {
        "ccy": "EUR",
        "sales":   [13.43, 15.17, 16.45, 17.93, 19.54, 21.20],
        "organic": [21.0, 13.0, 8.5, 9.0, 9.0, 8.5],
        "margin":  [42.1, 40.5, 40.2, 40.6, 40.9, 41.2],
        "eps":     [41.3, 44.7, 47.9, 52.8, 58.3, 64.1],
        "dps":     [15.00, 16.00, 17.00, 18.50, 20.00, 22.00],
        "fcf":     [3.5, 4.0, 4.4, 4.9, 5.4, 6.0],
    },
    "CFR SW": {
        "ccy": "CHF",
        "sales":   [20.62, 21.41, 22.28, 23.62, 25.04, 26.42],
        "organic": [3.0, 5.0, 5.5, 6.0, 6.0, 5.5],
        "margin":  [23.3, 23.9, 24.4, 25.1, 25.6, 26.0],
        "eps":     [5.9, 6.1, 6.3, 6.7, 7.3, 7.9],
        "dps":     [2.75, 3.00, 3.20, 3.50, 3.80, 4.10],
        "fcf":     [3.2, 3.4, 3.7, 4.0, 4.3, 4.7],
    },
    "MONC IM": {
        "ccy": "EUR",
        "sales":   [2.98, 3.11, 3.26, 3.46, 3.68, 3.92],
        "organic": [8.0, 4.0, 5.0, 6.0, 6.0, 6.0],
        "margin":  [29.5, 29.1, 29.3, 29.6, 29.9, 30.1],
        "eps":     [2.25, 2.34, 2.46, 2.62, 2.81, 3.02],
        "dps":     [1.15, 1.25, 1.30, 1.40, 1.50, 1.62],
        "fcf":     [0.60, 0.65, 0.70, 0.75, 0.82, 0.90],
    },
    "UHR SW": {
        "ccy": "CHF",
        "sales":   [7.89, 6.74, 6.52, 6.65, 6.88, 7.16],
        "organic": [5.2, -14.6, -2.5, 2.0, 3.5, 4.0],
        "margin":  [15.1, 8.5, 7.8, 8.4, 9.5, 10.6],
        "eps":     [16.4, 10.1, 9.4, 10.3, 12.1, 13.9],
        "dps":     [6.50, 4.50, 4.50, 5.00, 5.50, 6.00],
        "fcf":     [0.8, 0.4, 0.4, 0.5, 0.6, 0.7],
    },
}


def _series(title: str, values: list[float], fmt: str = "{:.1f}",
            signed: bool = False) -> dict:
    """A chart series with display labels + bar geometry on a shared ± scale.

    zero_pct     — the zero axis position, % from the TOP of the chart area
    point.pct    — bar height as % of its zone (positive zone above the axis,
                   negative zone below); point.neg marks below-axis bars
    point.kind   — 'a' actual, 'e' estimate (striped in the dashboards)
    """
    max_pos = max([v for v in values if v > 0], default=0.0)
    min_neg = min([v for v in values if v < 0], default=0.0)
    span = (max_pos - min_neg) or 1.0
    zero_pct = round(100.0 * max_pos / span, 1)
    points = []
    for i, v in enumerate(values):
        label = fmt.format(v)
        if signed and v > 0:
            label = "+" + label
        if v >= 0:
            pct = round(100.0 * v / max_pos, 1) if max_pos else 0.0
            neg = False
        else:
            pct = round(100.0 * abs(v) / abs(min_neg), 1) if min_neg else 0.0
            neg = True
        points.append({"label": YEARS[i], "value": v, "value_label": label,
                       "pct": pct, "neg": neg,
                       "kind": "a" if i < N_ACTUALS else "e"})
    return {"title": title, "zero_pct": zero_pct, "has_neg": min_neg < 0,
            "points": points,
            "source": "Source: Company data, BNP Paribas Exane (synthetic estimates)"}


def get_financials(ticker: str) -> dict | None:
    r = _RAW.get(ticker)
    if not r:
        return None
    ccy = r["ccy"]
    fmt_row = lambda vals, fmt, signed=False: [  # noqa: E731
        (("+" if (signed and v > 0) else "") + fmt.format(v)) for v in vals]
    key_financials = {
        "title": f"Key financials — FY2023-28e ({ccy})",
        "header": ["", *YEARS],
        "estimate_cols": [i + 1 for i in range(len(YEARS)) if i >= N_ACTUALS],
        "rows": [
            [f"Sales ({ccy}bn)", *fmt_row(r["sales"], "{:,.2f}")],
            ["Organic growth (%)", *fmt_row(r["organic"], "{:.1f}", signed=True)],
            ["Rec. EBIT margin (%)", *fmt_row(r["margin"], "{:.1f}")],
            [f"EPS ({ccy})", *fmt_row(r["eps"], "{:.2f}")],
            [f"DPS ({ccy})", *fmt_row(r["dps"], "{:.2f}")],
            [f"Free cash flow ({ccy}bn)", *fmt_row(r["fcf"], "{:.1f}")],
        ],
        "source": "Source: Company data, BNP Paribas Exane (synthetic estimates); "
                  "2026e-28e are estimates",
    }
    charts = [
        _series(f"Sales ({ccy}bn)", r["sales"], "{:.1f}"),
        _series("Organic growth (%)", r["organic"], "{:.1f}", signed=True),
        _series("Rec. EBIT margin (%)", r["margin"], "{:.1f}"),
        _series(f"EPS ({ccy})", r["eps"], "{:.1f}"),
    ]
    for ch in r.get("extra_charts", []):
        charts.append(_series(ch["title"], ch["values"], ch.get("fmt", "{:.1f}")))
    return {"ticker": ticker, "ccy": ccy, "years": YEARS, "n_actuals": N_ACTUALS,
            "key_financials": key_financials, "charts": charts,
            "note": "SYNTHETIC demo data. pct/zero_pct are precomputed bar geometry so "
                    "script-free canvases can render the charts from attributes alone."}
