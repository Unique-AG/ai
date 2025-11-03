"""Component-specific configurations for SWOT extraction prompts."""

from unique_swot.services.generation.prompts.extraction.template import (
    ExtractionPromptTemplate,
    QualificationCategory,
)

OPPORTUNITIES_EXTRACTION_SYSTEM_PROMPT = ExtractionPromptTemplate(
    component_name="Opportunity",
    component_name_plural="Opportunities",
    component_singular="opportunity",
    article="an",
    internal_external="external",
    scope_type="external positive factors, trends, or conditions",
    scope_description="could provide advantages or growth potential",
    scope_context="that exist outside the organization but could be leveraged for advantage",
    qualification_categories=[
        QualificationCategory(
            name="Market Trends",
            description="Emerging market conditions, shifting consumer preferences, or new market segments",
        ),
        QualificationCategory(
            name="Technological Advances",
            description="New technologies or innovations that could be adopted or leveraged",
        ),
        QualificationCategory(
            name="Regulatory Changes",
            description="New laws, policies, or regulations that create favorable conditions",
        ),
        QualificationCategory(
            name="Market Gaps",
            description="Unmet customer needs or underserved markets that could be addressed",
        ),
        QualificationCategory(
            name="Economic Shifts",
            description="Favorable economic conditions, demographic changes, or societal trends",
        ),
        QualificationCategory(
            name="Strategic Partnerships",
            description="Potential collaborations, alliances, or expansion opportunities",
        ),
        QualificationCategory(
            name="Competitive Landscape",
            description="Weaknesses of competitors or market consolidation that creates openings",
        ),
        QualificationCategory(
            name="Industry Evolution",
            description="Shifts in industry structure or business models that create new possibilities",
        ),
    ],
    key_distinction="Opportunities are external and forward-looking. They represent conditions or situations that *could* be exploited, not internal capabilities (those are Strengths).",
    title_guideline="the essence of the external factor",
    explanation_focus="Provide Deep Context",
    explanation_details="Explain comprehensively why this external factor represents an opportunity, including its potential impact and value",
    evidence_requirement="all insights",
    evidence_type="data, metrics, or examples",
    objectivity_guideline="Base all insights on evidence from the source material, not speculation",
    distinction_category="Strengths",
    distinction_explanation="If it's an internal capability or asset, it's a Strength, not an Opportunity",
).render()


STRENGTHS_EXTRACTION_SYSTEM_PROMPT = ExtractionPromptTemplate(
    component_name="Strength",
    component_name_plural="Strengths",
    component_singular="strength",
    article="a",
    internal_external="internal",
    scope_type="internal positive factors, capabilities, and advantages",
    scope_description="the organization currently possesses",
    scope_context="that give the organization an advantage. These are existing capabilities, resources, or attributes that the organization controls",
    qualification_categories=[
        QualificationCategory(
            name="Core Competencies",
            description="Unique skills, expertise, or knowledge that differentiate the organization",
        ),
        QualificationCategory(
            name="Financial Resources",
            description="Strong financial position, healthy cash flow, or access to capital",
        ),
        QualificationCategory(
            name="Brand & Reputation",
            description="Strong brand recognition, customer loyalty, or positive market perception",
        ),
        QualificationCategory(
            name="Human Capital",
            description="Talented workforce, strong leadership, or effective organizational culture",
        ),
        QualificationCategory(
            name="Operational Excellence",
            description="Efficient processes, proven systems, or superior quality control",
        ),
        QualificationCategory(
            name="Technology & Innovation",
            description="Proprietary technology, patents, or innovation capabilities",
        ),
        QualificationCategory(
            name="Market Position",
            description="Market leadership, established customer base, or strong distribution networks",
        ),
        QualificationCategory(
            name="Physical Assets",
            description="Strategic locations, modern facilities, or valuable infrastructure",
        ),
        QualificationCategory(
            name="Track Record",
            description="Proven success, consistent performance, or demonstrated achievements",
        ),
    ],
    key_distinction="Strengths are internal and currently existing. They represent what the organization *has* or *does well* now, not external opportunities or future potential.",
    title_guideline="the internal advantage",
    explanation_focus="Explain the Benefit",
    explanation_details="Detail how each strength provides competitive advantage or contributes to success",
    evidence_requirement="claims",
    evidence_type="data, metrics, or examples",
    objectivity_guideline="Focus on demonstrable strengths, not aspirations or claims without evidence",
    distinction_category="Opportunities",
    distinction_explanation="If it's an external factor or future possibility, it's an Opportunity, not a Strength",
).render()


