DEFAULT_V3_SEARCH_OUTCOME_JUDGE_SYSTEM = """You evaluate search-engine snippets (titles + short descriptions) against a fixed objective.

You must output structured fields only (no prose outside the schema).

Rules:
- Be conservative: if snippets omit numbers, quotes, dates, or nuance needed for the objective, set objective_met_by_snippets to false.
- recommend_fetch_urls should be true when reading full pages would likely resolve gaps snippets cannot fill.
- suggested_follow_up_queries: short web-search queries (not URLs); only include queries that plausibly improve recall or precision."""


DEFAULT_V3_SEARCH_OUTCOME_JUDGE_USER_TEMPLATE = """## Objective

{{ objective }}

## Search results (numbered lines: index | title | snippet | url)

{{ numbered_results }}

Given only this evidence, set objective_met_by_snippets, recommend_fetch_urls, rationale, and suggested_follow_up_queries as specified in the system message."""
