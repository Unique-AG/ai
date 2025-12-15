from pydantic import Field

from unique_swot.utils import StructuredOutputResult, StructuredOutputWithNotification


## SWOT Extraction Models
class SWOTExtractionFactsList(StructuredOutputWithNotification):
    facts: list[str] = Field(
        description="The list of facts extracted from the sources chunks."
    )


## SWOT Report Models
class SWOTReportSectionEntry(StructuredOutputResult):
    preview: str = Field(
        description="The preview of the section entry. Should be a concise preview that captures the main idea of the entry."
    )
    content: str = Field(description="The content of the section entry.")


class SWOTReportComponentSection(StructuredOutputResult):
    h2: str = Field(
        description="The subheading of the cluster. Should be concise sentence that summarizes the content of the entries in the cluster."
    )
    entries: list[SWOTReportSectionEntry] = Field(
        description="The list of entries in the section. Each entry should be a concise title and content that summarizes the content of the entry in the section."
    )


class SWOTReportComponents(StructuredOutputResult):
    strengths: list[SWOTReportComponentSection] = Field(
        description="The sections of the report. Each section should be a concise title and content that summarizes the content of the section."
    )
    weaknesses: list[SWOTReportComponentSection] = Field(
        description="The sections of the report. Each section should be a concise title and content that summarizes the content of the section."
    )
    opportunities: list[SWOTReportComponentSection] = Field(
        description="The sections of the report. Each section should be a concise title and content that summarizes the content of the section."
    )
    threats: list[SWOTReportComponentSection] = Field(
        description="The sections of the report. Each section should be a concise title and content that summarizes the content of the section."
    )

    def is_empty(self) -> bool:
        return all(len(section) == 0 for section in self.model_dump().values())
