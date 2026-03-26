# Complex Test Scenarios for Todo Tracking

Advanced manual test scenarios that exercise multi-phase research with Code Interpreter calculations between phases. These create **genuine sequential dependencies** — the model cannot skip ahead because each Code Interpreter step requires data from prior research, and subsequent research requires the computed results.

## Prerequisites

1. Enable `todo_tracking` in the space's Experimental Settings
2. Enable **Code Interpreter** in the Tools section
3. Use GPT-5.4 as the model
4. Enable trace logging (`ENV=LOCAL`) for debugging

## What Makes These Hard

Unlike the basic scenarios in `todo_tracking.md`, these scenarios have:

- **Research → Compute → Research loops**: Code Interpreter phases act as gates — the model must do the math before it can determine what to research next
- **Dynamic task graphs**: some steps can only be planned after earlier steps return data (e.g., "deep-dive the top 3" requires knowing which 3 emerged)
- **Cross-domain synthesis**: combining data from unrelated domains (ecology + urban planning, finance + technology)
- **Quantitative rigor**: calculations that can't be faked — wrong inputs produce wrong outputs, so the model must actually use the research data

---

## Scenario 1: Urban Oxygen Budget (Zurich)

**Tools exercised:** WebSearch (5×), Code Interpreter (3×)

**Prompt:**

> I want to understand whether Zurich produces enough oxygen from its urban greenery to support its population. Do this analysis step by step:
>
> 1. Search the web for Zurich's urban tree inventory — how many trees does the city have, and what are the dominant species?
> 2. Search the web for oxygen production rates by tree species (kg O₂ per tree per year for the species you found)
> 3. Use Code Interpreter to calculate total annual oxygen production from Zurich's urban trees based on the data from steps 1 and 2
> 4. Search the web for average human oxygen consumption per year (kg O₂ per person per year) and Zurich's current population
> 5. Search the web for Zurich's annual vehicle fuel consumption and the oxygen consumed per liter of fuel combustion
> 6. Use Code Interpreter to calculate the net oxygen balance: production from trees minus consumption from people and vehicles. Express as a surplus or deficit percentage
> 7. Search the web for how Zurich's green coverage has changed over the last 20 years (percentage of green space over time)
> 8. Use Code Interpreter to model how the oxygen balance would change if Zurich hit its 2040 climate target of 50% reduction in vehicle emissions. Plot the current vs projected oxygen balance
> 9. Write a final report with all findings, calculations, data sources, and the projection chart
>
> Each calculation step depends on the research before it — work through these sequentially.

**Why it's hard:**
- 3 Code Interpreter phases that each depend on prior research data
- Step 6 requires outputs from steps 3, 4, and 5
- Step 8 requires outputs from steps 6 and 7
- Calculations can't be faked — wrong tree counts or O₂ rates produce visibly wrong totals

**Expected behavior:**
- Creates 9 todos (or groups into ~6-7 coarser phases)
- Uses WebSearch for steps 1, 2, 4, 5, 7
- Uses Code Interpreter for steps 3, 6, 8 — each must reference actual numbers from prior searches
- Step 8 should produce an actual chart (Code Interpreter matplotlib)
- All items reach terminal state; no mid-execution questions

**What to verify:**
- Code Interpreter inputs reference specific numbers from search results (not placeholders)
- The net balance calculation in step 6 actually uses the tree count × per-tree rate from step 3
- The projection in step 8 uses the historical trend from step 7

---

## Scenario 2: Startup Investment Due Diligence

**Tools exercised:** WebSearch (5×), InternalSearch (1×), Code Interpreter (2×)

**Prompt:**

