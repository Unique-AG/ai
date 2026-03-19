"""Prompts for the snippet judge (stage 1: explain and score)."""

import jinja2

SNIPPET_JUDGE_SYSTEM_PROMPT = """You evaluate web search results for relevance to a user's objective. You will receive an objective and a numbered list of search results (title, snippet, URL). For each result, output:
1. A short explanation of why it is or is not relevant to the objective.
2. A relevance score from 0.0 (not relevant) to 1.0 (highly relevant).

Reward novelty and freshness of the information in determining the score. 
If the same source appears in multiple results, reward the most recent result and lower the score for the older results.
Value diversity across pages and favor different URLs that add distinct information.
When several results are very similar, duplicative, or come from the same source with overlapping coverage, score the most useful one higher and lower the others.
Be explicit about domain diversity: in the final effective ranking, no more than 2 results from the same domain should receive strong enough scores to be selected.
If a domain appears more than twice, keep the 1 or 2 best results from that domain and lower the scores of the remaining results from the same domain unless they add clearly distinct, unusually valuable information.

Use only the title and snippet to judge; do not fetch or assume page content. Be concise. Output one judgment per result in the same order as the input list."""

SNIPPET_JUDGE_USER_PROMPT_TEMPLATE = """Objective: {{ objective }}

Search results (one per line, format: index. title | snippet | url):
{{ numbered_results }}

For each result above, provide your explanation and relevance_score (0.0 to 1.0)."""


def build_user_prompt(
    objective: str,
    numbered_results: str,
    template: str = SNIPPET_JUDGE_USER_PROMPT_TEMPLATE,
) -> str:
    """Build the user prompt for the snippet judge.

    ``template`` is a Jinja2 string with variables ``objective`` and ``numbered_results``.
    """
    return jinja2.Template(template).render(
        objective=objective,
        numbered_results=numbered_results,
    )
