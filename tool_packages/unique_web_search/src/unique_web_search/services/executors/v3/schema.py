"""V3 WebSearch tool parameters: exactly one of ``search`` or ``fetch_urls`` per call."""

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WebSearchV3SearchPayload(BaseModel):
    """Run a web search; results return as content chunks (e.g. snippets)."""

    model_config = ConfigDict(extra="forbid")
    query: str = Field(description="Search query for the configured search engine.")


class WebSearchV3FetchUrlsPayload(BaseModel):
    """Fetch full pages for the given URLs (user-supplied or from a prior ``search``)."""

    model_config = ConfigDict(extra="forbid")
    urls: list[str] = Field(
        min_length=1,
        description="HTTP(S) URLs to crawl.",
    )


class WebSearchV3ToolParameters(BaseModel):
    """Root JSON for the V3 WebSearch tool: set exactly one of ``search`` or ``fetch_urls``."""

    model_config = ConfigDict(extra="forbid")

    user_intent: str = Field(
        description=(
            "Fill this first, before any other root field. The user's underlying goal: what they want to know, "
            "decide, or verify, in plain language (the 'why'). This is not an execution plan—avoid steps like "
            "'run a search' or 'look up X then Y'. Keep it stable when you use several WebSearch calls for the "
            "same task: reuse the same `user_intent` across those calls and vary only `objective` and the "
            "payload to cover each part."
        )
    )

    task_complexity: Literal["simple", "complex"] = Field(
        description=(
            "Stable across all calls for the same `user_intent`. Set to 'simple' when the user's goal is a "
            "single, narrow factual ask coverable by ONE search query (or one `fetch_urls` when URLs are "
            "given): single fact, single entity, single timeframe. Set to 'complex' when the goal involves "
            "multiple distinct facts, comparisons across entities, multiple timeframes, or otherwise "
            "independent sub-questions that should be split into separate `search` calls. Repeat the SAME "
            "value on every follow-up call for this `user_intent`."
        )
    )
    sub_questions: list[str] = Field(
        default_factory=list,
        description=(
            "Empty list when `task_complexity`='simple'. When 'complex', the full decomposition of the user "
            "task into 2-5 self-contained sub-questions, each answerable by its own `search` query. Repeat "
            "the SAME list on every call for this `user_intent`; vary only `objective` so each call's "
            "`objective` points at the sub-question this call covers. Do NOT bundle multiple sub-questions "
            "into one query."
        ),
    )

    objective: str = Field(
        description=(
            "This invocation only: the sub-goal or information slice for this call (one search query or one "
            "URL batch). Contrast with `user_intent`: if the task is complex, use one shared `user_intent` and "
            "a different `objective` + `search.query` (or `fetch_urls`) per part. For `action`=`search`, name "
            "the facet this `search.query` is meant to satisfy; for `action`=`fetch_urls`, state why these "
            "specific URLs answer the need right now."
        )
    )

    action: Literal["search", "fetch_urls"] = Field(
        description=(
            "The operation for this call; it must match which block you populate. Use `search` when you "
            "set `search` (SERP / snippets) and set `fetch_urls` to `null`. Use `fetch_urls` when you set "
            "`fetch_urls` (crawl those URLs) and set `search` to `null`. Must not contradict the non-null payload."
        )
    )
    
    search: WebSearchV3SearchPayload | None = Field(
        description="Use the search engine: snippets / SERP rows. Explicitly set to `None` if `fetch_urls` was used in the same call.",
    )
    fetch_urls: WebSearchV3FetchUrlsPayload | None = Field(
        description="Fetch and process full page content for specific URLs. Explicitly set to `None` if `search` was used in the same call.",
    )

    @model_validator(mode="before")
    @classmethod
    def add_none_if_used_in_same_call(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "search" in data and "fetch_urls" not in data:
            data["fetch_urls"] = None
        elif "fetch_urls" in data and "search" not in data:
            data["search"] = None
        return data

    @model_validator(mode="after")
    def exactly_one_of_search_or_fetch_and_action(self) -> Self:
        n = (self.search is not None) + (self.fetch_urls is not None)
        if n != 1:
            msg = "Exactly one of 'search' or 'fetch_urls' must be set."
            raise ValueError(msg)
        if self.search is not None and self.action != "search":
            msg = "When `search` is set, `action` must be 'search'."
            raise ValueError(msg)
        if self.fetch_urls is not None and self.action != "fetch_urls":
            msg = "When `fetch_urls` is set, `action` must be 'fetch_urls'."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def sub_questions_match_task_complexity(self) -> Self:
        if self.task_complexity == "complex" and len(self.sub_questions) < 2:
            msg = (
                "When `task_complexity`='complex', `sub_questions` must contain at least 2 "
                "self-contained sub-questions (the decomposition of the user task)."
            )
            raise ValueError(msg)
        if self.task_complexity == "simple" and self.sub_questions:
            msg = (
                "When `task_complexity`='simple', `sub_questions` must be empty; the user task "
                "is coverable by a single `search` (or `fetch_urls`) call."
            )
            raise ValueError(msg)
        return self
