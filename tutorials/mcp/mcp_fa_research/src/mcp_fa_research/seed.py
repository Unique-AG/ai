"""seed.py — synthetic data for the FA (fundamental analyst) research demo.

One European-luxury coverage universe (6 names). The story: **reports are generated
overnight** (the scheduled 07:00 desk brief) and the analyst **reviews them early in the
morning** from the cockpit. The overnight run surfaces several market-data / news changes
that move (or explicitly don't move) valuation — an LVMH profit warning, a Richemont
positive jewellery read, a Kering consensus cut, a Swatch tone-drift transcript, a peer
downgrade, an FX move, and a China macro headline.

ALL VALUES ARE SYNTHETIC — DEMO USE ONLY. Reference data (coverage statics, dossiers,
consensus, prices) are module constants; the *mutable* demo state the analyst touches in
the morning (brief acknowledgements, reviewed drafts, jobs) is built by ``baseline()`` and
restored by the server's ``Reset_Demo_Data``.
"""

from __future__ import annotations

import copy

AS_OF = "07:00 CET"

# ---------------------------------------------------------------------------
# Coverage universe — the analyst's 6 names (static reference)
# ---------------------------------------------------------------------------
COVERAGE: list[dict] = [
    {"ticker": "MC FP", "yahoo": "MC.PA", "bbg": "MC FP", "name": "LVMH",
     "sector": "Luxury Goods", "ccy": "EUR", "rating": "Outperform",
     "target_price": 675.0, "price": 585.0, "upside_pct": 15.4,
     "status": "profit warning · post-view due ASAP",
     "pills": [{"kind": "warn", "label": "⚠ warning"}, {"kind": "init", "label": "✍ initiation"}],
     "premarket_pct": -6.2, "next_catalyst": "FY25 results (profit-warning scenario)"},
    {"ticker": "KER FP", "yahoo": "KER.PA", "bbg": "KER FP", "name": "Kering",
     "sector": "Luxury Goods", "ccy": "EUR", "rating": "Underperform",
     "target_price": 210.0, "price": 230.0, "upside_pct": -8.7,
     "status": "estimate review due",
     "pills": [{"kind": "ctrl", "label": "◯ review"}],
     "premarket_pct": 0.4, "next_catalyst": "Q sales update"},
    {"ticker": "RMS FP", "yahoo": "RMS.PA", "bbg": "RMS FP", "name": "Hermès",
     "sector": "Luxury Goods", "ccy": "EUR", "rating": "Neutral",
     "target_price": 2250.0, "price": 2300.0, "upside_pct": -2.2,
     "status": "up to date",
     "pills": [{"kind": "ok", "label": "✓"}],
     "premarket_pct": 0.3, "next_catalyst": "Q sales update"},
    {"ticker": "CFR SW", "yahoo": "CFR.SW", "bbg": "CFR SW", "name": "Richemont",
     "sector": "Luxury Goods", "ccy": "CHF", "rating": "Outperform",
     "target_price": 170.0, "price": 155.0, "upside_pct": 9.7,
     "status": "note in draft · estimates under review (upside)",
     "pills": [{"kind": "init", "label": "✎ draft"}, {"kind": "up", "label": "▲ upside"}],
     "premarket_pct": 1.9, "next_catalyst": "H1 results"},
    {"ticker": "MONC IM", "yahoo": "MONC.MI", "bbg": "MONC IM", "name": "Moncler",
     "sector": "Luxury Goods", "ccy": "EUR", "rating": "Neutral",
     "target_price": 55.0, "price": 52.0, "upside_pct": 5.8,
     "status": "up to date",
     "pills": [{"kind": "ok", "label": "✓"}],
     "premarket_pct": -0.4, "next_catalyst": "Q sales update"},
    {"ticker": "UHR SW", "yahoo": "UHR.SW", "bbg": "UHR SW", "name": "Swatch Group",
     "sector": "Luxury Goods", "ccy": "CHF", "rating": "Underperform",
     "target_price": 160.0, "price": 165.0, "upside_pct": -3.0,
     "status": "in pre-publication control · tone flag",
     "pills": [{"kind": "ctrl", "label": "◯ control"}, {"kind": "warn", "label": "⚠ tone"}],
     "premarket_pct": -0.8, "next_catalyst": "H1 results"},
]

