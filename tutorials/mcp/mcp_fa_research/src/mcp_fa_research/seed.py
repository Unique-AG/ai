"""seed.py — synthetic data for the FA (fundamental analyst) research demo.

One European-luxury coverage universe (6 names), centred on the LVMH profit-warning
scenario from Pascal's cockpit sketch (resources/fa-demo/06_Cockpit/cockpit.html).
ALL VALUES ARE SYNTHETIC — DEMO USE ONLY, not real market data or research.

Read-only by design: these are the "mock connectors" (consensus / price / estimates
à la the RM demo) plus the cockpit feeds (coverage, morning brief, inbox, agenda,
jobs). Persistent analyst state (thesis edits, interaction log growth) belongs to the
coverage-dossier skill in the Knowledge Base, not here.
"""

from __future__ import annotations

AS_OF = "07:00 CET"

# ---------------------------------------------------------------------------
# Coverage universe — the analyst's 6 names
# ---------------------------------------------------------------------------
COVERAGE: list[dict] = [
    {
        "ticker": "MC.PA", "yahoo": "MC.PA", "bbg": "MC FP", "name": "LVMH",
        "sector": "Luxury Goods", "ccy": "EUR",
        "rating": "Outperform", "target_price": 675.0, "price": 585.0, "upside_pct": 15.4,
        "status": "profit warning · initiation in progress",
        "pills": [{"kind": "warn", "label": "⚠ warning"}, {"kind": "init", "label": "✍ initiation"}],
        "premarket_pct": -6.2,
        "next_catalyst": "FY25 results (profit-warning scenario)",
    },
    {
        "ticker": "KER.PA", "yahoo": "KER.PA", "bbg": "KER FP", "name": "Kering",
        "sector": "Luxury Goods", "ccy": "EUR",
        "rating": "Underperform", "target_price": 210.0, "price": 230.0, "upside_pct": -8.7,
        "status": "estimate review due",
        "pills": [{"kind": "ctrl", "label": "◯ review"}],
        "premarket_pct": 0.4,
        "next_catalyst": "Q sales update",
    },
    {
        "ticker": "RMS.PA", "yahoo": "RMS.PA", "bbg": "RMS FP", "name": "Hermès",
        "sector": "Luxury Goods", "ccy": "EUR",
        "rating": "Neutral", "target_price": 2250.0, "price": 2300.0, "upside_pct": -2.2,
        "status": "up to date",
        "pills": [{"kind": "ok", "label": "✓"}],
        "premarket_pct": 0.3,
        "next_catalyst": "Q sales update",
    },
    {
        "ticker": "CFR.SW", "yahoo": "CFR.SW", "bbg": "CFR SW", "name": "Richemont",
        "sector": "Luxury Goods", "ccy": "CHF",
        "rating": "Outperform", "target_price": 170.0, "price": 155.0, "upside_pct": 9.7,
        "status": "note in draft",
        "pills": [{"kind": "init", "label": "✎ draft"}],
        "premarket_pct": -0.2,
        "next_catalyst": "H1 results",
    },
    {
        "ticker": "MONC.MI", "yahoo": "MONC.MI", "bbg": "MONC IM", "name": "Moncler",
        "sector": "Luxury Goods", "ccy": "EUR",
        "rating": "Neutral", "target_price": 55.0, "price": 52.0, "upside_pct": 5.8,
        "status": "up to date",
        "pills": [{"kind": "ok", "label": "✓"}],
        "premarket_pct": 0.6,
        "next_catalyst": "Q sales update",
    },
    {
        "ticker": "UHR.SW", "yahoo": "UHR.SW", "bbg": "UHR SW", "name": "Swatch Group",
        "sector": "Luxury Goods", "ccy": "CHF",
        "rating": "Underperform", "target_price": 160.0, "price": 165.0, "upside_pct": -3.0,
        "status": "in pre-publication control",
        "pills": [{"kind": "ctrl", "label": "◯ control"}],
        "premarket_pct": -0.3,
        "next_catalyst": "H1 results",
    },
]

# name/alias → canonical ticker (case-insensitive lookup at resolve time)
ALIASES: dict[str, str] = {
    "lvmh": "MC.PA", "mc fp": "MC.PA", "mc.pa": "MC.PA", "moet": "MC.PA",
    "kering": "KER.PA", "ker fp": "KER.PA", "ker.pa": "KER.PA", "gucci": "KER.PA",
    "hermes": "RMS.PA", "hermès": "RMS.PA", "rms fp": "RMS.PA", "rms.pa": "RMS.PA",
    "richemont": "CFR.SW", "cfr sw": "CFR.SW", "cfr.sw": "CFR.SW", "cartier": "CFR.SW",
    "moncler": "MONC.MI", "monc im": "MONC.MI", "monc.mi": "MONC.MI",
    "swatch": "UHR.SW", "swatch group": "UHR.SW", "uhr sw": "UHR.SW", "uhr.sw": "UHR.SW",
}

