from __future__ import annotations

import json
import typing
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model
from unidecode import unidecode
from unique_toolkit.content.schemas import ContentChunk

from unique_web_search.services.search_engine.base import SearchEngineMode


class WebSearchToolParameters(BaseModel):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(extra="forbid")
    query: str
    date_restrict: str | None

    @classmethod
    def from_tool_parameter_query_description(
        cls, query_description: str, date_restrict_description: str | None
    ) -> type["WebSearchToolParameters"]:
        """Create a new model with the query field."""
        return create_model(
            cls.__name__,
            query=(str, Field(description=query_description)),
            date_restrict=(
                str | None,
                Field(description=date_restrict_description),
            ),
            __base__=cls,
        )


class StepType(StrEnum):
    SEARCH = "search"
    READ_URL = "read_url"


_STEP_QUERY_DESCRIPTION_STANDARD = (
    "The input for this step: either an optimized search query "
    "(for search steps) or a URL to read (for read_url steps)."
)

_STEP_QUERY_DESCRIPTION_AGENT = (
    "For search steps, provide a single, comprehensive description of the "
    "user's full intent: what information they need, the context of their "
    "question, and relevant background. Combine all related information "
    "needs into this one description — the search engine handles query "
    "optimization and source diversification internally. "
    "For read_url steps, provide the URL to read."
)


class Step(BaseModel):
    step_type: Literal[StepType.SEARCH, StepType.READ_URL]
    objective: str = Field(description="The objective of the step")
    query_or_url: str = Field(
        description=_STEP_QUERY_DESCRIPTION_STANDARD,
    )


class WebSearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(description="The objective of the plan")
    query_analysis: str = Field(
        description="Analysis of the user's query and what information is needed"
    )
    steps: list[Step] = Field(description="Steps to execute")
    expected_outcome: str = Field(description="Expected outcome")

    @classmethod
    def with_search_engine_mode(
        cls, mode: SearchEngineMode
    ) -> type[WebSearchPlan]:
        """Build a ``WebSearchPlan`` variant whose ``Step.query_or_url``
        description is tailored to the search-engine mode."""
        if mode == SearchEngineMode.AGENT:
            query_desc = _STEP_QUERY_DESCRIPTION_AGENT
        else:
            query_desc = _STEP_QUERY_DESCRIPTION_STANDARD

        DynamicStep = create_model(
            "Step",
            __base__=Step,
            query_or_url=(str, Field(description=query_desc)),
        )
        return create_model(
            cls.__name__,
            __base__=cls,
            steps=(list[DynamicStep], Field(description="Steps to execute")),
        )

    @classmethod
    def schema_hint(cls, mode: SearchEngineMode) -> str:
        """Return a prompt-friendly JSON block whose values are the field
        descriptions of the (possibly dynamic) plan model.

        The ``query_or_url`` value automatically reflects the search-engine
        mode so the LLM sees the right guidance.
        """
        PlanModel = cls.with_search_engine_mode(mode)

        steps_inner_type = typing.get_args(
            PlanModel.model_fields["steps"].annotation
        )[0]

        step_hint: dict[str, str] = {}
        for name, field in steps_inner_type.model_fields.items():
            if name == "step_type":
                step_hint[name] = "search | read_url"
            else:
                step_hint[name] = field.description or name

        plan_hint: dict[str, object] = {}
        for name, field in PlanModel.model_fields.items():
            if name == "steps":
                plan_hint[name] = [step_hint]
            else:
                plan_hint[name] = field.description or name

        return json.dumps(plan_hint, indent=2)

    @staticmethod
    def build_example_simple(mode: SearchEngineMode) -> WebSearchPlan:
        """Build a simple one-step example plan, adapted to *mode*."""
        if mode == SearchEngineMode.AGENT:
            query = (
                "I need to find current weather conditions, temperature, "
                "and the short-term forecast for New York City today"
            )
        else:
            query = "New York City weather today current conditions"

        return WebSearchPlan(
            objective="Get current weather information for New York City",
            query_analysis=(
                "Need current weather conditions, temperature, "
                "and forecast for NYC"
            ),
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find current weather conditions in NYC",
                    query_or_url=query,
                )
            ],
            expected_outcome=(
                "Current temperature, weather conditions, "
                "and short-term forecast for NYC"
            ),
        )

    @staticmethod
    def build_example_complex(mode: SearchEngineMode) -> WebSearchPlan:
        """Build a multi-step example plan, adapted to *mode*.

        In agent mode the search engine performs comprehensive research
        internally, so we consolidate into a single search step.
        """
        if mode == SearchEngineMode.AGENT:
            return WebSearchPlan(
                objective=(
                    "Research Tesla's recent financial performance "
                    "and market position"
                ),
                query_analysis=(
                    "Need latest quarterly results, stock performance, "
                    "and competitive analysis to understand Tesla's "
                    "current market position. A single comprehensive "
                    "search is sufficient because the search engine "
                    "performs its own research internally."
                ),
                steps=[
                    Step(
                        step_type=StepType.SEARCH,
                        objective=(
                            "Find Tesla's latest earnings, stock performance, "
                            "and competitive position"
                        ),
                        query_or_url=(
                            "I need a comprehensive overview of Tesla's recent "
                            "financial performance: latest quarterly earnings "
                            "results and key metrics, current TSLA stock price "
                            "and recent price trends, and how Tesla compares "
                            "to competitors in the EV market."
                        ),
                    ),
                ],
                expected_outcome=(
                    "Comprehensive view of Tesla's financial health, "
                    "stock performance, and market position"
                ),
            )

        return WebSearchPlan(
            objective=(
                "Research Tesla's recent financial performance "
                "and market position"
            ),
            query_analysis=(
                "Need latest quarterly results, stock performance, "
                "and competitive analysis to understand Tesla's "
                "current market position"
            ),
            steps=[
                Step(
                    step_type=StepType.SEARCH,
                    objective="Find Tesla's latest quarterly earnings",
                    query_or_url="Tesla Q3 2024 earnings results financial performance",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Get current Tesla stock price and recent performance",
                    query_or_url="Tesla stock price TSLA recent performance 2024",
                ),
                Step(
                    step_type=StepType.READ_URL,
                    objective="Read detailed earnings report",
                    query_or_url="[URL from previous search results]",
                ),
            ],
            expected_outcome=(
                "Comprehensive view of Tesla's financial health, "
                "stock performance, and market position"
            ),
        )


    @staticmethod
    def build_example_fsi(mode: SearchEngineMode) -> WebSearchPlan:
        """Build an FSI-themed example plan (used by V3), adapted to *mode*.

        In agent mode the search engine researches comprehensively on its
        own, so the 5-query domain-rotation pattern collapses into a single
        well-described search step.
        """
        if mode == SearchEngineMode.AGENT:
            steps = [
                Step(
                    step_type=StepType.SEARCH,
                    objective=(
                        "Comprehensive FSI research on Nvidia in asset management"
                    ),
                    query_or_url=(
                        "I need a thorough overview of Nvidia's latest "
                        "developments and their relevance to the asset "
                        "management industry: new GPU/AI products aimed "
                        "at financial workloads, partnerships with asset "
                        "managers or fintech firms, and analyst commentary "
                        "from major financial news outlets."
                    ),
                ),
            ]
        else:
            steps = [
                Step(
                    step_type=StepType.SEARCH,
                    objective="Get broad FSI context on Nvidia",
                    query_or_url="Nvidia latest developments asset management",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Run the exact same Nvidia query against a first set of financial and news domains",
                    query_or_url="Nvidia latest developments asset management reuters.com ft.com bloomberg.com wsj.com cnbc.com",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Run the exact same Nvidia query against a second set of financial and analysis domains",
                    query_or_url="Nvidia latest developments asset management marketwatch.com forbes.com barrons.com morningstar.com fool.com",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Run the exact same Nvidia query against a third set of market and investing domains",
                    query_or_url="Nvidia latest developments asset management businessinsider.com yahoo.com investing.com seekingalpha.com nasdaq.com",
                ),
                Step(
                    step_type=StepType.SEARCH,
                    objective="Run the exact same Nvidia query against a fourth set of technology and business domains",
                    query_or_url="Nvidia latest developments asset management theinformation.com techcrunch.com venturebeat.com wired.com economist.com",
                ),
            ]

        if mode == SearchEngineMode.AGENT:
            query_analysis = (
                "The user is asking about Nvidia in an FSI context. The "
                "strongest inferred FSI interpretation is asset management. "
                "A single comprehensive search is sufficient because the "
                "search engine researches broadly on its own."
            )
            expected_outcome = (
                "Comprehensive overview of Nvidia's relevance and recent "
                "developments in the asset management space"
            )
        else:
            query_analysis = (
                "The user is asking about Nvidia in an FSI context. The strongest "
                "inferred FSI interpretation is asset management, so query 1 already "
                "includes that wording. Queries 2-5 repeat the core intent and vary "
                "the preferred website domains. Each follow-up query contains "
                "5 different website domains."
            )
            expected_outcome = (
                "A broad overview first, followed by four searches that repeat "
                "the core intent with different sets of preferred website domains"
            )

        return WebSearchPlan(
            objective="Understand Nvidia's relevance in Financial Services",
            query_analysis=query_analysis,
            steps=steps,
            expected_outcome=expected_outcome,
        )


class StepDebugInfo(BaseModel):
    step_name: str
    execution_time: float
    config: str | dict
    extra: dict = Field(default_factory=dict)


class WebPageChunk(BaseModel):
    url: str
    display_link: str
    title: str
    snippet: str
    content: str
    order: str

    def to_content_chunk(self) -> "ContentChunk":
        """Convert WebPageChunk to ContentChunk format."""

        # Convert to ascii
        title = unidecode(self.title)
        name = f'{self.display_link}: "{title}"'

        return ContentChunk(
            id=name,
            text=self.content,
            order=int(self.order),
            start_page=None,
            end_page=None,
            key=name,
            chunk_id=self.order,
            url=self.url,
            title=name,
        )


class WebSearchDebugInfo(BaseModel):
    parameters: dict
    steps: list[StepDebugInfo] = []
    web_page_chunks: list[WebPageChunk] = []
    execution_time: float | None = None
    num_chunks_in_final_prompts: int = 0

    def model_dump(self, *, with_debug_details: bool = True, **kwargs):
        """
        Dump the model, dropping `additional_info` in steps when debug=False.
        """
        exclude = kwargs.pop("exclude", {})
        if not with_debug_details:
            # Build an exclude structure that applies to all steps
            exclude = {
                "steps": {i: {"extra"} for i in range(len(self.steps))},
                "web_page_chunks": True,
            } | exclude
        return super().model_dump(exclude=exclude, **kwargs)