ALIASES: dict[str, str] = {
    "lvmh": "MC FP", "mc fp": "MC FP", "mc.pa": "MC FP", "moet": "MC FP",
    "kering": "KER FP", "ker fp": "KER FP", "ker.pa": "KER FP", "gucci": "KER FP",
    "hermes": "RMS FP", "hermès": "RMS FP", "rms fp": "RMS FP", "rms.pa": "RMS FP",
    "richemont": "CFR SW", "cfr sw": "CFR SW", "cfr.sw": "CFR SW", "cartier": "CFR SW",
    "moncler": "MONC IM", "monc im": "MONC IM", "monc.mi": "MONC IM",
    "swatch": "UHR SW", "swatch group": "UHR SW", "uhr sw": "UHR SW", "uhr.sw": "UHR SW",
}

# ---------------------------------------------------------------------------
# Overnight run — the market-data / news changes generated during the night.
# severity: alert (act now) · positive (upside) · watch (review) · info (note)
# Each carries the valuation read (the "so what") + the skill the analyst runs.
# ---------------------------------------------------------------------------
OVERNIGHT: dict[str, dict] = {
    "MC FP": {
        "ticker": "MC FP", "name": "LVMH", "severity": "alert", "category": "results",
        "headline": "PROFIT WARNING (pre-open) — FY guidance cut",
        "detail": "FY guidance cut on deeper Hennessy cognac destocking + soft China Q4; "
                  "management drops 'resilient growth' language, now guides FY organic "
                  "slightly negative. Stock indicated −6%.",
        "valuation_impact": "Recurring EBIT −6%, EPS −7%; target price €675 → €615 "
                            "(upside +5%). Rating held Outperform — trough thesis intact.",
        "new_target_price": 615.0, "new_upside_pct": 5.1, "price_move_pct": -6.2,
        "direction": "down", "suggested_skill": "results-first-take",
        "suggested_action": "Launch the reaction pack",
    },
    "CFR SW": {
        "ticker": "CFR SW", "name": "Richemont", "severity": "positive", "category": "news",
        "headline": "Strong US jewellery data + peer pre-announcement",
        "detail": "Overnight US luxury-jewellery tracker and a peer's positive "
                  "pre-announcement point to Cartier / Van Cleef momentum into H1 — ahead "
                  "of our estimates.",
        "valuation_impact": "Upside risk to FY26 jewellery estimates (+3–4%); target price "
                            "CHF 170 → CHF 180 under review. Outperform reinforced.",
        "new_target_price": 180.0, "new_upside_pct": 16.1, "price_move_pct": 1.9,
        "direction": "up", "suggested_skill": "exane-financial-model",
        "suggested_action": "Raise estimates — review",
    },
    "KER FP": {
        "ticker": "KER FP", "name": "Kering", "severity": "watch", "category": "consensus",
        "headline": "Consensus −3% overnight — two brokers cut FY26 EBIT",
        "detail": "Weak Gucci run-rate read; sell-side consensus FY26 EBIT −3% overnight.",
        "valuation_impact": "We were already below (FY26 EPS €16.9 vs €17.8 consensus); no "
                            "TP change, but our Underperform (−8.7%) is better supported.",
        "new_target_price": None, "price_move_pct": 0.4, "direction": "down",
        "suggested_skill": "coverage-morning-brief",
        "suggested_action": "Run estimate review",
    },
    "UHR SW": {
        "ticker": "UHR SW", "name": "Swatch Group", "severity": "watch", "category": "transcript",
        "headline": "New Q3 transcript indexed — softer China entry-demand tone",
        "detail": "Management language on the China entry consumer turned more cautious vs "
                  "the H1 call — the kind of qualitative tone drift that precedes a reset.",
        "valuation_impact": "Early-warning flag: downside risk to FY26 organic +2%; watch "
                            "for a guidance reset. No change yet — run tone × guidance.",
        "new_target_price": None, "price_move_pct": -0.8, "direction": "down",
        "suggested_skill": "tone-guidance-analysis",
        "suggested_action": "Run tone/guidance",
    },
    "RMS FP": {
        "ticker": "RMS FP", "name": "Hermès", "severity": "info", "category": "rating",
        "headline": "A broker cut the luxury sector on multiples overnight",
        "detail": "A competing house downgraded European luxury on valuation; Hermès is "
                  "most exposed to a de-rating given its ~48x P/E premium.",
        "valuation_impact": "Quality but priced — we stay Neutral. No estimate change; flag "
                            "the multiple risk in the morning meeting.",
        "new_target_price": None, "price_move_pct": 0.3, "direction": "flat",
        "suggested_skill": "exane-desknote", "suggested_action": "Note the peer move",
    },
    "MONC IM": {
        "ticker": "MONC IM", "name": "Moncler", "severity": "info", "category": "price",
        "headline": "FX: EUR strength overnight (EURUSD +0.8%)",
        "detail": "A stronger EUR is a modest translation headwind for EUR reporters with "
                  "USD / Asia exposure.",
        "valuation_impact": "~−0.5% to FY26 reported revenue; immaterial to the target "
                            "price. Monitor if sustained.",
        "new_target_price": None, "price_move_pct": -0.4, "direction": "flat",
        "suggested_skill": "exane-financial-model", "suggested_action": "Monitor",
    },
    "SECTOR": {
        "ticker": "SECTOR", "name": "European Luxury", "severity": "positive", "category": "macro",
        "headline": "China announces consumption-support measures overnight",
        "detail": "Beijing unveiled consumer-stimulus measures — a potential sentiment "
                  "tailwind for China-exposed luxury; partially cushions LVMH, helps Swatch "
                  "and Richemont.",
        "valuation_impact": "Sector sentiment positive; raises the option value on a China "
                            "turn. No single-name estimate change yet — factor into the "
                            "morning-meeting narrative.",
        "new_target_price": None, "price_move_pct": None, "direction": "up",
        "suggested_skill": "coverage-morning-brief",
        "suggested_action": "Frame in the desk brief",
    },
}

