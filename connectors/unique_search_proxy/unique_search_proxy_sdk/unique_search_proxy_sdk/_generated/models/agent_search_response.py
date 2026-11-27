from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.answer_span_citation import AnswerSpanCitation


T = TypeVar("T", bound="AgentSearchResponse")


@_attrs_define
class AgentSearchResponse:
    """Result of an agent-based (grounded) search.

    Thin egress contract: opaque ``answer`` text from the provider, the
    citations the provider attached to it, and ``raw`` for debugging. Consumers
    interpret ``answer`` (JSON parsing, mapping citations, etc.).

        Attributes:
            engine (str):
            query (str):
            answer (str | Unset): Agent response text as returned by the provider (opaque to the proxy) Default: ''.
            citations (list[AnswerSpanCitation] | Unset): Sources cited in the answer. Only Grounding with Bing Search
                reports citations; other engines return an empty list.
            raw (Any | Unset): Opaque provider payload
    """

    engine: str
    query: str
    answer: str | Unset = ""
    citations: list[AnswerSpanCitation] | Unset = UNSET
    raw: Any | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        engine = self.engine

        query = self.query

        answer = self.answer

        citations: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.citations, Unset):
            citations = []
            for citations_item_data in self.citations:
                citations_item = citations_item_data.to_dict()
                citations.append(citations_item)

        raw = self.raw

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "engine": engine,
                "query": query,
            }
        )
        if answer is not UNSET:
            field_dict["answer"] = answer
        if citations is not UNSET:
            field_dict["citations"] = citations
        if raw is not UNSET:
            field_dict["raw"] = raw

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.answer_span_citation import AnswerSpanCitation

        d = dict(src_dict)
        engine = d.pop("engine")

        query = d.pop("query")

        answer = d.pop("answer", UNSET)

        _citations = d.pop("citations", UNSET)
        citations: list[AnswerSpanCitation] | Unset = UNSET
        if _citations is not UNSET:
            citations = []
            for citations_item_data in _citations:
                citations_item = AnswerSpanCitation.from_dict(citations_item_data)

                citations.append(citations_item)

        raw = d.pop("raw", UNSET)

        agent_search_response = cls(
            engine=engine,
            query=query,
            answer=answer,
            citations=citations,
            raw=raw,
        )

        agent_search_response.additional_properties = d
        return agent_search_response

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
