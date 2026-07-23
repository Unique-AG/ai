"""note_pack.py — the numeric backbone for house-format research notes.

``get_note_pack(ticker)`` serves everything a note template needs as DISPLAY-READY
tables ({"header": [...], "rows": [[...]]}) so the build script splices them verbatim
and the LLM only writes narrative. ALL VALUES ARE SYNTHETIC — DEMO USE ONLY.

Modelled on the BNP Paribas Exane note anatomy (initiation / revision / flash):
cover snapshot tables, key financials, estimates-vs-consensus, DCF + sensitivity,
SOTP, peer group, company profile, financial-highlights grid, six-charts data.

Only MC FP (LVMH) carries the FULL pack; other names return a partial pack
(cover snapshot only) with ``"full": false`` — enough for a flash note.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# LVMH (MC FP) — full note pack. Coherent with seed.py: last close EUR585,
# post-warning TP EUR615 (Outperform, upside +5%), FY25 printed low
# (rev 78.9bn / rec. EBIT margin 21.2% / EPS 20.4 / DPS 12.75).
# ---------------------------------------------------------------------------
_MC_FP: dict = {
    "full": True,
    "meta": {
        "company": "LVMH", "ticker": "MC FP", "ccy": "EUR",
        "sector_label": "LUXURY GOODS",
        "country_subsector": "France / Luxury Goods",
        "listing": "Refinitiv / Bloomberg: LVMH.PA / MC FP",
    },
    "header": {
        "rating": "OUTPERFORM",
        "price_label": "EUR585.0", "price_asof": "22 July 2026",
        "tp_label": "EUR615", "upside_label": "UPSIDE 5%",
        "horizon": "12m",
    },
    "esg": {"overall": "Average",
            "topics": [{"label": "Climate change", "score": "3/5"},
                       {"label": "Community & ethics", "score": "4/5"},
                       {"label": "Customers | Purpose", "score": "3/5"},
                       {"label": "Workers (own)", "score": "3/5"}]},
    # -- cover snapshot tables ------------------------------------------------
    "snapshot_company": {
        "title": "LVMH (+)", "ticker_label": "MC FP",
        "rows": [["*Closing Price (22 July 2026)", "EUR585.0"],
                 ["Volume (EURm)", "412.6"],
                 ["Market cap (EURbn)", "290.7"],
                 ["Free float (EURbn)", "150.2"],
                 ["EV (EURbn)", "302.1"],
                 ["Country / Sub Sector", "France / Luxury Goods"]],
    },
    "snapshot_financials": {
        "header": ["Financials", "12/25", "12/26e", "12/27e", "12/28e"],
        "rows": [["EPS, Adjusted (EUR)", "20.4", "21.6", "23.9", "26.1"],
                 ["EPS, Company (EUR)", "20.4", "21.6", "23.9", "26.1"],
                 ["EPS - Bloomberg (EUR)", "20.4", "21.9", "24.2", "26.4"],
                 ["Net dividend (EUR)", "12.75", "13.30", "14.70", "16.00"],
                 ["Sales (EURm)", "78,900", "81,290", "85,760", "90,590"],
                 ["Rec. EBIT, Adj. (EURm)", "16,730", "17,720", "19,380", "21,020"],
                 ["Net profit, Adj. (EURm)", "10,190", "10,790", "11,940", "13,040"],
                 ["ROCE (%)", "14.2", "14.8", "15.9", "17.0"],
                 ["Net Debt/EBITDA, Adj. (x)", "0.5", "0.4", "0.2", "0.1"]],
        "source": "Source: BNP Paribas Exane (synthetic estimates), Bloomberg (consensus)",
    },
    "snapshot_valuation": {
        "header": ["Valuation metrics", "12/25", "12/26e", "12/27e", "12/28e"],
        "rows": [["P/E (x)", "28.7", "27.1", "24.5", "22.4"],
                 ["Net yield (%)", "2.2", "2.3", "2.5", "2.7"],
                 ["FCF yield (%)", "3.1", "3.4", "3.9", "4.4"],
                 ["EV/Sales (x)", "3.8", "3.7", "3.4", "3.2"],
                 ["EV/EBITDA (x)", "13.9", "13.1", "11.9", "10.9"],
                 ["EV/EBIT (x)", "18.1", "17.0", "15.4", "14.1"]],
        "note": "All valuation metrics based on adjusted figures",
    },
    "snapshot_performance": {
        "header": ["Performance (1)", "1w", "1m", "3m", "12m"],
        "rows": [["Absolute (%)", "(7)", "(4)", "2", "(12)"],
                 ["Rel. Luxury Goods (%)", "(5)", "(2)", "(1)", "(8)"],
                 ["Rel. MSCI Europe (%)", "(6)", "(3)", "0", "(10)"]],
        "note": "(1) In listing currency, with dividend reinvested",
    },
    # -- financials section ---------------------------------------------------
    "key_financials": {
        "title": "LVMH – key financials at a glance",
        "subtitle": "Reset FY25 base, then a 15% adj. EPS CAGR through 2028e on cognac "
                    "normalisation, China stabilisation and Sephora compounding",
        "header": ["KEY FINANCIALS (EURm)", "2023", "2024", "2025", "2026e", "2027e", "2028e"],
        "rows": [["Sales", "86,153", "84,683", "78,900", "81,290", "85,760", "90,590"],
                 ["y/y", "8.8%", "(1.7%)", "(6.8%)", "3.0%", "5.5%", "5.6%"],
                 ["Organic growth (%)", "13.3%", "1.0%", "(4.3%)", "2.6%", "5.0%", "5.2%"],
                 ["EBITDA (adj.)", "29,780", "28,460", "26,010", "27,190", "29,320", "31,530"],
                 ["% sales", "34.6%", "33.6%", "33.0%", "33.4%", "34.2%", "34.8%"],
                 ["Rec. EBIT (adj.)", "22,800", "19,570", "16,730", "17,720", "19,380", "21,020"],
                 ["% sales", "26.5%", "23.1%", "21.2%", "21.8%", "22.6%", "23.2%"],
                 ["Net profit (adj.)", "15,170", "12,550", "10,190", "10,790", "11,940", "13,040"],
                 ["EPS, adj. (EUR)", "30.3", "25.1", "20.4", "21.6", "23.9", "26.1"],
                 ["DPS (EUR)", "13.00", "13.00", "12.75", "13.30", "14.70", "16.00"],
                 ["Free cash flow", "8,100", "10,430", "9,020", "9,880", "11,340", "12,790"],
                 ["Net debt (cash)", "10,980", "9,240", "11,410", "9,680", "6,540", "2,910"]],
        "source": "Source: Company data, BNP Paribas Exane (synthetic estimates); shaded years are estimates",
    },
    "segment_details": {
        "title": "Segment details — sales and recurring EBIT margin by division",
        "header": ["Segment (EURm)", "2024", "2025", "2026e", "2027e", "2028e"],
        "rows": [["Fashion & Leather Goods", "41,060", "38,510", "39,470", "41,640", "44,140"],
                 ["   margin", "38.4%", "36.1%", "36.5%", "37.2%", "37.8%"],
                 ["Wines & Spirits", "5,860", "4,910", "5,110", "5,570", "6,020"],
                 ["   margin", "23.5%", "16.8%", "18.9%", "22.0%", "24.0%"],
                 ["Perfumes & Cosmetics", "8,420", "8,290", "8,620", "9,050", "9,500"],
                 ["   margin", "9.5%", "9.2%", "9.6%", "10.1%", "10.6%"],
                 ["Watches & Jewelry", "10,580", "9,870", "10,170", "10,780", "11,430"],
                 ["   margin", "16.9%", "14.8%", "15.4%", "16.5%", "17.4%"],
                 ["Selective Retailing (o/w Sephora)", "18,260", "18,980", "19,930", "21,130", "22,390"],
                 ["   margin", "9.9%", "10.4%", "10.9%", "11.4%", "11.9%"],
                 ["Other & eliminations", "497", "(1,660)", "(2,010)", "(2,410)", "(2,890)"],
                 ["Group sales", "84,683", "78,900", "81,290", "85,760", "90,590"]],
        "source": "Source: Company data, BNP Paribas Exane (synthetic estimates)",
    },
    "consensus_comparison": {
        "title": "LVMH – BNP Paribas Exane vs consensus (2026-28e)",
        "subtitle": "We sit below the street on FY26e (cognac restock timing) and above from FY27e",
        "header": ["LC", "2025", "2026e BNPPE", "Cons.", "Δ", "2027e BNPPE", "Cons.", "Δ",
                   "2028e BNPPE", "Cons.", "Δ"],
        "rows": [["Revenue (EURm)", "78,900", "81,290", "82,140", "-1%", "85,760", "85,340", "0%",
                  "90,590", "89,120", "+2%"],
                 ["Rec. EBIT (EURm)", "16,730", "17,720", "18,050", "-2%", "19,380", "19,010", "+2%",
                  "21,020", "20,290", "+4%"],
                 ["% sales", "21.2%", "21.8%", "22.0%", "-0.2", "22.6%", "22.3%", "+0.3",
                  "23.2%", "22.8%", "+0.4"],
                 ["EPS, adj. (EUR)", "20.4", "21.6", "21.9", "-1%", "23.9", "23.3", "+3%",
                  "26.1", "25.2", "+4%"],
                 ["DPS (EUR)", "12.75", "13.30", "13.40", "-1%", "14.70", "14.30", "+3%",
                  "16.00", "15.40", "+4%"]],
        "source": "Source: Company data, Bloomberg (consensus), BNP Paribas Exane (synthetic estimates)",
    },
    "forecast_changes": {
        "title": "Changes to forecasts",
        "header": ["LC", "2026e NEW", "OLD", "Δ", "2027e NEW", "OLD", "Δ", "2028e NEW", "OLD", "Δ"],
        "rows": [["Revenue (EURm)", "81,290", "84,110", "-3%", "85,760", "88,420", "-3%",
                  "90,590", "92,880", "-2%"],
                 ["EBITDA (adj.)", "27,190", "28,690", "-5%", "29,320", "30,660", "-4%",
                  "31,530", "32,700", "-4%"],
                 ["Rec. EBIT (rep.)", "17,720", "19,050", "-7%", "19,380", "20,560", "-6%",
                  "21,020", "22,050", "-5%"],
                 ["EBIT margin", "21.8%", "22.6%", "-0.8", "22.6%", "23.3%", "-0.7",
                  "23.2%", "23.7%", "-0.5"],
                 ["EPS (rep.)", "21.6", "23.2", "-7%", "23.9", "25.4", "-6%",
                  "26.1", "27.5", "-5%"]],
        "source": "Source: BNP Paribas Exane (synthetic estimates), Company data for reported figures",
    },
    # -- valuation section ----------------------------------------------------
    "dcf": {
        "title": "LVMH – DCF model",
        "assumptions": "2.5% terminal growth, 23.5% mid-cycle EBIT margin and a WACC of 8.0%. "
                       "At our TP, MC would trade on 18.0x EV/EBIT 2027e, in line with its "
                       "10-year pre-2021 average.",
        "table": {
            "header": ["Next FY end 31/12/26", "2026e", "2027e", "2028e", "2029e", "2030e",
                       "2031e", "2032e", "TV"],
            "rows": [["Sales", "81,290", "85,760", "90,590", "95,480", "100,160", "104,570", "108,750", ""],
                     ["y/y", "3.0%", "5.5%", "5.6%", "5.4%", "4.9%", "4.4%", "4.0%", "2.5%"],
                     ["EBIT", "17,720", "19,380", "21,020", "22,440", "23,740", "24,880", "25,890", ""],
                     ["% sales", "21.8%", "22.6%", "23.2%", "23.5%", "23.7%", "23.8%", "23.8%", ""],
                     ["NOPLAT", "12,580", "13,760", "14,920", "15,930", "16,860", "17,660", "18,380", ""],
                     ["D&A", "8,120", "8,390", "8,680", "8,990", "9,290", "9,580", "9,860", ""],
                     ["Capex", "(4,880)", "(5,150)", "(5,430)", "(5,730)", "(6,010)", "(6,270)", "(6,530)", ""],
                     ["Change in WCR", "(690)", "(740)", "(790)", "(830)", "(860)", "(880)", "(900)", ""],
                     ["Free Cash Flow", "10,050", "11,180", "12,290", "13,270", "14,190", "15,000", "15,720", "293,610"],
                     ["Present Value FCF", "9,660", "9,950", "10,120", "10,110", "10,010", "9,790", "9,500", "164,730"]],
        },
        "summary_rows": [["Phase I (2026-32e)", "69,140", "29%"],
                         ["Terminal value", "164,730", "71%"],
                         ["Enterprise value", "233,870", ""],
                         ["-/- Net financial debt (YE25)", "(11,410)", ""],
                         ["-/- Net pension & lease liability", "(15,890)", ""],
                         ["-/- Minority interests", "(1,540)", ""],
                         ["+ Associates + other", "830", ""],
                         ["Equity value", "305,860", ""],
                         ["NOSH (m)", "497.0", ""],
                         ["Value per share (EUR)", "615", ""]],
        "wacc_matrix": {
            "title": "Sensitivity — WACC × terminal growth (EUR per share)",
            "header": ["WACC \\ TV growth", "1.5%", "2.0%", "2.5%", "3.0%", "3.5%"],
            "rows": [["7.0%", "648", "689", "738", "798", "873"],
                     ["7.5%", "601", "634", "673", "720", "777"],
                     ["8.0%", "560", "587", "615", "657", "702"],
                     ["8.5%", "524", "547", "574", "605", "642"],
                     ["9.0%", "492", "511", "533", "559", "589"]],
        },
        "source": "Source: Company data, BNP Paribas Exane (synthetic estimates)",
    },
    "sotp": {
        "title": "LVMH – SOTP valuation (2027e, equity value discounted)",
        "subtitle": "Fashion & Leather Goods contributes c. 70% of the group's enterprise value",
        "header": ["Segment", "EBIT 27e", "Multiple (EV/EBIT)", "Bear", "Base", "Bull"],
        "rows": [["Fashion & Leather Goods", "15,490", "20.0x", "263,300", "309,800", "356,300"],
                 ["Wines & Spirits", "1,230", "14.0x", "13,500", "17,200", "22,100"],
                 ["Perfumes & Cosmetics", "910", "16.0x", "12,700", "14,600", "16,400"],
                 ["Watches & Jewelry", "1,780", "18.0x", "26,700", "32,000", "37,400"],
                 ["Selective Retailing", "2,410", "14.0x", "28,900", "33,700", "38,600"],
                 ["Other & central costs", "(2,440)", "14.0x", "(34,200)", "(34,200)", "(34,200)"],
                 ["Enterprise Value", "", "", "310,900", "373,100", "436,600"],
                 ["-/- Net debt, pensions, leases, minorities", "", "", "(28,000)", "(28,000)", "(28,000)"],
                 ["Equity value", "", "", "282,900", "345,100", "408,600"],
                 ["Value per share (EUR)", "", "", "569", "694", "822"],
                 ["discounted (YE26)", "", "", "527", "620", "761"]],
        "source": "Source: Company data, BNP Paribas Exane (synthetic estimates)",
    },
    "peers": {
        "title": "LVMH – Peer group overview",
        "subtitle": "Our EUR615 target price implies 18.0x/16.5x EV/EBIT 2027/28e for a 15% adj. EPS CAGR",
        "header": ["LC", "EV (EURm)", "Mcap (EURm)", "EV/SALES 27e", "28e",
                   "EV/EBIT 27e", "28e", "P/E 27e", "28e"],
        "rows": [["Hermès*", "222,410", "225,880", "12.1x", "11.0x", "27.9x", "25.2x", "42.1x", "38.3x"],
                 ["Richemont*", "84,120", "89,940", "3.4x", "3.2x", "14.9x", "13.6x", "21.8x", "19.9x"],
                 ["Kering*", "42,880", "28,410", "2.4x", "2.3x", "13.8x", "12.1x", "16.4x", "13.7x"],
                 ["Moncler*", "13,020", "14,110", "4.1x", "3.8x", "13.9x", "12.6x", "19.6x", "17.8x"],
                 ["Swatch Group*", "9,540", "10,120", "1.1x", "1.0x", "9.8x", "8.4x", "13.4x", "11.5x"],
                 ["Burberry*", "4,610", "4,180", "1.5x", "1.4x", "14.2x", "11.8x", "19.9x", "15.6x"],
                 ["Median — Luxury Goods", "", "", "2.9x", "2.8x", "14.1x", "12.4x", "19.8x", "16.7x"],
                 ["LVMH", "302,100", "290,700", "3.4x", "3.2x", "15.4x", "14.1x", "24.5x", "22.4x"],
                 ["LVMH at TP", "", "", "3.7x", "3.5x", "18.0x", "16.5x", "25.7x", "23.6x"]],
        "source": "Source: Refinitiv (synthetic), BNP Paribas Exane estimates; closing prices as of 22 July 2026; "
                  "* consensus-based",
    },
    # -- profile / back page --------------------------------------------------
    "profile": {
        "description": [
            "LVMH is the world's largest luxury group, spanning 75 maisons across Fashion & "
            "Leather Goods (Louis Vuitton, Dior, Celine, Loro Piana), Wines & Spirits (Moët "
            "Hennessy), Perfumes & Cosmetics, Watches & Jewelry (Tiffany, Bulgari, TAG Heuer) "
            "and Selective Retailing (Sephora, DFS).",
            "Fashion & Leather Goods generates c. 49% of sales and c. 75% of recurring EBIT; "
            "Sephora is the group's counter-cyclical engine. The group is family-controlled "
            "(Arnault family c. 49% of capital, c. 64% of voting rights)."],
        "management": [["Bernard Arnault", "Chairman & CEO"],
                       ["Stéphane Bianchi", "Group Managing Director"],
                       ["Cécile Cabanis", "CFO"],
                       ["Rodolphe Ozun", "Investor Relations"]],
        "ownership": [["Arnault Family Group", "48.6%"],
                      ["Free float", "45.3%"],
                      ["Treasury shares", "1.2%"],
                      ["Other", "4.9%"]],
        "sales_by_geo": [["Asia ex-Japan", "30%"], ["United States", "25%"], ["Europe ex-France", "16%"],
                         ["France", "8%"], ["Japan", "7%"], ["Other", "14%"]],
        "calendar": [["14 Oct. 26", "LVMH: Q3 2026 Revenue (17:45 CET)"],
                     ["28 Jan. 27", "LVMH: FY 2026 Results (17:45 CET)"],
                     ["15 Apr. 27", "LVMH: Q1 2027 Revenue (17:45 CET)"],
                     ["16 Apr. 27", "AGM"]],
    },
    "highlights_grid": {
        "title": "Company profile and financial highlights",
        "header": ["Per share data (EUR)", "Dec. 22", "Dec. 23", "Dec. 24", "Dec. 25",
                   "Dec. 26e", "Dec. 27e", "Dec. 28e"],
        "blocks": [
            {"label": "PER SHARE DATA (EUR)",
             "rows": [["EPS, adjusted", "28.1", "30.3", "25.1", "20.4", "21.6", "23.9", "26.1"],
                      ["EPS growth (%)", "17.0", "7.8", "(17.2)", "(18.7)", "5.9", "10.7", "9.2"],
                      ["Net dividend", "12.00", "13.00", "13.00", "12.75", "13.30", "14.70", "16.00"],
                      ["Book value (BVPS)", "112.4", "124.9", "133.6", "139.8", "148.1", "157.3", "167.4"]]},
            {"label": "STOCKMARKET RATIOS",
             "rows": [["P/E (x)", "24.2", "24.2", "25.3", "28.7", "27.1", "24.5", "22.4"],
                      ["Net yield (%)", "1.8", "1.8", "2.0", "2.2", "2.3", "2.5", "2.7"],
                      ["FCF yield (%)", "2.9", "2.3", "3.3", "3.1", "3.4", "3.9", "4.4"],
                      ["EV/Sales (x)", "4.5", "4.4", "3.9", "3.8", "3.7", "3.4", "3.2"],
                      ["EV/EBITDA (x)", "13.0", "12.7", "11.7", "13.9", "13.1", "11.9", "10.9"],
                      ["EV/EBIT (x)", "16.9", "16.6", "17.1", "18.1", "17.0", "15.4", "14.1"]]},
            {"label": "P&L HIGHLIGHTS (EURm)",
             "rows": [["Sales", "79,184", "86,153", "84,683", "78,900", "81,290", "85,760", "90,590"],
                      ["Rec. EBIT, adjusted", "21,055", "22,800", "19,570", "16,730", "17,720", "19,380", "21,020"],
                      ["Net profit, adjusted", "14,080", "15,170", "12,550", "10,190", "10,790", "11,940", "13,040"]]},
            {"label": "CASH FLOW & BALANCE SHEET (EURm)",
             "rows": [["Free cash flow", "7,300", "8,100", "10,430", "9,020", "9,880", "11,340", "12,790"],
                      ["Net debt (cash)", "9,200", "10,980", "9,240", "11,410", "9,680", "6,540", "2,910"],
                      ["Net Debt/EBITDA, adj. (x)", "0.4", "0.4", "0.3", "0.5", "0.4", "0.2", "0.1"],
                      ["ROCE (%)", "17.9", "18.4", "15.6", "14.2", "14.8", "15.9", "17.0"]]},
        ],
        "source": "Source: Company data, BNP Paribas Exane (synthetic estimates). Latest model update: 22 Jul. 26",
    },
    # -- "our investment thesis in six charts" — data for optional chart render
    "six_charts": [
        {"title": "Figure 1: Cognac destocking is the FY25 reset — W&S sales rebase then recover",
         "kind": "bar", "x": ["2023", "2024", "2025", "2026e", "2027e", "2028e"],
         "series": [{"name": "Wines & Spirits sales (EURm)",
                     "values": [6640, 5860, 4910, 5110, 5570, 6020]}],
         "source": "Company data, BNPPE (synthetic)"},
        {"title": "Figure 2: Group organic growth inflects from the FY25 trough",
         "kind": "bar", "x": ["2023", "2024", "2025", "2026e", "2027e", "2028e"],
         "series": [{"name": "Organic growth (%)", "values": [13.3, 1.0, -4.3, 2.6, 5.0, 5.2]}],
         "source": "Company data, BNPPE (synthetic)"},
        {"title": "Figure 3: Recurring EBIT margin rebuilds ~200bp by 2028e",
         "kind": "line", "x": ["2023", "2024", "2025", "2026e", "2027e", "2028e"],
         "series": [{"name": "Rec. EBIT margin (%)", "values": [26.5, 23.1, 21.2, 21.8, 22.6, 23.2]}],
         "source": "Company data, BNPPE (synthetic)"},
        {"title": "Figure 4: Sephora — the counter-cyclical compounding engine",
         "kind": "bar", "x": ["2023", "2024", "2025", "2026e", "2027e", "2028e"],
         "series": [{"name": "Selective Retailing sales (EURm)",
                     "values": [17890, 18260, 18980, 19930, 21130, 22390]}],
         "source": "Company data, BNPPE (synthetic)"},
        {"title": "Figure 5: FCF steps up to c. EUR12.8bn by 2028e (yield 4.4%)",
         "kind": "bar", "x": ["2023", "2024", "2025", "2026e", "2027e", "2028e"],
         "series": [{"name": "FCF (EURm)", "values": [8100, 10430, 9020, 9880, 11340, 12790]}],
         "source": "Company data, BNPPE (synthetic)"},
        {"title": "Figure 6: Valuation de-rated to 17x EV/EBIT 26e vs 22x 10-year average",
         "kind": "line", "x": ["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026e"],
         "series": [{"name": "1Y FW EV/EBIT (x)", "values": [19.5, 23.8, 26.4, 16.9, 16.6, 17.1, 18.1, 17.0]}],
         "source": "Factset (synthetic), BNPPE"},
    ],
    "disclaimer": "SYNTHETIC DEMO DOCUMENT — Unique AI demo material in the BNP Paribas Exane "
                  "house format. All figures are synthetic. Not investment research; not for "
                  "distribution.",
}


# ---------------------------------------------------------------------------
# Company Highlights — the dense full-history data page (à la the machine-generated
# p2/p34 of a real note): ~40 rows × 12 year-columns, GENERATED from base series so
# every ratio reconciles. 2019-24 magnitudes are real-world-plausible history; 2025+
# is the synthetic demo scenario (profit-warning trough, TP EUR615).
# ---------------------------------------------------------------------------
def _gen_highlights_mc() -> dict:
    yrs = ["Dec. 19", "Dec. 20", "Dec. 21", "Dec. 22", "Dec. 23", "Dec. 24",
           "Dec. 25", "Dec. 26e", "Dec. 27e", "Dec. 28e", "Dec. 29e", "Dec. 30e"]
    n = len(yrs)
    cur = 6  # index of Dec. 25 — the shaded "current" column
    nosh = 497.0  # m shares, kept flat
    price = [368.0, 400.0, 626.0, 640.0, 800.0, 662.0, 610.0,
             585.0, 585.0, 585.0, 585.0, 585.0]          # yearly avg; estimates = spot
    sales = [53670, 44651, 64215, 79184, 86153, 84683, 78900,
             81290, 85760, 90590, 95480, 100160]
    ebita = [11504, 8305, 17151, 21055, 22800, 19570, 16730,
             17720, 19380, 21020, 22440, 23740]
    ebitda = [15290, 13070, 22590, 27510, 29780, 28460, 26010,
              27190, 29320, 31530, 33430, 35030]
    eps = [15.3, 9.5, 24.2, 28.1, 30.3, 25.1, 20.4, 21.6, 23.9, 26.1, 27.9, 29.6]
    dps = [6.80, 6.00, 10.00, 12.00, 13.00, 13.00, 12.75, 13.30, 14.70, 16.00, 17.10, 18.20]
    bvps = [72.8, 76.5, 96.3, 112.4, 124.9, 133.6, 139.8, 148.1, 157.3, 167.4, 178.4, 189.8]
    netdebt = [12140, 15690, 9600, 9200, 10980, 9240, 11410,
               9680, 6540, 2910, -890, -4930]
    capex = [3294, 2478, 3550, 4969, 5305, 5100, 4740, 4880, 5150, 5430, 5730, 6010]
    fcf = [6100, 4900, 12000, 7300, 8100, 10430, 9020, 9880, 11340, 12790, 13270, 14190]
    organic = [10.0, -16.0, 36.0, 17.0, 13.3, 1.0, -4.3, 2.6, 5.0, 5.2, 5.0, 4.5]
    other_ev = 15200.0  # pensions + leases + minorities − associates, held ~flat

    dep = [ebitda[i] - ebita[i] for i in range(n)]
    netpro = [eps[i] * nosh for i in range(n)]
    mcap = [price[i] * nosh for i in range(n)]
    ev = [mcap[i] + netdebt[i] + other_ev for i in range(n)]
    nopat = [ebita[i] * 0.74 for i in range(n)]
    opfcf = [fcf[i] + 1450 for i in range(n)]
    equity = [bvps[i] * nosh for i in range(n)]
    tax = [-(ebita[i] - 780) * 0.26 for i in range(n)]
    divpaid = [-(dps[i - 1] if i else 6.0) * nosh for i in range(n)]
    capemp = [equity[i] + netdebt[i] + 6300 for i in range(n)]

    def n0(v):  # thousands separators, parentheses for negatives
        return f"({abs(v):,.0f})" if v < 0 else f"{v:,.0f}"

    def x1(v):
        return f"({abs(v):.1f})" if v < 0 else f"{v:.1f}"

    def row(name, vals, fmt=n0):
        return [name, *[fmt(v) for v in vals]]

    def rowx(name, vals):
        return row(name, vals, x1)

    def blank_first(r):  # first-year change figures are meaningless — show "-"
        r[1] = "-"
        return r

    sections = [
        {"label": "PER SHARE DATA (EUR)", "rows": [
            rowx("EPS restated", eps),
            blank_first(rowx("% change", [0 if i == 0 else (eps[i] / eps[i - 1] - 1) * 100 for i in range(n)])),
            rowx("Book value (BVPS)", bvps),
            rowx("Net dividend", dps),
        ]},
        {"label": "STOCKMARKET RATIOS", "rows": [
            rowx("P/E (P/EPS restated)", [price[i] / eps[i] for i in range(n)]),
            rowx("P/CF (x)", [mcap[i] / (netpro[i] + dep[i]) for i in range(n)]),
            rowx("FCF yield (%)", [fcf[i] / mcap[i] * 100 for i in range(n)]),
            rowx("P/BVPS (x)", [price[i] / bvps[i] for i in range(n)]),
            rowx("Net yield (%)", [dps[i] / price[i] * 100 for i in range(n)]),
            rowx("Payout (%)", [dps[i] / eps[i] * 100 for i in range(n)]),
        ]},
        {"label": "ENTERPRISE VALUE (EURm)", "rows": [
            row("Market cap", mcap),
            row("+ Adjusted net debt", netdebt),
            row("+ Other liabilities and commitments", [other_ev] * n),
            row("= Enterprise value", ev),
            rowx("EV / Sales (x)", [ev[i] / sales[i] for i in range(n)]),
            rowx("EV / Restated EBITDA (x)", [ev[i] / ebitda[i] for i in range(n)]),
            rowx("EV / Restated EBITA (x)", [ev[i] / ebita[i] for i in range(n)]),
            rowx("EV / NOPAT (x)", [ev[i] / nopat[i] for i in range(n)]),
            rowx("EV / OpFCF (x)", [ev[i] / opfcf[i] for i in range(n)]),
        ]},
        {"label": "P&L HIGHLIGHTS (EURm)", "rows": [
            row("Sales", sales),
            row("Restated EBITDA", ebitda),
            row("Depreciation", [-d for d in dep]),
            row("Restated EBITA", ebita),
            row("Net financial income (charges)", [-780] * n),
            row("Tax", tax),
            row("Minorities", [-490] * n),
            row("Net attributable profit restated", netpro),
        ]},
        {"label": "CASH FLOW HIGHLIGHTS (EURm)", "rows": [
            row("EBITDA (reported)", ebitda),
            row("Change in WCR", [-620] * n),
            row("Operating cash flow", [ebitda[i] - 620 - abs(tax[i]) for i in range(n)]),
            row("Capex", [-c for c in capex]),
            row("Operating free cash flow (OpFCF)", opfcf),
            row("Free cash flow", fcf),
            row("Dividends paid", divpaid),
            blank_first(row("Increase (decrease) in net financial debt",
                [netdebt[i] - netdebt[i - 1] if i else 0 for i in range(n)])),
        ]},
        {"label": "BALANCE SHEET HIGHLIGHTS (EURm)", "rows": [
            row("Restated capital employed, incl. gross goodwill", capemp),
            row("Shareholders' funds, group share", equity),
            row("Net financial debt (cash)", netdebt),
        ]},
        {"label": "FINANCIAL RATIOS (%)", "rows": [
            blank_first(rowx("Sales (% change)", [0 if i == 0 else (sales[i] / sales[i - 1] - 1) * 100 for i in range(n)])),
            rowx("Organic sales growth", organic),
            blank_first(rowx("Restated EBITA (% change)", [0 if i == 0 else (ebita[i] / ebita[i - 1] - 1) * 100 for i in range(n)])),
            rowx("Restated EBITDA margin", [ebitda[i] / sales[i] * 100 for i in range(n)]),
            rowx("Restated EBITA margin", [ebita[i] / sales[i] * 100 for i in range(n)]),
            rowx("Tax rate", [26.0] * n),
            rowx("Net margin", [netpro[i] / sales[i] * 100 for i in range(n)]),
            rowx("Capex / Sales", [capex[i] / sales[i] * 100 for i in range(n)]),
            rowx("OpFCF / Sales", [opfcf[i] / sales[i] * 100 for i in range(n)]),
            rowx("Gearing", [netdebt[i] / equity[i] * 100 for i in range(n)]),
            rowx("ROE", [netpro[i] / equity[i] * 100 for i in range(n)]),
            rowx("ROCE", [nopat[i] / capemp[i] * 100 for i in range(n)]),
            rowx("WACC", [8.0] * n),
        ]},
    ]
    # a smooth-ish synthetic monthly price path for the chart (deterministic wiggle)
    import math
    monthly, rel = [], []
    for i in range(n - 5):  # chart history: 2019 → 2025 (+ spot)
        p0, p1 = price[i], price[min(i + 1, n - 1)]
        for m in range(12):
            t = m / 12.0
            base = p0 + (p1 - p0) * t
            monthly.append(round(base * (1 + 0.06 * math.sin((i * 12 + m) * 0.9)), 1))
            rel.append(round(base * 0.92 * (1 + 0.04 * math.cos((i * 12 + m) * 0.7)), 1))
    monthly.append(585.0)
    rel.append(538.0)
    return {
        "columns": yrs, "current_col": cur, "estimates_from": 7,
        "sections": sections,
        "price_row": ["Price (yearly avg from Dec. 19 to Dec. 25)", *[f"{p:,.1f}" for p in price]],
        "header_block": {
            "price_line": "Price at 22 Jul. 26 / 12m Target Price",
            "price_values": "EUR585.0 / EUR615  +5%",
            "listing": "Refinitiv / Bloomberg: LVMH.PA / MC FP",
            "company_line": "LVMH (Outperform)",
            "sector_line": "Luxury Goods | France",
            "highlights": [["Enterprise value (EURm)", "302,100"],
                           ["Market capitalisation (EURm)", "290,745"],
                           ["Free float (EURm)", "150,200"],
                           ["3m average volume (EURm)", "412.6"]],
            "performance": {"header": ["Performance (%)", "1m", "3m", "12m"],
                            "rows": [["Absolute", "(4)", "2", "(12)"],
                                     ["Rel. Luxury Goods", "(2)", "(1)", "(8)"],
                                     ["Rel. MSCI Europe", "(3)", "0", "(10)"]]},
            "hilo": "12m Hi/Lo (EUR): 705.0 -17% / 549.0 +7%",
            "cagr": "CAGR 2002/2025: EPS restated +9% · CFPS +8%",
        },
        "chart": {"monthly": monthly, "rel": rel, "target": 615.0, "spot": 585.0,
                  "years": [y.replace("Dec. ", "") for y in yrs[:7]]},
        "footnote": "(a) Restated for capital gains/losses, exceptional restructuring, "
                    "capitalized R&D; EBITA adjusted for impairments and amortisation of "
                    "intangibles from M&A. All figures SYNTHETIC — demo. "
                    "Latest model update: 22 Jul. 26",
    }


_MC_FP["highlights_full"] = _gen_highlights_mc()

NOTE_PACKS: dict[str, dict] = {"MC FP": _MC_FP}


def get_pack(ticker: str, coverage_row: dict | None = None) -> dict:
    """Full pack when seeded; else a partial cover-only pack from the coverage row."""
    if ticker in NOTE_PACKS:
        return NOTE_PACKS[ticker]
    if not coverage_row:
        return {"full": False, "error": f"no note pack and no coverage for '{ticker}'"}
    c = coverage_row
    return {
        "full": False,
        "meta": {"company": c["name"], "ticker": c["ticker"], "ccy": c["ccy"],
                 "sector_label": c["sector"].upper(),
                 "country_subsector": f"— / {c['sector']}"},
        "header": {"rating": c["rating"].upper(),
                   "price_label": f"{c['ccy']}{c['price']:.1f}",
                   "price_asof": "latest close (synthetic)",
                   "tp_label": f"{c['ccy']}{c['target_price']:.0f}",
                   "upside_label": (f"UPSIDE {c['upside_pct']:.0f}%" if c["upside_pct"] >= 0
                                    else f"DOWNSIDE {abs(c['upside_pct']):.0f}%"),
                   "horizon": "12m"},
        "note": "Partial pack — cover header only (full pack not seeded for this name). "
                "Sufficient for a FLASH note; initiation/revision need the full pack.",
        "disclaimer": _MC_FP["disclaimer"],
    }
