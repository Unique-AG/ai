from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

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


class ComponentDefinitionPromptConfig(BaseModel):
    model_config = get_configuration_dict()

    strengths_definition: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_COMPONENT_DEFINITIONS[SWOTComponent.STRENGTHS].split("\n"))
        ),
    ] = Field(
        default=_COMPONENT_DEFINITIONS[SWOTComponent.STRENGTHS],
        description="The definition of the strengths component.",
    )
    weaknesses_definition: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_COMPONENT_DEFINITIONS[SWOTComponent.WEAKNESSES].split("\n"))
        ),
    ] = Field(
        default=_COMPONENT_DEFINITIONS[SWOTComponent.WEAKNESSES],
        description="The definition of the weaknesses component.",
    )
    opportunities_definition: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_COMPONENT_DEFINITIONS[SWOTComponent.OPPORTUNITIES].split("\n"))
        ),
    ] = Field(
        default=_COMPONENT_DEFINITIONS[SWOTComponent.OPPORTUNITIES],
        description="The definition of the opportunities component.",
    )
    threats_definition: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_COMPONENT_DEFINITIONS[SWOTComponent.THREATS].split("\n"))
        ),
    ] = Field(
        default=_COMPONENT_DEFINITIONS[SWOTComponent.THREATS],
        description="The definition of the threats component.",
    )


def get_component_definition(
    component: SWOTComponent, config: ComponentDefinitionPromptConfig
) -> str:
    match component:
        case SWOTComponent.STRENGTHS:
            return config.strengths_definition
        case SWOTComponent.WEAKNESSES:
            return config.weaknesses_definition
        case SWOTComponent.OPPORTUNITIES:
            return config.opportunities_definition
        case SWOTComponent.THREATS:
            return config.threats_definition
        case _:
            raise ValueError(f"Unknown SWOT component: {component}")