> I need to evaluate AI infrastructure startups for a potential investment. Do this analysis:
>
> 1. Search the web for the top 10 AI infrastructure startups by recent funding (Series B or later, raised in the last 12 months)
> 2. Pick the top 3 by funding amount. For each of those 3, do a deep web search for: revenue estimates, customer count, key technology differentiators, and founding team background
> 3. Search our internal knowledge base for any existing analysis, meeting notes, or evaluations we have on these companies or this market segment
> 4. Use Code Interpreter to build a weighted comparison matrix scoring each of the 3 companies on: technology (25%), market traction (25%), team (20%), financials (20%), strategic fit (10%). Use the data you gathered — assign 1-5 scores with justification
> 5. Search the web for the top risks in the AI infrastructure market right now (regulatory, competitive, technical)
> 6. For the highest-scoring company from step 4, do a deeper web search for any red flags: lawsuits, executive departures, customer complaints, or negative press
> 7. Use Code Interpreter to build a risk-adjusted score: take the weighted scores from step 4 and apply risk discounts based on the market risks (step 5) and company-specific risks (step 6). Show the before/after comparison
> 8. Write an investment memo with executive summary, company profiles, scoring methodology, risk analysis, and a clear recommendation
>
> Important: the companies that emerge from step 1 determine everything that follows — you can't plan the specifics until you see the search results.

**Why it's hard:**
- **Dynamic task graph**: step 1's output determines which companies appear in steps 2-3 and 6
- The model can't pre-populate company names in its todo list — it must adapt as data arrives
- Step 4 requires synthesizing qualitative research into quantitative scores
- Step 7 layers risk adjustments on top of step 4's scores using step 5 and 6 data

**Expected behavior:**
- Initial todos may be generic ("research top AI infra startups"); after step 1, todos should reference specific companies
- Uses WebSearch for steps 1, 2, 5, 6; InternalSearch for step 3; Code Interpreter for steps 4, 7
- The comparison matrix in step 4 must use actual data from step 2, not generic placeholders
- The risk-adjusted scores in step 7 should visibly differ from step 4's scores

**What to verify:**
- Todo list evolves: items added or updated after step 1 returns specific companies
- Code Interpreter in step 4 receives actual research data as input (check trace logs)
- Risk discount in step 7 references specific risks from steps 5 and 6

---

## Scenario 3: Cross-Country Market Entry Analysis

**Tools exercised:** WebSearch (7-9×), InternalSearch (1×), Code Interpreter (2×)

**Prompt:**

> We're evaluating market entry into three countries for our enterprise AI product: Japan, Brazil, and Germany. Do a comprehensive analysis:
>
> 1. For each country (Japan, Brazil, Germany), search the web for: market size for enterprise AI solutions, growth rate, and number of enterprises with 500+ employees
> 2. For each country, search the web for: AI-related regulations, data residency requirements, and any restrictions on foreign AI companies
> 3. Search our internal knowledge base for any existing market research, expansion plans, or partner discussions related to these countries
> 4. Search the web for our top 3 competitors' presence in each of these markets — who's already there and what's their market share?
> 5. Use Code Interpreter to calculate TAM, SAM, and SOM for each country using the data from steps 1 and 4. Show a side-by-side comparison table and a bar chart
> 6. For each country, search the web for typical localization costs: translation, local hiring, legal entity setup, and data center costs
> 7. Use Code Interpreter to build a 3-year ROI model for each country: projected revenue (from SAM penetration curve), minus localization and operational costs from step 6. Include a break-even timeline for each country
> 8. Write an executive briefing with country profiles, regulatory summary, competitive landscape, financial projections, and a recommended entry sequence (which country first, second, third) with rationale
>
> Keep the data organized by country throughout — don't mix countries within steps.

**Why it's hard:**
- **Parallel-within-sequential**: 3 countries × multiple research dimensions, but the financial modeling depends on all research being done first
- Many web searches that must stay organized (the model needs to track which country's data it has vs. hasn't collected)
- TAM/SAM/SOM calculation requires combining market size data with competitive presence data
- ROI model requires both the SAM numbers and the localization costs
- The final recommendation must be justified by the quantitative analysis, not hand-waved

**Expected behavior:**
- Creates todos organized by phase (not by country) — e.g., "research market size for all 3 countries" rather than 3 separate items per data point
- Or creates todos by country with sub-phases — either organization is acceptable
- Code Interpreter in step 5 produces an actual comparison table and chart
- Code Interpreter in step 7 produces 3-year projections with break-even dates
- Final recommendation references specific numbers from the ROI model

