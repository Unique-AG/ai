"""Agent-engine grounding turned into the same SERP evidence every arm stores.

An agent engine (Vertex AI, Grounding with Bing) grounds *and* drafts a full
answer in one `/v1/agent-search` call, so it has no SERP. To keep the pipeline
downstream of fetch identical for every arm, its grounded answer is folded into
a single :class:`SerpResult`, which the shared answerer (`answer_bench.py`) then
condenses into the short graded answer — same answerer model as everywhere else.

Shared by `serp_bench.py` (agent arms interleaved with the SERP arms) and
`agent_bench.py` (agent arms only).
"""

from __future__ import annotations

from serp_records import SerpResult
from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput

#: Engines reached via `/v1/agent-search` rather than `/v1/search`.
AGENT_ENGINES = frozenset(engine.value for engine in AgentEngineType)

_EVIDENCE_TITLES = {
    AgentEngineType.VERTEXAI.value: "Vertex AI grounded answer",
    AgentEngineType.BING.value: "Bing grounded answer",
}

# generation_instructions that steer the agent to draft one COMPLETE grounded
# answer. This aligns with the proxy's comprehensive output schema (no terseness
# conflict); the shared answerer handles brevity downstream.
GROUNDING_INSTRUCTIONS = """\
You are a grounded research agent. Using web search, answer the user's question \
as completely and accurately as possible. Return a SINGLE result whose \
`detailed_answer` is your full answer — include every fact, date, name, and \
figure needed for it to be correct and unambiguous. Put the discrete supporting \
facts in `key_facts` and cite your main source in `source_url`/`source_title`. \
If web search does not contain the answer, say so in `detailed_answer`."""


def grounded_answer_to_evidence(raw_answer: str, *, engine: str) -> list[SerpResult]:
    """The proxy pins agent engines to a results-list schema; fold it into a
    single evidence blob (the full grounded answer). Falls back to raw text if
    the payload is not the expected JSON (e.g. a provider that answers in
    prose)."""
    title = _EVIDENCE_TITLES.get(engine, f"{engine} grounded answer")
    try:
        parsed = AgentSearchOutput.model_validate_json(raw_answer)
    except ValueError:
        text = raw_answer.strip()
        return [SerpResult(url="", title=title, snippet=text)] if text else []
    blocks = [
        "\n".join([item.detailed_answer.strip(), *(f"- {k}" for k in item.key_facts)])
        for item in parsed.results
        if item.detailed_answer.strip() or item.key_facts
    ]
    answer_text = "\n\n".join(block.strip() for block in blocks).strip()
    if not answer_text:
        return []
    primary_url = parsed.results[0].source_url if parsed.results else ""
    return [SerpResult(url=primary_url, title=title, snippet=answer_text)]


__all__ = [
    "AGENT_ENGINES",
    "GROUNDING_INSTRUCTIONS",
    "grounded_answer_to_evidence",
]
