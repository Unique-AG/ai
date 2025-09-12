from enum import StrEnum
from typing import Optional

from pydantic import ConfigDict, Field
from unique_toolkit import LanguageModelService
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel
from unique_toolkit.language_model import (
    LanguageModelName,
)
from unique_toolkit.language_model.builder import MessagesBuilder

RESTRICT_DATE_DESCRIPTION = """
Restricts results to a recent time window. Format: `[period][number]` — `d`=days, `w`=weeks, `m`=months, `y`=years.  
Examples: `d1` (24h), `w1` (1 week), `m3` (3 months), `y1` (1 year).  
Omit for no date filter. Avoid adding date terms in the main query.
"""

PLANNER_SYSTEM_PROMPT = """
You are an expert web research planner. Your task is to create a comprehensive plan to answer a user's query using web search and URL reading capabilities.

** Planning Guidelines **
- Break down complex queries into logical, sequential steps
- Each step should have a clear objective and specific search strategy
- Consider different types of information sources (news, academic, official sites, forums, etc.)
- Plan for iterative refinement based on initial findings
- Include verification steps for controversial or critical information
- Consider temporal aspects (recent vs. historical information)
- Plan for synthesizing information from multiple sources

** Step Types Available **
1. **SEARCH**: Perform web search with specific queries
2. **READ_URL**: Read content from specific URLs
3. **VERIFY**: Cross-check information from multiple sources
4. **SYNTHESIZE**: Combine and analyze gathered information
5. **FOLLOW_UP**: Search for additional information based on initial findings

** Search Strategy Guidelines **
- Use specific, targeted queries rather than broad searches
- Consider using advanced search operators when beneficial:
  - Use quotes `"..."` for exact phrases
  - Use `-word` to exclude terms
  - Use `site:domain.com` to restrict to specific sites
  - Use `intitle:`, `inurl:` to target title/URL
  - Use `OR` for alternatives, `*` as wildcards
  - Use `..` for number ranges (e.g., 2010..2020)
  - Use `AROUND(N)` to find terms close together
- Plan multiple search angles for comprehensive coverage
- Include date restrictions when temporal relevance is important

** Important Considerations **
- Always start with broad searches, then narrow down
- Plan for fact-checking and source verification
- Consider the user's intent and context
- Anticipate potential gaps in information
- Plan backup strategies if initial searches fail
- Consider multiple perspectives on controversial topics

{mode_instructions}
""".strip()


class PlanningMode(StrEnum):
    """Different modes of planning complexity."""

    COMPREHENSIVE = "comprehensive"  # Full multi-step planning with verification
    FOCUSED = "focused"  # Targeted planning for specific topics
    QUICK = "quick"  # Simple, direct planning for straightforward queries


class StepType(StrEnum):
    """Types of steps in a research plan."""

    SEARCH = "search"  # Perform web search
    READ_URL = "read_url"  # Read specific URLs
    VERIFY = "verify"  # Cross-check information
    SYNTHESIZE = "synthesize"  # Combine information
    FOLLOW_UP = "follow_up"  # Additional searches based on findings

step_type_to_name = {
    StepType.SEARCH: "**Web search**",
    StepType.READ_URL: "**Read URL**",
    StepType.VERIFY: "**Verify Information**",
    StepType.SYNTHESIZE: "**Synthesize**",
    StepType.FOLLOW_UP: "**Generating Follow-up Questions**",
}

class SearchStep(StructuredOutputModel):
    """A single step in the research plan."""
    model_config = ConfigDict(extra="forbid")
    
    step_type: StepType = Field(description="The type of step to perform")
    objective: str = Field(
        description="Clear description of what this step aims to achieve"
    )
    query: Optional[str] = Field(
        default=None,
        description="Search query to use (required for SEARCH and FOLLOW_UP steps)",
    )
    urls: Optional[list[str]] = Field(
        default=None, description="Specific URLs to read (required for READ_URL steps)"
    )
    restrict_date: Optional[str] = Field(
        default=None, description=RESTRICT_DATE_DESCRIPTION
    )
    priority: int = Field(
        description="Priority level (1=highest, 5=lowest) for this step", ge=1, le=5
    )
    depends_on: Optional[list[int]] = Field(
        default=None,
        description="List of step indices this step depends on (0-indexed)",
    )


class ResearchPlan(StructuredOutputModel):
    """A comprehensive research plan to answer a user query."""
    model_config = ConfigDict(extra="forbid")
    
    query_analysis: str = Field(
        description="Analysis of the user's query and what information is needed"
    )
    search_strategy: str = Field(
        description="Overall strategy for gathering the required information"
    )
    steps: list[SearchStep] = Field(
        description="Ordered list of steps to execute the research plan", min_length=1
    )
    expected_outcome: str = Field(
        description="What kind of answer or information this plan should produce"
    )


async def create_research_plan(
    query: str,
    language_model_service: LanguageModelService,
    language_model: LanguageModelName,
    mode: PlanningMode = PlanningMode.FOCUSED,
    context: Optional[str] = None,
) -> ResearchPlan:
    """
    Create a comprehensive research plan to answer a user's query using web search capabilities.

    Args:
        query: The user's query that needs to be answered
        language_model_service: The language model service to use
        language_model: The specific language model to use
        mode: The planning mode (comprehensive, focused, or quick)
        context: Optional additional context about the query

    Returns:
        A detailed research plan with steps to gather information
    """
    # Build the prompt based on the mode
    mode_instructions = _get_mode_instructions(mode)

    user_message = f"User Query: {query}"
    if context:
        user_message += f"\n\nAdditional Context: {context}"

    messages = (
        MessagesBuilder()
        .system_message_append(
            PLANNER_SYSTEM_PROMPT.format(mode_instructions=mode_instructions)
        )
        .user_message_append(user_message)
        .build()
    )

    response = await language_model_service.complete_async(
        messages,
        model_name=language_model.name,
        structured_output_model=ResearchPlan,
        structured_output_enforce_schema=True,
    )

    parsed_response = response.choices[0].message.parsed
    if parsed_response is None:
        raise ValueError("Failed to parse research plan from LLM response")

    return ResearchPlan.model_validate(parsed_response)


def _get_mode_instructions(mode: PlanningMode) -> str:
    """Get specific instructions based on the planning mode."""
    if mode == PlanningMode.COMPREHENSIVE:
        return """
** COMPREHENSIVE MODE **
Create a thorough, multi-step research plan with:
- 5-8 detailed steps including verification and synthesis
- Multiple search angles and perspectives
- Cross-referencing and fact-checking steps
- Consideration of different source types and viewpoints
- Backup strategies for complex or controversial topics
""".strip()
    elif mode == PlanningMode.FOCUSED:
        return """
** FOCUSED MODE **
Create a targeted research plan with:
- 3-5 focused steps directly addressing the query
- Strategic searches for the most relevant information
- Basic verification for important claims
- Clear path from search to synthesis
""".strip()
    else:  # QUICK mode
        return """
** QUICK MODE **
Create a streamlined research plan with:
- 2-3 direct steps to answer the query
- Efficient searches targeting the most likely sources
- Minimal but essential verification
- Quick path to actionable information
""".strip()
