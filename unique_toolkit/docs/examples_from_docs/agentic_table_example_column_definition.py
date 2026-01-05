from pydantic import BaseModel

from unique_sdk import CellRendererTypes
from enum import StrEnum

class ColumnDefinition(BaseModel):
    """
    Defines the structure and styling of a single table column.
    
    Attributes:
        order: Zero-based column index
        name: Display name shown in header row
        width: Column width in pixels
        renderer: Cell renderer type for specialized display/interaction
        editable: Whether users can edit cells in this column by default
    """
    order: int
    name: str
    width: int
    renderer: CellRendererTypes | None = None
    editable: bool = True
    
    
class ColumnDefinitions(BaseModel):
    """
    Defines the structure and styling of all columns in the table.
    """
    columns: list[ColumnDefinition]
    
    @property
    def column_map(self) -> dict[str, ColumnDefinition]:
        """
        Get a dictionary of column names to column definitions.
        """
        return {column.name: column for column in self.columns}
    
    def get_column_by_name(self, name: str) -> ColumnDefinition:
        """
        Get a column definition by name.
        """
        return self.column_map[name]
    
    def get_column_names(self) -> list[str]:
        """
        Get a list of all column names.
        """
        return list(self.column_map.keys())
    

class ExampleColumnNames(StrEnum):
    QUESTION = "Question"
    SECTION = "Section"
    ANSWER = "Answer"
    CRITICAL_CONSISTENCY = "Critical Consistency"
    STATUS = "Status"
    REVIEWER = "Reviewer"
    
example_configuration = {
    "columns": [
        {
            "order": 0,
            "name": ExampleColumnNames.QUESTION,
            "width": 300,
            "renderer": None,
            "editable": False
        },
        {
            "order": 1,
            "name": ExampleColumnNames.SECTION,
            "width": 150,
            "renderer": None,
            "editable": False
        },
        {
            "order": 2,
            "name": ExampleColumnNames.ANSWER,
            "width": 400,
            "renderer": CellRendererTypes.SELECTABLE_CELL_RENDERER,
            "editable": True
        },
        {
            "order": 3,
            "name": ExampleColumnNames.CRITICAL_CONSISTENCY,
            "width": 200,
            "renderer": None,
            "editable": True
        },
        {
            "order": 4,
            "name": ExampleColumnNames.STATUS,
            "width": 150,
            "renderer": CellRendererTypes.REVIEW_STATUS_DROPDOWN,
            "editable": True
        },
        {
            "order": 5,
            "name": ExampleColumnNames.REVIEWER,
            "width": 150,
            "renderer": CellRendererTypes.COLLABORATOR_DROPDOWN,
            "editable": True
        }
    ]
}

example_column_definitions = ColumnDefinitions.model_validate(example_configuration)