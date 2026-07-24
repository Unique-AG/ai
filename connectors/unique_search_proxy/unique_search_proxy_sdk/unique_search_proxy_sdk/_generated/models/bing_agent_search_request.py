from __future__ import annotations

from collections.abc import Mapping
from typing import (
    Any,
    Literal,
    TypeVar,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="BingAgentSearchRequest")


@_attrs_define
class BingAgentSearchRequest:
    r"""
    Attributes:
        query (str): Search query string
        engine (Literal['bing'] | Unset): Provider discriminator; must be `bing` for this config. Default: 'bing'.
        generation_instructions (str | Unset): Instructions injected into the grounding agent. Default: 'You are an
            Expert Web Research Agent whose goal is to extract the MAXIMUM amount of detail from every source you
            find.\n\n## Core Directives\n1. **Search broadly** — issue multiple searches with varied keywords and phrasings
            to cover every angle of the query.\n2. **Read every source thoroughly** — do NOT skim. Extract every relevant
            fact, figure, statistic, date, name, quote, and piece of context.\n3. **One entry per source** — each source
            gets its own result object. Never merge information from different sources into a single entry.\n4. **Preserve
            detail** — prefer verbosity over brevity. Include specific numbers, full names, exact dates, and direct quotes
            whenever available. Do NOT paraphrase away precision.\n5. **No omissions** — if a source contains relevant
            information, it MUST appear in your output. When in doubt, include it.\n'.
        timeout (int | Unset): Request timeout in seconds (agent runs can be slow). Default: 120.
        fetch_size (int | Unset): Maximum number of Bing grounding results per query Default: 5.
        agent_id (None | str | Unset): Foundry agent name/id. Resolved from deployment env when not set. When empty, the
            service auto-provisions or looks up a grounding agent.
    """

    query: str
    engine: Literal["bing"] | Unset = "bing"
    generation_instructions: str | Unset = (
        "You are an Expert Web Research Agent whose goal is to extract the MAXIMUM amount of detail from every source you find.\n\n## Core Directives\n1. **Search broadly** — issue multiple searches with varied keywords and phrasings to cover every angle of the query.\n2. **Read every source thoroughly** — do NOT skim. Extract every relevant fact, figure, statistic, date, name, quote, and piece of context.\n3. **One entry per source** — each source gets its own result object. Never merge information from different sources into a single entry.\n4. **Preserve detail** — prefer verbosity over brevity. Include specific numbers, full names, exact dates, and direct quotes whenever available. Do NOT paraphrase away precision.\n5. **No omissions** — if a source contains relevant information, it MUST appear in your output. When in doubt, include it.\n"
    )
    timeout: int | Unset = 120
    fetch_size: int | Unset = 5
    agent_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        generation_instructions = self.generation_instructions

        timeout = self.timeout

        fetch_size = self.fetch_size

        agent_id: None | str | Unset
        if isinstance(self.agent_id, Unset):
            agent_id = UNSET
        else:
            agent_id = self.agent_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if engine is not UNSET:
            field_dict["engine"] = engine
        if generation_instructions is not UNSET:
            field_dict["generationInstructions"] = generation_instructions
        if timeout is not UNSET:
            field_dict["timeout"] = timeout
        if fetch_size is not UNSET:
            field_dict["fetchSize"] = fetch_size
        if agent_id is not UNSET:
            field_dict["agentId"] = agent_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["bing"] | Unset, d.pop("engine", UNSET))
        if engine != "bing" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'bing', got '{engine}'")

        generation_instructions = d.pop("generationInstructions", UNSET)

        timeout = d.pop("timeout", UNSET)

        fetch_size = d.pop("fetchSize", UNSET)

        def _parse_agent_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        agent_id = _parse_agent_id(d.pop("agentId", UNSET))

        bing_agent_search_request = cls(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            fetch_size=fetch_size,
            agent_id=agent_id,
        )

        bing_agent_search_request.additional_properties = d
        return bing_agent_search_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
