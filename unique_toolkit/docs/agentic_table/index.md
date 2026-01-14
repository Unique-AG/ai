# Agentic Table Module

The Agentic Table module provides methods to interact with the Agentic Table (Magic Table) functionality in the Unique platform.

## Overview

The `unique_toolkit.agentic_table` module provides:

- Cell manipulation (get, set, batch operations)
- Sheet data retrieval
- Activity tracking
- Agent registration and deregistration
- Column styling
- Artifact management
- Row verification status updates

## Event Triggers and Payloads

The Agentic Table module triggers the following events when specific actions are performed. Each event contains the necessary payload to perform the action. All payload schemas are defined in the `unique_toolkit.agentic_table.schemas` module.

All payloads inherit from `MagicTableBasePayload` which includes the following base attributes:

- `name: str` - The name of the module
- `sheet_name: str` - The name of the sheet
- `action: MagicTableAction` - The action being performed
- `chat_id: str` - The chat ID
- `assistant_id: str` - The assistant ID
- `table_id: str` - The table ID
- `user_message: ChatEventUserMessage` - The user message that triggered the event
- `assistant_message: ChatEventAssistantMessage` - The assistant message associated with the event
- `configuration: dict[str, Any]` - Configuration dictionary
- `metadata: T` - Metadata specific to the payload type (varies by event)
- `metadata_filter: dict[str, Any] | None` - Optional metadata filter

| Event Name | Description | Payload Type | Payload Structure |
|------------|-------------|--------------|-------------------|
| `unique.magic-table.update-cell` | Triggered when a cell is updated | `MagicTableUpdateCellPayload` | **Base attributes** (see above)<br><br>**Additional attributes:**<br><br>- `column_order: int` - The column index of the cell<br>- `row_order: int` - The row index of the cell<br>- `data: str` - The cell data to update<br><br>**Metadata:** `DDMetadata` (see Metadata Attributes section below) |
| `unique.magic-table.add-meta-data` | Triggered when a new question, question file, or source file is added | `MagicTableAddMetadataPayload` | **Base attributes** (see above)<br><br>**Metadata:** `DDMetadata` (see Metadata Attributes section below) |
| `unique.magic-table.generate-artifact` | Triggered when a report generation button is clicked | `MagicTableGenerateArtifactPayload` | **Base attributes** (see above)<br><br>**Additional attributes:**<br><br>- `data: ArtifactData` - Artifact data containing:<br><br>  - `artifact_type: ArtifactType` - Type of artifact (`QUESTIONS` or `FULL_REPORT`)<br><br>**Metadata:** `BaseMetadata` (see Metadata Attributes section below) |
| `unique.magic-table.sheet-completed` | Triggered when the sheet is marked as completed | `MagicTableSheetCompletedPayload` | **Base attributes** (see above)<br><br>**Metadata:** `SheetCompletedMetadata` (see Metadata Attributes section below) |
| `unique.magic-table.library-sheet-row.verified` | Triggered when a row in a "Library" sheet is verified | `MagicTableLibrarySheetRowVerifiedPayload` | **Base attributes** (see above)<br><br>**Metadata:** `LibrarySheetRowVerifiedMetadata` (see Metadata Attributes section below) |
| `unique.magic-table.sheet-created` | Triggered when a new sheet is created | `MagicTableSheetCreatedPayload` | **Base attributes** (see above)<br><br>**Metadata:** `SheetCreatedMetadata` (see Metadata Attributes section below) |

## Metadata Attributes

All metadata types inherit from `BaseMetadata` which includes the following base attributes:

- `sheet_type: SheetType` - The type of the sheet (defaults to `SheetType.DEFAULT`)
- `additional_sheet_information: dict[str, Any]` - Additional information for the sheet (defaults to empty dict)

The following metadata types are used by the event payloads:

### BaseMetadata

The base metadata class that all other metadata types inherit from.

**Attributes:**

- `sheet_type: SheetType` - The type of the sheet
- `additional_sheet_information: dict[str, Any]` - Additional information for the sheet

### DDMetadata

Used by `MagicTableUpdateCellPayload` and `MagicTableAddMetadataPayload`.

**Inherits from:** `BaseMetadata`

**Additional attributes:**

- `question_file_ids: list[str]` - The IDs of the question files (defaults to empty list)
- `source_file_ids: list[str]` - The IDs of the source files (defaults to empty list)
- `question_texts: list[str]` - The texts of the questions (defaults to empty list)
- `context: str` - The context text for the table (defaults to empty string)

### SheetCompletedMetadata

Used by `MagicTableSheetCompletedPayload`.

**Inherits from:** `BaseMetadata`

**Additional attributes:**

- `sheet_id: str` - The ID of the sheet that was completed
- `library_sheet_id: str` - The ID of the library corresponding to the sheet
- `context: str` - The context text for the table (defaults to empty string)

### LibrarySheetRowVerifiedMetadata

Used by `MagicTableLibrarySheetRowVerifiedPayload`.

**Inherits from:** `BaseMetadata`

**Additional attributes:**

- `row_order: int` - The row index of the row that was verified

### SheetCreatedMetadata

Used by `MagicTableSheetCreatedPayload`.

**Inherits from:** `BaseMetadata`

**Attributes:**

- Only includes the base attributes from `BaseMetadata` (no additional attributes)

## Examples

The following examples demonstrate how to use the Agentic Table module:

- [FastAPI App with Agentic Table](../examples_from_docs/fastapi_app_agentic_table.py)
- [Cell Updated Event Handler](../examples_from_docs/agentic_table_example_cell_updated_event_handler.py)
- [Metadata Added Event Handler](../examples_from_docs/agentic_table_example_metadata_added_event_handler.py)
- [Sheet Created Event Handler](../examples_from_docs/agentic_table_example_sheet_created_event_handler.py)
- [Artifact Generated Event Handler](../examples_from_docs/agentic_table_example_artifact_generated_event_handler.py)
- [Column Definition Example](../examples_from_docs/agentic_table_example_column_definition.py)

