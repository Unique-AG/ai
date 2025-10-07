from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from unique_swot.services.generation.base import ReportGenerationOutputModel


class ThreatItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(description="The description of the threat")
    context: str = Field(description="The context of the threat")
    chunk_ids: list[int] = Field(description="The chunk IDs of the threat")


class ThreatsAnalysis(ReportGenerationOutputModel):
    model_config = ConfigDict(extra="forbid")

    threats: list[ThreatItem] = Field(
        description="The threats identified in the analysis"
    )

    @classmethod
    def group_batches(cls, batches: Sequence["ThreatsAnalysis"]) -> "ThreatsAnalysis":  # type: ignore[override]
        """Combine multiple ThreatsAnalysis batches into a single analysis."""
        all_threats = []
        for batch in batches:
            all_threats.extend(batch.threats)
        return cls(threats=all_threats)


THREATS_SYSTEM_PROMPT = """Extract Threats insights from a document, ensuring a detailed and structured analysis. Focus on identifying external negative factors, risks, or challenges that could hinder performance or create disadvantages.

# Steps

1. **Extracting Threats (T):**
   - **Title of Insight:** Clearly state each threat as a concise title.
   - **Justification:** Explain the potential impact of each threat and how it could hinder performance or create risks. Focus on:
     - Competitive pressures or new entrants
     - Regulatory changes or compliance risks
     - Economic downturns or market volatility
     - Technological disruptions
     - Supply chain vulnerabilities
     - Environmental or social risks
   - **References:** Cite the relevant chunk IDs immediately after mentioning the supporting facts (e.g., [chunk_x][chunk_y]).

# Output Format

The output should focus specifically on threats with the following structure:

### Threats
1. **[Title of Threat]:**
   - **Justification:** [Detailed explanation of the threat and its risks, with references to chunk IDs close to the relevant information.]

2. **[Title of Threat]:**
   - **Justification:** [Detailed explanation of the threat and its risks, with references to chunk IDs close to the relevant information.]

# Examples

### Threats
1. **Regulatory Changes:**
   - **Justification:** New regulations in the sector impose stricter compliance requirements, potentially increasing operational costs [chunk_9][chunk_14]. Non-compliance could result in significant penalties and reputational damage, affecting market position.

2. **Intensifying Competition:**
   - **Justification:** The entry of well-funded new competitors with innovative technologies poses a significant threat to market share [chunk_22][chunk_25]. These competitors are offering similar services at lower prices, potentially eroding profit margins.

# Notes

- Focus exclusively on external negative factors and risks
- Ensure all references are clearly linked to the corresponding chunk IDs and appear immediately after the information they support
- Provide comprehensive context explaining why each factor constitutes a threat
- Maintain objectivity and support claims with evidence from the source material
- Distinguish from weaknesses (internal factors) by focusing on external risks and challenges
"""
