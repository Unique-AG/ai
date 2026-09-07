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

from ..models.bing_agent_search_request_search_freshness_type_0 import (
    BingAgentSearchRequestSearchFreshnessType0,
)
from ..models.bing_agent_search_request_search_market_type_0 import (
    BingAgentSearchRequestSearchMarketType0,
)
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
        search_market (BingAgentSearchRequestSearchMarketType0 | None | Unset): Region and language Bing should favour,
            as `<language>-<country>`. Examples: `de-CH`, `fr-CH`, `fr-FR`. This biases the results rather than restricting
            them — sources from other regions can still appear. Set it when the space serves one country; left blank, the
            deployment default applies, or Bing guesses from the caller if there is none. [Supported `mkt`
            values](https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/bing-web-search/reference/market-
            codes)
        search_freshness (BingAgentSearchRequestSearchFreshnessType0 | None | Unset): Drops anything Bing discovered
            before a cut-off, counted back from each search. Unlike the region, this really does filter, and it applies to
            **every** search in the space — set it only for news spaces, since elsewhere it hides older pages that are still
            correct. [Accepted `freshness` values](https://learn.microsoft.com/en-us/previous-versions/bing/search-
            apis/bing-web-search/reference/query-parameters#freshness)
    """

    query: str
    engine: Literal["bing"] | Unset = "bing"
    generation_instructions: str | Unset = (
        "You are an Expert Web Research Agent whose goal is to extract the MAXIMUM amount of detail from every source you find.\n\n## Core Directives\n1. **Search broadly** — issue multiple searches with varied keywords and phrasings to cover every angle of the query.\n2. **Read every source thoroughly** — do NOT skim. Extract every relevant fact, figure, statistic, date, name, quote, and piece of context.\n3. **One entry per source** — each source gets its own result object. Never merge information from different sources into a single entry.\n4. **Preserve detail** — prefer verbosity over brevity. Include specific numbers, full names, exact dates, and direct quotes whenever available. Do NOT paraphrase away precision.\n5. **No omissions** — if a source contains relevant information, it MUST appear in your output. When in doubt, include it.\n"
    )
    timeout: int | Unset = 120
    fetch_size: int | Unset = 5
    search_market: BingAgentSearchRequestSearchMarketType0 | None | Unset = UNSET
    search_freshness: BingAgentSearchRequestSearchFreshnessType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        generation_instructions = self.generation_instructions

        timeout = self.timeout

        fetch_size = self.fetch_size

        search_market: None | str | Unset
        if isinstance(self.search_market, Unset):
            search_market = UNSET
        elif isinstance(self.search_market, BingAgentSearchRequestSearchMarketType0):
            search_market = self.search_market.value
        else:
            search_market = self.search_market

        search_freshness: None | str | Unset
        if isinstance(self.search_freshness, Unset):
            search_freshness = UNSET
        elif isinstance(
            self.search_freshness, BingAgentSearchRequestSearchFreshnessType0
        ):
            search_freshness = self.search_freshness.value
        else:
            search_freshness = self.search_freshness

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
        if search_market is not UNSET:
            field_dict["searchMarket"] = search_market
        if search_freshness is not UNSET:
            field_dict["searchFreshness"] = search_freshness

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

        def _parse_search_market(
            data: object,
        ) -> BingAgentSearchRequestSearchMarketType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                search_market_type_0 = BingAgentSearchRequestSearchMarketType0(data)

                return search_market_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(BingAgentSearchRequestSearchMarketType0 | None | Unset, data)

        search_market = _parse_search_market(d.pop("searchMarket", UNSET))

        def _parse_search_freshness(
            data: object,
        ) -> BingAgentSearchRequestSearchFreshnessType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                search_freshness_type_0 = BingAgentSearchRequestSearchFreshnessType0(
                    data
                )

                return search_freshness_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(BingAgentSearchRequestSearchFreshnessType0 | None | Unset, data)

        search_freshness = _parse_search_freshness(d.pop("searchFreshness", UNSET))

        bing_agent_search_request = cls(
            query=query,
            engine=engine,
            generation_instructions=generation_instructions,
            timeout=timeout,
            fetch_size=fetch_size,
            search_market=search_market,
            search_freshness=search_freshness,
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