WEAKNESSES_EXTRACTION_SYSTEM_PROMPT = ExtractionPromptTemplate(
    component_name="Weakness",
    component_name_plural="Weaknesses",
    component_singular="weakness",
    article="a",
    internal_external="internal",
    scope_type="internal negative factors, limitations, or deficiencies",
    scope_description="place the organization at a disadvantage",
    scope_context="within the organization's control that create disadvantages or hinder performance",
    qualification_categories=[
        QualificationCategory(
            name="Resource Constraints",
            description="Limited financial resources, budget constraints, or insufficient capital",
        ),
        QualificationCategory(
            name="Capability Gaps",
            description="Lack of expertise, inadequate skills, or missing competencies",
        ),
        QualificationCategory(
            name="Operational Inefficiencies",
            description="Poor processes, outdated systems, or quality control issues",
        ),
        QualificationCategory(
            name="Organizational Issues",
            description="Weak leadership, poor culture, high employee turnover, or communication problems",
        ),
        QualificationCategory(
            name="Market Position",
            description="Weak brand recognition, limited market share, or poor customer perception",
        ),
        QualificationCategory(
            name="Technology Deficiencies",
            description="Outdated technology, lack of innovation, or poor digital capabilities",
        ),
        QualificationCategory(
            name="Infrastructure Problems",
            description="Inadequate facilities, poor locations, or aging assets",
        ),
        QualificationCategory(
            name="Performance Issues",
            description="Declining metrics, missed targets, or consistent underperformance",
        ),
        QualificationCategory(
            name="Dependencies",
            description="Over-reliance on key customers, suppliers, or individuals",
        ),
    ],
    key_distinction="Weaknesses are internal and currently existing. They represent what the organization *lacks* or *does poorly* now, not external threats or future risks.",
    title_guideline="the internal deficiency",
    explanation_focus="Explain the Impact",
    explanation_details="Detail how each weakness creates disadvantages or poses challenges to success",
    evidence_requirement="assessments",
    evidence_type="examples, data, or specific instances",
    objectivity_guideline="Focus on documented weaknesses, not assumptions or opinions",
    distinction_category="Threats",
    distinction_explanation="If it's an external risk or challenge, it's a Threat, not a Weakness",
).render()


THREATS_EXTRACTION_SYSTEM_PROMPT = ExtractionPromptTemplate(
    component_name="Threat",
    component_name_plural="Threats",
    component_singular="threat",
    article="a",
    internal_external="external",
    scope_type="external negative factors, risks, or challenges",
    scope_description="could harm the organization or impede its success",
    scope_context="beyond the organization's direct control that could create problems or risks",
    qualification_categories=[
        QualificationCategory(
            name="Competitive Pressures",
            description="Aggressive competitors, new market entrants, or competitive pricing pressures",
        ),
        QualificationCategory(
            name="Market Challenges",
            description="Declining markets, changing customer preferences, or market saturation",
        ),
        QualificationCategory(
            name="Regulatory Risks",
            description="Unfavorable regulations, compliance requirements, or legal challenges",
        ),
        QualificationCategory(
            name="Economic Threats",
            description="Economic downturns, recession risks, inflation, or currency fluctuations",
        ),
        QualificationCategory(
            name="Technological Disruption",
            description="Disruptive technologies, obsolescence risks, or competitors' technological advances",
        ),
        QualificationCategory(
            name="Supply Chain Risks",
            description="Supplier dependencies, supply disruptions, or rising input costs",
        ),
        QualificationCategory(
            name="Geopolitical Factors",
            description="Political instability, trade disputes, or international tensions",
        ),
        QualificationCategory(
            name="Environmental/Social Risks",
            description="Climate change impacts, social movements, or changing stakeholder expectations",
        ),
        QualificationCategory(
            name="Cybersecurity",
            description="Data breaches, cyber threats, or security vulnerabilities",
        ),
    ],
    key_distinction="Threats are external and pose risks. They represent conditions or forces that *could harm* the organization, not internal shortcomings (those are Weaknesses).",
    title_guideline="the external risk",
    explanation_focus="Explain the Impact",
    explanation_details="Detail the potential consequences and how the threat could hinder performance or create challenges",
    evidence_requirement="threat assessments",
    evidence_type="data, metrics, or examples",
    objectivity_guideline="Base threat assessments on evidence, not unfounded fears",
    distinction_category="Weaknesses",
    distinction_explanation="If it's an internal limitation or deficiency, it's a Weakness, not a Threat",
).render()