# Order the overnight items surface in the brief: alerts first, then upside, watch, info.
_SEVERITY_RANK = {"alert": 0, "positive": 1, "watch": 2, "info": 3}
OVERNIGHT_ORDER = sorted(OVERNIGHT, key=lambda k: (_SEVERITY_RANK[OVERNIGHT[k]["severity"]], k))

# The prepared LVMH profit-warning reaction cascade + priority call list
LVMH_CASCADE = [
    {"step": 1, "label": "Model updated · recurring EBIT & EPS cut ~7%"},
    {"step": 2, "label": "Target price revised €675 → €615 · new upside +5%"},
    {"step": 3, "label": "Post-view note drafted — for the mic · publish ASAP"},
    {"step": 4, "label": "Buy-side reaction email drafted + priority call list"},
]
LVMH_CALL_LIST = [
    {"account": "Fund A", "priority": "High"},
    {"account": "Fund B", "priority": "High"},
    {"account": "Fund C", "priority": "Med"},
    {"account": "+4 holders", "priority": ""},
]

# ---------------------------------------------------------------------------
# Per-name dossier (the cockpit drawer; the KB coverage-dossier is the deep record)
# ---------------------------------------------------------------------------
DOSSIERS: dict[str, dict] = {
    "MC FP": {"thesis": "Reference luxury compounder; FY25 = earnings trough; Sephora "
              "counter-cyclical; cognac destocking the near-term drag.",
              "estimates": "Preview (T-5d): EPS €21.0 vs consensus €21.3 · Company printed €20.4 "
                           "+ FY guidance cut — post-view due ASAP.",
              "interaction_log": ["H1-25 call", "FY24 call", "IR follow-up (cognac timeline)",
                                  "NY corporate roadshow (planned)"],
              "note_history": ["Re-initiation of coverage (published)",
                               "FY25 Preview — Ours vs Consensus (published T-5d)",
                               "Profit warning — reaction pack (this morning)",
                               "Post-view — Ours / Consensus / Company (draft · publish ASAP)"]},
    "KER FP": {"thesis": "Gucci turnaround execution risk; aspirational over-exposure; we "
               "stay cautious until volumes stabilise.",
               "estimates": "FY26E organic −1%; consensus cut −3% overnight — estimate review suggested.",
               "interaction_log": ["FY25 call", "CFO meeting (brand reset)", "Sector conference"],
               "note_history": ["Estimate-change note (2w ago)", "Review due"]},
    "RMS FP": {"thesis": "Highest-quality compounder; the quality is in the price — we "
               "prefer the risk/reward elsewhere at current multiples.",
               "estimates": "FY26E organic +9%; P/E ~48x — premium justified but full.",
               "interaction_log": ["FY25 call", "Store visit note"],
               "note_history": ["Up to date — last note 3w ago"]},
    "CFR SW": {"thesis": "Jewellery structural winner (Cartier, VCA); balance-sheet optionality.",
               "estimates": "FY26E organic +6%; jewellery mix supports margin — upside risk overnight.",
               "interaction_log": ["H1 call", "IR follow-up (China)"],
               "note_history": ["Note in draft — valuation section pending"]},
    "MONC IM": {"thesis": "Single-brand story; brand heat solid, watch wholesale normalisation.",
                "estimates": "FY26E organic +6%; margin resilient.",
                "interaction_log": ["FY25 call", "Genius event note"],
                "note_history": ["Up to date"]},
    "UHR SW": {"thesis": "Most geared to a Chinese entry-consumer recovery; a high-beta call "
               "on the timing of the China turn, not a quality holding.",
               "estimates": "FY26E organic +2%; earnings sensitive to China entry demand.",
               "interaction_log": ["H1 call", "Q3 transcript (new, indexed)"],
               "note_history": ["Note in pre-publication control"]},
}

