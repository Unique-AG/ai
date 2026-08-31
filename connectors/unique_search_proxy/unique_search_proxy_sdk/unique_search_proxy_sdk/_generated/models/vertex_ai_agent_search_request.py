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

T = TypeVar("T", bound="VertexAiAgentSearchRequest")


@_attrs_define
class VertexAiAgentSearchRequest:
    r"""
    Attributes:
        query (str): Search query string
        engine (Literal['vertexai'] | Unset): Provider discriminator; must be `vertexai` for this config. Default:
            'vertexai'.
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
        vertexai_model_name (str | Unset): Gemini model name for grounded generation Default: 'gemini-3-flash-preview'.
        enable_enterprise_search (bool | Unset): Use enterprise web search grounding tool instead of Google Search
            Default: False.
    """

    query: str
    engine: Literal["vertexai"] | Unset = "vertexai"
    generation_instructions: str | Unset = (
        "You are an Expert Web Research Agent whose goal is to extract the MAXIMUM amount of detail from every source you find.\n\n## Core Directives\n1. **Search broadly** — issue multiple searches with varied keywords and phrasings to cover every angle of the query.\n2. **Read every source thoroughly** — do NOT skim. Extract every relevant fact, figure, statistic, date, name, quote, and piece of context.\n3. **One entry per source** — each source gets its own result object. Never merge information from different sources into a single entry.\n4. **Preserve detail** — prefer verbosity over brevity. Include specific numbers, full names, exact dates, and direct quotes whenever available. Do NOT paraphrase away precision.\n5. **No omissions** — if a source contains relevant information, it MUST appear in your output. When in doubt, include it.\n"
    )
    timeout: int | Unset = 120
    vertexai_model_name: str | Unset = "gemini-3-flash-preview"
    enable_enterprise_search: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        generation_instructions = self.generation_instructions

        timeout = self.timeout

        vertexai_model_name = self.vertexai_model_name

        enable_enterprise_search = self.enable_enterprise_search

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
        if vertexai_model_name is not UNSET:
            field_dict["vertexaiModelName"] = vertexai_model_name
        if enable_enterprise_search is not UNSET:
            field_dict["enableEnterpriseSearch"] = enable_enterprise_search

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["vertexai"] | Unset, d.pop("engine", UNSET))
        if engine != "vertexai" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'vertexai', got '{engine}'")

        generation_instructions = d.pop("generationInstructions", UNSET)

        timeout = d.pop("timeout", UNSET)

        vertexai_model_name = d.pop("vertexaiModelName", UNSET)

        enable_enterprise_search = d.pop("enableEnterpriseSearch", UNSET)

        vertex_ai_agent_search_request = cls(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            vertexai_model_name=vertexai_model_name,
            enable_enterprise_search=enable_enterprise_search,
        )

        vertex_ai_agent_search_request.additional_properties = d
        return vertex_ai_agent_search_request

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