# ---------------------------------------------------------------------------
# Per-name dossier (the cockpit drawer; the KB coverage-dossier is the deep record)
# ---------------------------------------------------------------------------
DOSSIERS: dict[str, dict] = {
    "MC.PA": {
        "thesis": "Reference luxury compounder; FY25 = earnings trough; Sephora "
                  "counter-cyclical; cognac destocking the near-term drag.",
        "estimates": "FY25E EPS €21.0 (below capitulated consensus €21.3) · margin floor 21.6%.",
        "interaction_log": ["H1-25 call", "FY24 call", "IR follow-up (cognac timeline)",
                            "NY corporate roadshow (planned)"],
        "note_history": ["Initiation (in progress)", "First-take (draft)",
                         "Pre-publication control (pending)"],
    },
    "KER.PA": {
        "thesis": "Gucci turnaround execution risk; aspirational over-exposure; we stay "
                  "cautious until volumes stabilise.",
        "estimates": "FY26E organic −1%; consensus cut −3% overnight — estimate review suggested.",
        "interaction_log": ["FY25 call", "CFO meeting (brand reset)", "Sector conference"],
        "note_history": ["Estimate-change note (2w ago)", "Review due"],
    },
    "RMS.PA": {
        "thesis": "Highest-quality compounder; the quality is in the price — we prefer the "
                  "risk/reward elsewhere at current multiples.",
        "estimates": "FY26E organic +9%; P/E ~48x — premium justified but full.",
        "interaction_log": ["FY25 call", "Store visit note"],
        "note_history": ["Up to date — last note 3w ago"],
    },
    "CFR.SW": {
        "thesis": "Jewellery structural winner (Cartier, VCA); balance-sheet optionality.",
        "estimates": "FY26E organic +6%; jewellery mix supports margin.",
        "interaction_log": ["H1 call", "IR follow-up (China)"],
        "note_history": ["Note in draft — valuation section pending"],
    },
    "MONC.MI": {
        "thesis": "Single-brand story; brand heat solid, watch wholesale normalisation.",
        "estimates": "FY26E organic +6%; margin resilient.",
        "interaction_log": ["FY25 call", "Genius event note"],
        "note_history": ["Up to date"],
    },
    "UHR.SW": {
        "thesis": "Most geared to a Chinese entry-consumer recovery; a high-beta call on "
                  "the timing of the China turn, not a quality holding.",
        "estimates": "FY26E organic +2%; earnings sensitive to China entry demand.",
        "interaction_log": ["H1 call", "Q3 transcript (new, indexed)"],
        "note_history": ["Note in pre-publication control"],
    },
}

# ---------------------------------------------------------------------------
# Morning brief — generated 07:00, the profit-warning cascade on LVMH
# ---------------------------------------------------------------------------
MORNING_BRIEF: dict = {
    "generated_at": "07:00 CET",
    "items": [
        {
            "severity": "alert", "ticker": "MC.PA", "name": "LVMH",
            "title": "LVMH — PROFIT WARNING (pre-open)",
            "detail": "FY guidance cut on deeper cognac destocking + China; stock indicated "
                      "−6%. The agent has prepared the full reaction:",
            "synthetic": True,
            "cascade": [
                {"step": 1, "label": "Model updated · recurring EBIT & EPS cut"},
                {"step": 2, "label": "Target price revised down · new upside %"},
                {"step": 3, "label": "Morning-meeting note ready — for the mic, Exane Sales"},
                {"step": 4, "label": "Buy-side reaction email drafted + priority call list"},
            ],
            "call_list": [
                {"account": "Fund A", "priority": "High"},
                {"account": "Fund B", "priority": "High"},
                {"account": "Fund C", "priority": "Med"},
                {"account": "+4 holders", "priority": ""},
            ],
            "suggested_action": "Open the reaction pack",
        },
        {
            "severity": "watch", "ticker": "KER.PA", "name": "Kering",
            "title": "Kering — consensus −3% overnight",
            "detail": "Two brokers cut FY26 EBIT. Suggested: review our estimate vs new consensus.",
            "suggested_action": "Run estimate review",
        },
        {
            "severity": "watch", "ticker": "UHR.SW", "name": "Swatch Group",
            "title": "Swatch — Q3 transcript now available",
            "detail": "New call transcript indexed. Suggested: run tone × guidance analysis.",
            "suggested_action": "Run tone/guidance",
        },
    ],
}

