from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from unique_swot.services.generation.base import ReportGenerationOutputModel


class StrengthItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(description="The description of the strength")
    context: str = Field(description="The context of the strength")
    chunk_ids: list[int] = Field(description="The chunk IDs of the strength")


class StrengthsAnalysis(ReportGenerationOutputModel):
    model_config = ConfigDict(extra="forbid")

    strengths: list[StrengthItem] = Field(
        description="The strengths identified in the analysis"
    )

    @classmethod
    def group_batches(
        cls, batches: Sequence["StrengthsAnalysis"]
    ) -> "StrengthsAnalysis":  # type: ignore[override]
        """Combine multiple StrengthsAnalysis batches into a single analysis."""
        all_strengths = []
        for batch in batches:
            all_strengths.extend(batch.strengths)
        return cls(strengths=all_strengths)


STRENGTHS_SYSTEM_PROMPT = """Extract Strengths insights from a document, ensuring a detailed and structured analysis. Focus on identifying internal positive attributes, capabilities, or advantages that benefit the subject and contribute to achieving goals.

# Steps

1. **Extracting Strengths (S):**
   - **Title of Insight:** Clearly state each strength as a concise title.
   - **Justification:** Provide a detailed explanation of how each strength benefits the subject and contributes to achieving goals. Focus on:
     - Internal capabilities and resources
     - Competitive advantages
     - Unique assets or competencies
     - Proven track records or achievements
   - **References:** Cite the relevant chunk IDs immediately after mentioning the supporting facts (e.g., [chunk_x][chunk_y]).

# Output Format

The output should focus specifically on strengths with the following structure:

### Strengths
1. **[Title of Strength]:**
   - **Justification:** [Detailed explanation of the strength and its benefits, with references to chunk IDs close to the relevant information.]

2. **[Title of Strength]:**
   - **Justification:** [Detailed explanation of the strength and its benefits, with references to chunk IDs close to the relevant information.]

# Examples

### Strengths
1. **Strong Market Position:**
   - **Justification:** The company has a dominant market position in its sector, as evidenced by its high market share and strong brand recognition [chunk_12][chunk_15]. This provides pricing power and customer loyalty advantages.

2. **Robust Financial Performance:**
   - **Justification:** The organization demonstrates consistent revenue growth and strong profit margins, indicating efficient operations and effective cost management [chunk_8][chunk_11].

# Notes

- Focus exclusively on internal positive factors and capabilities
- Ensure all references are clearly linked to the corresponding chunk IDs and appear immediately after the information they support
- Provide comprehensive context explaining why each factor constitutes a strength
- Maintain objectivity and support claims with evidence from the source material
"""