**What to verify:**
- No country is skipped in any research phase
- TAM/SAM/SOM numbers in step 5 trace back to market size data from step 1
- ROI model in step 7 uses localization costs from step 6, not made-up numbers
- Recommendation in step 8 is consistent with the ROI model's rankings

---

## Scenario 4: Technical Architecture Benchmark

**Tools exercised:** WebSearch (4×), InternalSearch (1×), Code Interpreter (2×)

**Prompt:**

> We need to choose an analytical database for our new data platform. Compare ClickHouse, Apache Druid, and DuckDB:
>
> 1. Search the web for performance benchmarks comparing these three databases — query latency, ingestion throughput, and compression ratios from published benchmarks (ClickBench, independent tests, vendor benchmarks)
> 2. For each database, search the web for: licensing model, community size (GitHub stars, contributors), enterprise support options, and managed cloud offerings
> 3. Search our internal knowledge base for any previous evaluations, POCs, or discussions about analytical databases
> 4. Use Code Interpreter to normalize the performance data from step 1 into comparable scores (0-100 scale). Handle the fact that different benchmarks use different query sets — document your normalization methodology. Create a radar chart showing each database's profile across the performance dimensions
> 5. Search the web for production case studies of each database at companies with similar scale to ours (100M+ rows, <500ms p99 latency requirement, 5-10 concurrent users)
> 6. Use Code Interpreter to build a weighted decision matrix. Weights: query performance (30%), ingestion speed (15%), operational complexity (20%), cost (15%), community/support (10%), scalability (10%). Assign scores based on all research gathered. Then run a sensitivity analysis — vary each weight by ±10% and show which databases' rankings are stable vs. fragile. Output as a table and chart
> 7. Write an Architecture Decision Record (ADR) with: context, decision drivers, options considered, pros/cons for each, decision outcome, and consequences. Include the quantitative analysis as supporting evidence
>
> The decision must be defended by the numbers, not by gut feeling.

**Why it's hard:**
- **Quantitative rigor**: normalization methodology in step 4 must be explicit and defensible
- **Sensitivity analysis** in step 6 prevents hand-wavy recommendations — if the top pick changes when weights shift slightly, the model must flag that
- The ADR format is structured — the model must produce a real decision document, not a generic comparison
- Internal knowledge (step 3) may contradict external benchmarks — the model needs to reconcile or note discrepancies

**Expected behavior:**
- Creates 7 todos matching the steps
- Code Interpreter in step 4 explains its normalization approach (not just "I normalized the data")
- Code Interpreter in step 6 produces a sensitivity analysis showing which rankings are robust
- The ADR in step 7 has proper sections (Context, Decision Drivers, Options, Decision, Consequences)

**What to verify:**
- Normalization methodology in step 4 is explicit (e.g., "min-max scaling across benchmarks" or "percentile ranking")
- Sensitivity analysis in step 6 actually varies weights and shows the impact on rankings
- ADR recommendation is consistent with the decision matrix outcome
- If sensitivity analysis shows the top pick is fragile, the ADR acknowledges this

---

## Scenario 5: Remote Work Trend Analysis with Forecasting

**Tools exercised:** WebSearch (5×), InternalSearch (1×), Code Interpreter (2-3×)

**Prompt:**