# ---------------------------------------------------------------------------
# Action inbox (drafts only — nothing auto-sent), agenda, jobs
# ---------------------------------------------------------------------------
ACTION_INBOX: list[dict] = [
    {"from": "Head of Sales", "subject": "\"Need your LVMH reaction for the desk\"",
     "kind": "reply draft"},
    {"from": "Buy-side PM — Fund A", "subject": "\"Your read on the cognac destocking?\"",
     "kind": "reply draft"},
    {"from": "LVMH Investor Relations", "subject": "NY roadshow logistics — dates & venue",
     "kind": "reply draft"},
]

AGENDA: list[dict] = [
    {"title": "Investor roadshow — London", "role": "you lead · marketing the LVMH case",
     "when": "Wed–Thu", "kind": "investor", "action": "prep pack"},
    {"title": "Corporate roadshow — New York",
     "role": "you organise · LVMH CEO / CFO / Head of IR",
     "when": "Next week", "kind": "corporate", "action": "agenda + targeting"},
]

JOBS_SEED: list[dict] = [
    {"label": "overnight desk brief (6 names) — generated 07:00", "status": "done"},
    {"label": "first-take run — LVMH", "status": "running"},
    {"label": "scheduled — tone drift monitor", "status": "scheduled"},
    {"label": "tone × guidance — Swatch", "status": "done"},
]
NOTIFICATION = "LVMH reaction pack ready — model, note, buy-side email drafted."

# ---------------------------------------------------------------------------
# Mock market-data connectors: consensus / our-estimates / price
# ---------------------------------------------------------------------------
CONSENSUS: dict[str, dict] = {
    "MC FP": {"as_of": "20 January 2026", "analysts": 24, "period": "FY2025E",
              "eps_mean": 21.3, "eps_high": 23.1, "eps_low": 19.8, "revenue_bn": 79.6,
              "rec_ebit_margin_pct": 21.9, "ratings": {"buy": 13, "hold": 8, "sell": 3},
              "tp_mean": 640.0, "note": "Capitulated into the print — 11 cuts in 6 weeks."},
    "KER FP": {"as_of": "this morning", "analysts": 21, "period": "FY2026E",
               "eps_mean": 17.8, "eps_high": 20.0, "eps_low": 15.9, "revenue_bn": 17.2,
               "rec_ebit_margin_pct": 15.4, "ratings": {"buy": 5, "hold": 10, "sell": 6},
               "tp_mean": 235.0, "note": "Two brokers cut FY26 EBIT overnight (−3% consensus)."},
    "CFR SW": {"as_of": "this morning", "analysts": 19, "period": "FY2026E",
               "eps_mean": 6.4, "eps_high": 7.1, "eps_low": 5.8, "revenue_bn": 22.1,
               "rec_ebit_margin_pct": 24.8, "ratings": {"buy": 11, "hold": 6, "sell": 2},
               "tp_mean": 165.0, "note": "Jewellery momentum not yet in numbers — upside risk."},
}

