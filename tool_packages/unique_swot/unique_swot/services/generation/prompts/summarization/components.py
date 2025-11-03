"""Component-specific configurations for SWOT summarization prompts."""

from unique_swot.services.generation.prompts.summarization.template import (
    SummarizationPromptTemplate,
)

OPPORTUNITIES_SUMMARIZATION_SYSTEM_PROMPT = SummarizationPromptTemplate(
    component_name="Opportunity",
    component_singular="opportunity",
    component_plural="opportunities",
    scope_type="external conditions",
    scope_description="external favorable conditions",
    scope_context="external environment",
    quality_focus="Focus on external factors and their potential for creating advantage",
    additional_quality_standard="Be realistic about timing and feasibility - opportunities should be actionable, not wishful thinking",
    additional_merge_guideline="Highlight the full scope of the opportunity and its potential impact",
    merge_examples=[
        'Different phrasings of the same market trend (e.g., "Growing E-commerce Market" and "Shift to Online Shopping")',
        "Multiple mentions of the same external condition from different sources",
        "Overlapping aspects of a single market opportunity described separately",
        "Related aspects of a broader trend that should be presented together",
    ],
    distinct_examples=[
        "Different types of external opportunities (e.g., technological advancement vs. regulatory change)",
        "Multiple market opportunities in different segments or geographies",
        'Separate trends even if they\'re related (e.g., "AI Adoption" and "Cloud Computing Growth")',
        "Opportunities at different stages or with different time horizons",
    ],
    output_scope="external favorable conditions",
    output_context="opportunities available",
    additional_expectations=[
        "Emphasizes strategic potential and actionability",
    ],
    example_title="Expansion into Digital Payment Partnerships",
    example_bullets=[
        "**Digital payments growth is creating integration opportunities.** Digital payments are projected to grow at 18% CAGR through 2027, with mobile wallet adoption reaching 65% of US consumers [bullet_chunk_1][bullet_chunk_2]",
        "**Point-of-transaction embedding reduces friction and increases conversion.** Integration with payment platforms like Apple Pay and Google Wallet could embed Ibotta offers at point-of-transaction, reducing friction and increasing redemption rates [bullet_chunk_3]",
        "**Early movers can capture disproportionate market share in payment-linked offers.** The addressable market for payment-linked offers represents $2.4B in potential revenue, with early movers capturing disproportionate share [bullet_chunk_4][bullet_chunk_5]",
    ],
    example_reasoning="Digital payments growth is creating integration opportunities",
    bullet_focus="implication",
).render()


STRENGTHS_SUMMARIZATION_SYSTEM_PROMPT = SummarizationPromptTemplate(
    component_name="Strength",
    component_singular="strength",
    component_plural="strengths",
    scope_type="internal advantages",
    scope_description="internal advantages",
    scope_context="organization's internal capabilities",
    quality_focus="Emphasize demonstrable competitive advantages and unique capabilities that differentiate the organization",
    additional_quality_standard="Support claims with concrete evidence - avoid generic or unsubstantiated assertions of superiority",
    additional_merge_guideline="Ensure merged strengths capture the full breadth of the competitive advantage without diluting specificity",
    merge_examples=[
        'Different phrasings of the same core capability (e.g., "Strong Brand" and "Brand Recognition Excellence")',
        "Multiple mentions of the same resource or asset from different sources",
        "Overlapping aspects of a single competitive advantage described separately",
    ],
    distinct_examples=[
        "Different categories of internal advantages (e.g., financial strength vs. technological capability)",
        "Multiple competencies that serve different strategic purposes",
        "Separate resources or capabilities even if they're related",
    ],
    output_scope="internal advantages",
    output_context="organization's strengths",
    additional_expectations=[],
    example_title="Strong Brand Recognition and Customer Loyalty",
    example_bullets=[
        "**Ibotta's market position as #2 cashback app demonstrates strong brand awareness.** Ibotta ranks as the #2 cashback app with 50M+ downloads and maintains strong brand awareness in the competitive rewards space [bullet_chunk_1][bullet_chunk_2]",
        "**High retention rates indicate sticky user engagement patterns.** The platform demonstrates high retention rates with users averaging 3.2 redemptions per month, indicating sticky engagement patterns [bullet_chunk_3]",
        "**Brand equity creates competitive advantages in acquisition and partnerships.** Brand equity enables lower customer acquisition costs compared to newer entrants and supports premium partnership negotiations [bullet_chunk_4][bullet_chunk_5]",
    ],
    example_reasoning="Ibotta's market position as #2 cashback app demonstrates strong brand awareness",
    bullet_focus="implication",
).render()