> I need a comprehensive analysis of remote work trends with forward-looking projections. Do this research and analysis:
>
> 1. Search the web for remote work adoption rates by region (North America, Europe, Asia-Pacific) from 2019 to present — get specific percentages by year if possible
> 2. Search the web for the economic effects of remote work: impact on commercial real estate, productivity studies, salary adjustments for remote workers, and migration patterns
> 3. Use Code Interpreter to plot the remote work adoption curves by region from the data in step 1. Calculate the compound annual growth rate (CAGR) for each region. Identify inflection points (pre-COVID, COVID peak, post-COVID stabilization)
> 4. Search the web for the latest effects of remote work on: employee productivity (controlled studies), office vacancy rates in major cities, and salary differential between remote and in-office roles
> 5. Search our internal knowledge base for our company's remote work policy, hiring data, and any employee survey results related to remote work
> 6. Search the web for expert forecasts and research reports on remote work trends for 2026-2030 — what do McKinsey, Gartner, Stanford WFH Research, and similar sources project?
> 7. Use Code Interpreter to build three projection scenarios for remote work adoption through 2030:
>    - Bull case: remote-first becomes dominant (use the highest growth trajectory)
>    - Base case: hybrid stabilization (use the post-COVID plateau rate)
>    - Bear case: return-to-office mandates accelerate (use the declining trajectory from recent RTO data)
>    Plot all three scenarios on a single chart with confidence bands. Calculate the percentage of knowledge workers remote in each scenario by 2030
> 8. Write a comprehensive analysis report with: historical trends with charts, economic impact summary, our company's position relative to the market, three-scenario projections with charts, and strategic recommendations for our workforce planning
>
> The projections in step 7 must be grounded in the actual data from steps 1-6, not generic estimates.

**Why it's hard:**
- **Historical data processing**: step 3 must work with real (potentially messy) adoption rate data from multiple sources
- **CAGR calculation** requires actual numbers — the model can't just say "growth was strong"
- **Three-scenario modeling** in step 7 requires: (a) extracting growth rates from the historical data, (b) using expert forecasts as anchors, (c) producing actual projections, not hand-waves
- **Chart generation**: steps 3 and 7 should produce actual matplotlib/plotly charts via Code Interpreter
- Combines sociology, economics, and technology — the synthesis in step 8 must connect disparate findings

**Expected behavior:**
- Creates 8 todos (or groups into ~6 phases)
- Code Interpreter in step 3 produces adoption curve plots with CAGR annotations
- Code Interpreter in step 7 produces a multi-line projection chart with confidence bands
- The report in step 8 references specific numbers from the analysis (e.g., "CAGR of X% in North America")
- Internal search results in step 5 are incorporated into the final recommendations

**What to verify:**
- CAGR calculation in step 3 uses actual data points from step 1 (not made-up numbers)
- Projection scenarios in step 7 are distinguishable — the bull, base, and bear cases should produce meaningfully different numbers
- Charts are actually generated (check Code Interpreter output for base64 images or file references)
- Final report references specific data from all prior steps, not just generic observations

---

## Scoring Rubric (for all scenarios)

When evaluating a test run, check each dimension:

| Dimension | Pass | Partial | Fail |
|-----------|------|---------|------|
| **Todo creation** | Creates todos covering all major steps | Creates todos but misses some steps | No todos created, or fewer than 3 |
| **Sequential execution** | Each step uses data from prior steps | Some steps reference prior data, some don't | Steps are independent / data doesn't flow |
| **Code Interpreter usage** | CI receives actual research data as input | CI runs but with generic/placeholder data | CI not used, or calculations are in prose |
| **Autonomous execution** | Completes all steps without asking mid-task | Asks once but continues after | Stops mid-execution to ask for confirmation |
| **Completion** | All items reach terminal state | Most items completed, 1-2 left | Multiple items left pending or in_progress |
| **Report quality** | Final output cites specific numbers from analysis | Final output references analysis generally | Final output is generic / doesn't use gathered data |

## Tips for Testers

- **Check traces** at `/tmp/unique-ai-traces/` — the per-iteration JSON files show exactly what data flowed between steps
- **Look at Code Interpreter inputs** — do they contain actual numbers from web search results, or placeholder/generic values?
- **Time the full run** — these scenarios may take 3-5 minutes each. That's expected
- **If the model asks for clarification**, that's a partial failure for these scenarios (they're designed to be self-contained). Exception: the model may reasonably ask about "our company" in scenarios 2, 3, 5 — respond with generic context
- **If context overflows**, note which step it happened at. These scenarios are designed to push limits but should complete within 128K tokens with GPT-5.4