OUR_ESTIMATES: dict[str, dict] = {
    "MC FP": {"period": "FY2025", "phase": "post-release",
              "stance": "Preview (T-5d) had us below the street — right direction: the company "
              "printed lower still and cut FY guidance. Post-view: Ours / Consensus / Company.",
              "rows": [
                  {"metric": "Revenue (€bn)", "ours": 79.1, "consensus": 79.6, "company": 78.9, "delta": "−0.6%"},
                  {"metric": "Recurring EBIT margin (%)", "ours": 21.6, "consensus": 21.9, "company": 21.2, "delta": "−30bp"},
                  {"metric": "EPS (€)", "ours": 21.0, "consensus": 21.3, "company": 20.4, "delta": "−1.4%"},
                  {"metric": "DPS (€)", "ours": 13.0, "consensus": 13.2, "company": 12.75, "delta": "−1.5%"}]},
    "KER FP": {"period": "FY2026E", "phase": "pre-release",
               "stance": "Below consensus; estimate review due after the overnight cuts.",
               "rows": [
                   {"metric": "Organic growth (%)", "ours": -1.0, "consensus": 0.5, "delta": "−150bp"},
                   {"metric": "EPS (€)", "ours": 16.9, "consensus": 17.8, "delta": "−5.1%"}]},
    "CFR SW": {"period": "FY2026E", "phase": "pre-release",
               "stance": "Above consensus on jewellery mix; overnight data supports raising further.",
               "rows": [
                   {"metric": "Organic growth (%)", "ours": 6.0, "consensus": 5.2, "delta": "+80bp"},
                   {"metric": "EPS (CHF)", "ours": 6.7, "consensus": 6.4, "delta": "+4.7%"}]},
}

PRICES: dict[str, dict] = {
    c["ticker"]: {"ticker": c["ticker"], "name": c["name"], "ccy": c["ccy"],
                  "last_close": c["price"], "premarket_pct": c["premarket_pct"],
                  "note": "SYNTHETIC indication — use the yahoo-finance connector for live quotes."}
    for c in COVERAGE
}


# ---------------------------------------------------------------------------
# Precomputed review documents (nightly build) — KB contentIds per name, so the
# cockpit can open a company's review directly (openDocument). Env-specific;
# override with FA_REVIEW_IDS_JSON (a JSON object {ticker: contentId}).
# ---------------------------------------------------------------------------
import json as _json
import os as _os

REVIEW_IDS: dict[str, str] = {
    "CFR SW": "cont_zxl88zou3zbpbtkndm0qlu4c",
    "KER FP": "cont_asj6dg80h2kwy2oxuly7hkv0",
    "MC FP": "cont_icjk0yb6tc1i2bhjstry1dzu",
    "MONC IM": "cont_eg2e9h3yrdd0gw8ynkbhe2xq",
    "RMS FP": "cont_mwcvdhqjexvy1nl4xufhcao8",
    "UHR SW": "cont_ikja9ogi0z66esh3cplmomrh"
}
try:
    REVIEW_IDS.update(_json.loads(_os.getenv("FA_REVIEW_IDS_JSON", "") or "{}"))
except Exception:
    pass

COCKPIT_ID: str = _os.getenv("FA_COCKPIT_ID", "")  # set after the cockpit is uploaded


def resolve(ticker_or_name: str) -> str | None:
    raw = (ticker_or_name or "").strip().lower()
    if not raw:
        return None
    if raw in ALIASES:
        return ALIASES[raw]
    for c in COVERAGE:
        if raw in (c["ticker"].lower(), c["yahoo"].lower(), c["bbg"].lower(), c["name"].lower()):
            return c["ticker"]
    return None


def coverage_with_overnight() -> list[dict]:
    """Coverage roster with each name's overnight move merged in (headline + valuation)."""
    out = []
    for c in COVERAGE:
        row = copy.deepcopy(c)
        ov = OVERNIGHT.get(c["ticker"])
        if ov:
            row["overnight"] = {"severity": ov["severity"], "headline": ov["headline"],
                                "valuation_impact": ov["valuation_impact"],
                                "new_target_price": ov.get("new_target_price")}
        out.append(row)
    return out


def _brief_item(key: str) -> dict:
    ov = copy.deepcopy(OVERNIGHT[key])
    ov["acknowledged"] = False
    if key == "MC FP":
        ov["cascade"] = copy.deepcopy(LVMH_CASCADE)
        ov["call_list"] = copy.deepcopy(LVMH_CALL_LIST)
    return ov


def baseline() -> dict:
    """A fresh copy of the MUTABLE demo state (what the analyst touches in the morning).
    The server holds this and Reset_Demo_Data restores it to this baseline."""
    return {
        "generated_at": "07:00 CET",
        "brief": [_brief_item(k) for k in OVERNIGHT_ORDER],
        "inbox": [{**copy.deepcopy(d), "reviewed": False} for d in ACTION_INBOX],
        "jobs": {"jobs": copy.deepcopy(JOBS_SEED), "notification": NOTIFICATION},
    }
