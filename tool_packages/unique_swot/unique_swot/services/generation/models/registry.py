import json
from collections import defaultdict

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import SWOTReportComponentSection
from unique_swot.utils import generate_unique_id


class SWOTReportRegistry:
    def __init__(self):
        self._by_id: dict[str, SWOTReportComponentSection] = {}
        self._id_to_component: dict[str, SWOTComponent] = {}
        self._by_component: dict[
            SWOTComponent, dict[str, SWOTReportComponentSection]
        ] = defaultdict(dict)

    def register_section(
        self, component: SWOTComponent, section: SWOTReportComponentSection
    ) -> str:
        section_id = generate_unique_id(f"section_{component.value}")
        self._by_id[section_id] = section
        self._id_to_component[section_id] = component
        self._by_component[component][section_id] = section
        return section_id

    def retrieve_section(self, id: str) -> SWOTReportComponentSection | None:
        return self._by_id.get(id)

    def retrieve_sections_for_component(
        self, component: SWOTComponent, exclude_items: bool = True
    ) -> str:
        exclude_fields = {"items"} if exclude_items else None
        sections = self._by_component.get(component, {})
        return json.dumps(
            {
                id: section.model_dump(exclude=exclude_fields)
                for id, section in sections.items()
            },
            indent=1,
        )

    def update_section(self, id: str, section: SWOTReportComponentSection) -> None:
        target_component = self._id_to_component.get(id)
        if target_component is None:
            raise KeyError(f"Section id {id} not found in registry")
        self._by_id[id] = section
        self._by_component[target_component][id] = section

    def retrieve_component_sections(
        self, component: SWOTComponent
    ) -> list[SWOTReportComponentSection]:
        return list(self._by_component.get(component, {}).values())
