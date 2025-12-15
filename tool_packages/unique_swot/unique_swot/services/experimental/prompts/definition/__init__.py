from unique_swot.services.generation.context import SWOTComponent

_COMPONENT_DEFINITIONS: dict[SWOTComponent, str] = {
    SWOTComponent.STRENGTHS: (
        "Internal advantages, assets, capabilities, or resources that give "
        "the company an edge (e.g., brand, tech, talent, cash, IP, loyal customers)."
    ),
    SWOTComponent.WEAKNESSES: (
        "Internal limitations or gaps that hinder performance or competitiveness "
        "(e.g., execution issues, product gaps, debt, churn, reliance on single supplier)."
    ),
    SWOTComponent.OPPORTUNITIES: (
        "External trends or openings the company can capture for growth or advantage "
        "(e.g., market expansion, new tech adoption, regulatory tailwinds, partner ecosystems)."
    ),
    SWOTComponent.THREATS: (
        "External risks that could harm the company’s position or performance "
        "(e.g., competitors, substitutes, regulatory or macro headwinds, supply shocks)."
    ),
}


def get_component_definition(component: SWOTComponent) -> str:
    try:
        return _COMPONENT_DEFINITIONS[component]
    except KeyError as exc:
        raise ValueError(f"Unknown SWOT component: {component}") from exc
