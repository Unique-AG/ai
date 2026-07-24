"""MCP tool descriptions. Schema details are appended at runtime from SQLite."""

# Defaults pre-filled in the escalate elicitation form / demo email.
DEFAULT_ESCALATE_RECIPIENT_EMAIL = "compliance@unique.ch"
DEFAULT_ESCALATE_NOTE = (
    "Please review this client escalation and advise on next steps. "
    "Confirm whether enhanced due diligence or a formal Compliance case is required."
)
DEFAULT_ESCALATE_ELICIT_INTRO = (
    "You are about to escalate this record. Confirm the notification details below, "
    "then submit to apply the status change and send the escalation email."
)

LIST_SCHEMA_DESCRIPTION = (
    "Describe every table loaded from the Excel workbook into SQLite: table "
    "names, columns, SQLite types, and primary keys. Call this first so you "
    "know which tables and field names to use for CRUD."
)

LIST_ROWS_DESCRIPTION = (
    "List rows from a table. Optional filters is an object of "
    'column → exact value (ANDed), e.g. {"status":"Escalated"}. '
    "Optional search is a substring match over client_name + client_ref by default "
    '(or search_fields). Optional sort is [{"field":"due_date","dir":"asc"}]. '
    "Column names come from list_schema / Excel headers (sanitized). "
    "Use limit/offset for pagination."
)

COUNT_BY_DESCRIPTION = (
    "Return COUNT(*) grouped by a column (default status). Use for live KPI tiles "
    'such as Total / Escalated / Needs Remediation / Compliant: count_by(table="clients").'
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
    "object of columns to change. Primary key columns cannot be updated. "
    "No confirmation prompt — use escalate_row when the change needs "
    "elicitation (e.g. status → Escalated with notify email)."
)

ESCALATE_ROW_DESCRIPTION = (
    "Escalate a row with MCP form elicitation: confirm recipient email + note, "
    "then set status to Escalated (unless fields already contain status/state "
    "escalate/Escalated) and log a demo escalation email. "
    "Pass optional note / recipient_email for the notify email (not as table columns). "
    "fields is only for real table columns — never put note or recipient_email there "
    "(if you do, they are stripped and used as email defaults). "
    "Use this instead of update_row when the user must confirm before escalating. "
    "Cancel returns EscalateCancelled and leaves the row unchanged."
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
