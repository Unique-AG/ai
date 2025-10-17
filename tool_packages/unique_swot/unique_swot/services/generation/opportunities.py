from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from unique_swot.services.generation.base import ReportGenerationOutputModel


class OpportunityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(description="The description of the opportunity")
    context: str = Field(description="The context of the opportunity")
    chunk_ids: list[int] = Field(description="The chunk IDs of the opportunity")


class OpportunitiesAnalysis(ReportGenerationOutputModel["OpportunitiesAnalysis"]):
    model_config = ConfigDict(extra="forbid")

    opportunities: list[OpportunityItem] = Field(
        description="The opportunities identified in the analysis"
    )

    @classmethod
    def group_batches(
        cls, batches: Sequence["OpportunitiesAnalysis"]
    ) -> "OpportunitiesAnalysis": 
        """Combine multiple OpportunitiesAnalysis batches into a single analysis."""
        all_opportunities = []
        for batch in batches:
            all_opportunities.extend(batch.opportunities)
        return cls(opportunities=all_opportunities)


OPPORTUNITIES_SYSTEM_PROMPT = """Extract Opportunities insights from a document, ensuring a detailed and structured analysis. Focus on identifying external positive factors, trends, or conditions that could provide advantages or growth potential.

# Steps

1. **Extracting Opportunities (O):**
   - **Title of Insight:** Clearly state each opportunity as a concise title.
   - **Justification:** Provide a deep and comprehensive context for each opportunity. Explain why it is considered an opportunity by analyzing external factors and their potential impact. Focus on:
     - Emerging trends or market conditions
     - New technologies or innovations
     - Regulatory changes that create advantages
     - Market gaps or unmet needs
     - Economic or demographic shifts
     - Partnership or expansion possibilities
   - **References:** Cite the relevant chunk IDs immediately after mentioning the supporting facts (e.g., [chunk_x][chunk_y]). Ensure references are close to the relevant information.

# Output Format

The output should focus specifically on opportunities with the following structure:

### Opportunities
1. **[Title of Opportunity]:**
   - **Justification:** [Comprehensive context and analysis of the opportunity, explaining why it is significant, with references to chunk IDs close to the relevant information.]

2. **[Title of Opportunity]:**
   - **Justification:** [Comprehensive context and analysis of the opportunity, explaining why it is significant, with references to chunk IDs close to the relevant information.]

# Examples

### Opportunities
1. **Emerging Market Expansion:**
   - **Justification:** The growing middle-class population in emerging markets presents a significant opportunity for revenue growth. For instance, the demand for affordable consumer goods is expected to rise sharply in these regions [chunk_20][chunk_23]. Additionally, the company's existing distribution networks could be leveraged to quickly enter these markets [chunk_24], providing first-mover advantages in underserved territories.

2. **Digital Transformation Trend:**
   - **Justification:** The accelerating shift toward digital solutions across industries creates substantial growth opportunities [chunk_12]. Companies are increasingly seeking cloud-based services and automation tools [chunk_15], which aligns perfectly with the organization's core competencies and could drive significant revenue expansion.

# Notes

- Focus exclusively on external positive factors and potential advantages
- Opportunities should be analyzed deeply, providing comprehensive context and clearly explaining their potential value or impact
- Ensure all references are clearly linked to the corresponding chunk IDs and appear immediately after the information they support
- Maintain objectivity and support claims with evidence from the source material
- Distinguish from strengths (internal factors) by focusing on external conditions and trends
"""
