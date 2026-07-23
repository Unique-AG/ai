"""MCP tool descriptions. Schema details are appended at runtime from SQLite."""

LIST_SCHEMA_DESCRIPTION = (
    "Describe every table loaded from the Excel workbook into SQLite: table "
    "names, columns, SQLite types, and primary keys. Call this first so you "
    "know which tables and field names to use for CRUD."
)

LIST_ROWS_DESCRIPTION = (
    "List rows from a table. Optional filters is an object of "
    'column → exact value (ANDed), e.g. {"ticker":"MSFT"}. Column names come '
    "from list_schema / the Excel headers (sanitized). Use limit/offset for pagination."
)

GET_ROW_DESCRIPTION = (
    "Fetch a single row by primary key (id or row_id, depending on whether the Excel sheet already had an id column)."
)

CREATE_ROW_DESCRIPTION = (
    "Insert a new row. fields is an object of column → value using the "
    "column names from list_schema. Do not set auto-generated primary keys "
    "(row_id)."
)

UPDATE_ROW_DESCRIPTION = (
    "Update an existing row identified by its primary key. fields is an "
    "object of columns to change. Primary key columns cannot be updated."
)

DELETE_ROW_DESCRIPTION = (
    "Delete a row identified by its primary key. Asks the user to confirm via "
    "MCP elicitation before deleting. Returns the deleted row, or a cancelled error."
)

RESET_FROM_EXCEL_DESCRIPTION = (
    "DESTRUCTIVE: delete the SQLite database and recreate all tables from the "
    "Excel workbook. Asks the user to confirm via MCP elicitation first. "
    "Use between demos to restore the seed data."
)
