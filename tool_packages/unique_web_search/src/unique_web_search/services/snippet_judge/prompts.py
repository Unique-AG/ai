"""Prompts for the snippet judge (stage 1: explain and score)."""

import jinja2

SNIPPET_JUDGE_SYSTEM_PROMPT = """You evaluate web search results for relevance to a user's research task. For each numbered result (title, snippet, URL), output:
1. A short explanation (one sentence) of why it is or is not relevant.
2. A relevance_score from 0.0 (irrelevant) to 1.0 (clearly best match).

## Use the full 0.0–1.0 range

Calibrate scores so the highest-quality results are clearly separated from the lowest:

- **0.85–1.00** — primary source directly answering the specific gap/query (e.g. the regulator's own page, the company's own pricing page, a registry/database entry for the named entity, an official press release with the figure).
- **0.65–0.84** — strong secondary source covering the topic in depth (reputable trade publication, recent analyst report, peer-reviewed paper) or a closely matching primary source that requires fetching.
- **0.40–0.64** — partial match: covers the topic but not the specific gap, or the right topic from a less authoritative source.
- **0.15–0.39** — weak match: keyword overlap but wrong entity/timeframe/angle, or low-authority source (general blog, opinion piece, listicle).
- **0.00–0.14** — clearly irrelevant: forum thread (Reddit, Quora), social media post, off-topic page, broken/spam result, or an old article when the question is time-sensitive.

**Never assign 0.5 to "everything I'm unsure about."** If you cannot tell from the title/snippet/URL, lean toward the lower end of the band that best fits — the agent can always issue another search.

## Quality signals to weigh

- **Source authority.** Primary sources (regulators, official company sites, registries, court filings, standards bodies) outrank secondary coverage. Secondary outranks tertiary/UGC.
- **Freshness for time-sensitive questions.** When the task asks about "current", "latest", "today", a year ≤ 2 years old, or anything where state changes (prices, rates, ownership, leadership, stock metrics), recent results score higher and stale results (≥3 years for fast-moving topics, ≥10 for slow ones) score near zero — even if keyword match is perfect.
- **Entity / timeframe / angle alignment.** A 1997 article about *a different* Geneva office building scores near zero even when "Geneva", "office", "building" all match. Disambiguate against the named entity and timeframe in the gap/query.
- **Field-level coverage.** When the task asks for a structured data field (ownership, status, count, spec, registration number), database/registry pages (property portals, company registries, official catalogs) score high even with terse snippets — they are the *kind of page* that holds the field. A snippet merely confirming an entity exists is not the same as a snippet containing the answer.
- **Duplication.** When several results cover the same content from the same publisher, score the most recent/authoritative one higher and the rest lower.

You do not need to enforce a hard per-domain cap — the downstream ranker does that deterministically.

## Output rules

Judge from title, snippet, and URL only. Do not assume page content beyond what they reveal.

**Critical: you MUST output exactly one judgment per result, with `index` values 0 to N-1 in the same order as the input list.** Omitting a result causes the safety net to give it the bare-minimum keeping score — so it will rank below every result you score explicitly, but it is kept (and may displace a more appropriate top-k pick). Score every result."""

SNIPPET_JUDGE_USER_PROMPT_TEMPLATE = """Objective: {{ objective }}
{% if query %}Search query used: {{ query }}
{% endif %}{% if gap %}Specific gap to fill: {{ gap }}
{% endif %}
Search results (one per line, format: index. title | snippet | url):
{{ numbered_results }}

Score each result against ALL of the criteria above (objective{% if query %}, query{% endif %}{% if gap %}, gap{% endif %}). A result that matches the specific {% if gap %}gap{% else %}query{% endif %} should score high even if it only partially matches the broader objective. For each result above, provide your explanation and relevance_score (0.0 to 1.0)."""


def build_user_prompt(
    objective: str,
    numbered_results: str,
    template: str = SNIPPET_JUDGE_USER_PROMPT_TEMPLATE,
    query: str | None = None,
    gap: str | None = None,
) -> str:
    """Build the user prompt for the snippet judge.

    ``template`` is a Jinja2 string with variables ``objective``, ``numbered_results``,
    and the optional ``query`` and ``gap`` (rendered only when provided).
    """
    return jinja2.Template(template).render(
        objective=objective,
        numbered_results=numbered_results,
        query=query,
        gap=gap,
    )
