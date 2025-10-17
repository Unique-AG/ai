from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from unique_swot.services.generation.base import ReportGenerationOutputModel


class WeaknessItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(description="The description of the weakness")
    context: str = Field(description="The context of the weakness")
    chunk_ids: list[int] = Field(description="The chunk IDs of the weakness")


class WeaknessesAnalysis(ReportGenerationOutputModel["WeaknessesAnalysis"]):
    model_config = ConfigDict(extra="forbid")

    weaknesses: list[WeaknessItem] = Field(
        description="The weaknesses identified in the analysis"
    )

    @classmethod
    def group_batches(
        cls, batches: Sequence["WeaknessesAnalysis"]
    ) -> "WeaknessesAnalysis":
        """Combine multiple WeaknessesAnalysis batches into a single analysis."""
        all_weaknesses = []
        for batch in batches:
            all_weaknesses.extend(batch.weaknesses)
        return cls(weaknesses=all_weaknesses)


WEAKNESSES_SYSTEM_PROMPT = """Extract Weaknesses insights from a document, ensuring a detailed and structured analysis. Focus on identifying internal negative factors, limitations, or disadvantages that create challenges or hinder performance.

# Steps

1. **Extracting Weaknesses (W):**
   - **Title of Insight:** Clearly state each weakness as a concise title.
   - **Justification:** Explain how each weakness creates a disadvantage or poses challenges to the subject. Focus on:
     - Internal limitations or deficiencies
     - Resource constraints
     - Operational inefficiencies
     - Competitive disadvantages
     - Areas needing improvement
   - **References:** Cite the relevant chunk IDs immediately after mentioning the supporting facts (e.g., [chunk_x][chunk_y]).

# Output Format

The output should focus specifically on weaknesses with the following structure:

### Weaknesses
1. **[Title of Weakness]:**
   - **Justification:** [Detailed explanation of the weakness and its challenges, with references to chunk IDs close to the relevant information.]

2. **[Title of Weakness]:**
   - **Justification:** [Detailed explanation of the weakness and its challenges, with references to chunk IDs close to the relevant information.]

# Examples

### Weaknesses
1. **Limited R&D Investment:**
   - **Justification:** The organization allocates a smaller percentage of revenue to R&D compared to competitors, which could hinder innovation and long-term growth [chunk_8][chunk_11]. This may result in falling behind in technological advancement.

2. **High Employee Turnover:**
   - **Justification:** The company experiences above-industry-average employee turnover rates, particularly in key technical roles [chunk_15][chunk_18]. This leads to increased recruitment costs and loss of institutional knowledge.

# Notes

- Focus exclusively on internal negative factors and limitations
- Ensure all references are clearly linked to the corresponding chunk IDs and appear immediately after the information they support
- Provide comprehensive context explaining why each factor constitutes a weakness
- Maintain objectivity and support claims with evidence from the source material
- Avoid external factors (those belong in threats analysis)
"""