WEAKNESSES_SUMMARIZATION_SYSTEM_PROMPT = SummarizationPromptTemplate(
    component_name="Weakness",
    component_singular="weakness",
    component_plural="weaknesses",
    scope_type="internal limitations",
    scope_description="internal limitations",
    scope_context="organization's internal deficiencies",
    quality_focus="Provide honest assessment of limitations while maintaining a constructive, solution-oriented perspective",
    additional_quality_standard="Be constructive and objective - focus on factual limitations, not subjective criticism",
    additional_merge_guideline="Acknowledge the full scope and interconnected nature of related limitations when merging",
    merge_examples=[
        'Different phrasings of the same core limitation (e.g., "Limited R&D Budget" and "Insufficient Innovation Investment")',
        "Multiple mentions of the same constraint or deficiency from different sources",
        "Overlapping aspects of a single internal challenge described separately",
    ],
    distinct_examples=[
        "Different categories of internal limitations (e.g., financial constraints vs. skill gaps)",
        "Multiple deficiencies that affect different areas of operation",
        'Separate challenges even if they\'re related (e.g., "Outdated Technology" and "Lack of Digital Skills")',
    ],
    output_scope="internal limitations",
    output_context="organization's weaknesses",
    additional_expectations=[
        "Maintains an objective, constructive tone throughout",
    ],
    example_title="Profitability Challenges and Path to Break-Even",
    example_bullets=[
        "**Continued net losses and negative EBITDA margins indicate profitability challenges.** The company reported a net loss of $45M in Q4 2023, with EBITDA margins remaining negative at -8% despite revenue growth [bullet_chunk_1][bullet_chunk_2]",
        "**High operational costs limit margin expansion opportunities.** High operational costs from retailer integrations and user acquisition expenses consume 65% of gross revenue, limiting margin expansion [bullet_chunk_3]",
        "**Ongoing losses may constrain access to growth capital.** Continued losses raise questions about long-term viability and may limit access to growth capital in tighter funding environments [bullet_chunk_4][bullet_chunk_5]",
    ],
    example_reasoning="Continued net losses and negative EBITDA margins indicate profitability challenges",
    bullet_focus="consequence",
).render()


THREATS_SUMMARIZATION_SYSTEM_PROMPT = SummarizationPromptTemplate(
    component_name="Threat",
    component_singular="threat",
    component_plural="threats",
    scope_type="external risks",
    scope_description="external risks or challenges",
    scope_context="external risk landscape",
    quality_focus="Focus on external risks and their potential negative impact",
    additional_quality_standard="Maintain objectivity - base assessments on evidence, not speculation",
    additional_merge_guideline="Clearly articulate the full scope and potential impact of the threat",
    merge_examples=[
        'Different phrasings of the same external risk (e.g., "Increased Competition" and "New Market Entrants")',
        "Multiple mentions of the same external challenge from different sources",
        "Overlapping aspects of a single threat described separately",
        "Related aspects of a broader risk that should be presented together",
    ],
    distinct_examples=[
        "Different types of external threats (e.g., competitive pressure vs. regulatory risk)",
        "Multiple risks in different areas (e.g., supply chain vs. cybersecurity)",
        'Separate risks even if they\'re related (e.g., "Economic Recession" and "Currency Volatility")',
        "Threats with different time horizons or likelihood levels",
    ],
    output_scope="external risks",
    output_context="threats facing the organization",
    additional_expectations=[
        "Balances comprehensiveness with actionable clarity",
        "Maintains an objective, evidence-based tone",
    ],
    example_title="Intensifying Competition from Well-Funded Rivals",
    example_bullets=[
        "**Well-funded rivals are investing heavily in user acquisition and capturing market share.** Major players like Rakuten and Honey (PayPal) are investing heavily in user acquisition, spending $150M+ annually on marketing and capturing market share through aggressive promotional campaigns [bullet_chunk_1][bullet_chunk_2]",
        "**Competition is driving up cashback rates and compressing industry margins.** Increased competition is driving up cashback rates and promotional offers, compressing margins across the industry with average cashback rates rising from 3% to 5.5% over the past two years [bullet_chunk_3]",
        "**Platform proliferation is fragmenting the market and reducing network effects.** The proliferation of cashback platforms is dividing consumer attention and loyalty, making it harder to maintain exclusive brand partnerships and reducing the effectiveness of network effects [bullet_chunk_4][bullet_chunk_5]",
    ],
    example_reasoning="Well-funded rivals are investing heavily in user acquisition and capturing market share",
    bullet_focus="impact",
).render()