# ---------------------------------------------------------------------------
# Action inbox — drafts prepared by the agent; NOTHING is ever auto-sent
# ---------------------------------------------------------------------------
ACTION_INBOX: list[dict] = [
    {"from": "Head of Sales", "subject": "\"Need your LVMH reaction for the desk\"",
     "kind": "reply draft", "status": "draft ready"},
    {"from": "Buy-side PM — Fund A", "subject": "\"Your read on the cognac destocking?\"",
     "kind": "reply draft", "status": "draft ready"},
    {"from": "LVMH Investor Relations", "subject": "NY roadshow logistics — dates & venue",
     "kind": "reply draft", "status": "draft ready"},
]

# ---------------------------------------------------------------------------
# Agenda — the two roadshow modes
# ---------------------------------------------------------------------------
AGENDA: list[dict] = [
    {"title": "Investor roadshow — London", "role": "you lead · marketing the LVMH case",
     "when": "Wed–Thu", "kind": "investor", "action": "prep pack"},
    {"title": "Corporate roadshow — New York",
     "role": "you organise · LVMH CEO / CFO / Head of IR",
     "when": "Next week", "kind": "corporate", "action": "agenda + targeting"},
]

# ---------------------------------------------------------------------------
# Jobs — scheduled/background runs + the side-panel notification
# ---------------------------------------------------------------------------
JOBS: dict = {
    "jobs": [
        {"label": "first-take run — LVMH", "status": "running"},
        {"label": "scheduled 07:00 — desk brief (6 names)", "status": "scheduled"},
        {"label": "scheduled — tone drift monitor", "status": "scheduled"},
        {"label": "tone × guidance — Swatch", "status": "done"},
    ],
    "notification": "LVMH reaction pack ready — model, note, buy-side email drafted.",
}

# ---------------------------------------------------------------------------
# Mock market-data connectors (à la the RM demo): consensus / price / estimates
# ---------------------------------------------------------------------------
CONSENSUS: dict[str, dict] = {
    "MC.PA": {
        "as_of": "20 January 2026", "analysts": 24, "period": "FY2025E",
        "eps_mean": 21.3, "eps_high": 23.1, "eps_low": 19.8,
        "revenue_bn": 79.6, "rec_ebit_margin_pct": 21.9,
        "ratings": {"buy": 13, "hold": 8, "sell": 3},
        "tp_mean": 640.0, "note": "Capitulated into the print — 11 cuts in 6 weeks.",
    },
    "KER.PA": {
        "as_of": "this morning", "analysts": 21, "period": "FY2026E",
        "eps_mean": 17.8, "eps_high": 20.0, "eps_low": 15.9,
        "revenue_bn": 17.2, "rec_ebit_margin_pct": 15.4,
        "ratings": {"buy": 5, "hold": 10, "sell": 6},
        "tp_mean": 235.0, "note": "Two brokers cut FY26 EBIT overnight (−3% consensus move).",
    },
}

OUR_ESTIMATES: dict[str, dict] = {
    "MC.PA": {
        "period": "FY2025E",
        "rows": [
            {"metric": "Revenue (€bn)", "ours": 79.1, "consensus": 79.6, "delta": "−0.6%"},
            {"metric": "Recurring EBIT margin (%)", "ours": 21.6, "consensus": 21.9, "delta": "−30bp"},
            {"metric": "EPS (€)", "ours": 21.0, "consensus": 21.3, "delta": "−1.4%"},
            {"metric": "DPS (€)", "ours": 13.0, "consensus": 13.2, "delta": "−1.5%"},
        ],
        "stance": "Below the street into the print — we see the cognac destocking running deeper.",
    },
    "KER.PA": {
        "period": "FY2026E",
        "rows": [
            {"metric": "Organic growth (%)", "ours": -1.0, "consensus": 0.5, "delta": "−150bp"},
            {"metric": "EPS (€)", "ours": 16.9, "consensus": 17.8, "delta": "−5.1%"},
        ],
        "stance": "Below consensus; estimate review due after the overnight cuts.",
    },
}

PRICES: dict[str, dict] = {
    c["ticker"]: {
        "ticker": c["ticker"], "name": c["name"], "ccy": c["ccy"],
        "last_close": c["price"], "premarket_pct": c["premarket_pct"],
        "note": "SYNTHETIC indication — use the yahoo-finance connector for live quotes.",
    }
    for c in COVERAGE
}


def resolve(ticker_or_name: str) -> str | None:
    """Resolve a ticker/name/alias to the canonical ticker, or None."""
    raw = (ticker_or_name or "").strip().lower()
    if not raw:
        return None
    if raw in ALIASES:
        return ALIASES[raw]
    for c in COVERAGE:
        if raw in (c["ticker"].lower(), c["yahoo"].lower(), c["bbg"].lower(), c["name"].lower()):
            return c["ticker"]
    return None
