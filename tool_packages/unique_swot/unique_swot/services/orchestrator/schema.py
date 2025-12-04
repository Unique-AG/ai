from pydantic import BaseModel


class SourceSelectionResult(BaseModel):
    """This class is responsible for the result of the source selection."""

    should_select: bool
    reason: str


class ReportGenerationResult(BaseModel):
    """This class is responsible for the result of the report generation."""

    report: str
