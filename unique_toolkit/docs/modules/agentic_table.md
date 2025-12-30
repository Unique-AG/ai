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

| Event Name | Description | Payload Type |
|------------|-------------|--------------|
| `unique.magic-table.update-cell` | Triggered when a cell is updated | `MagicTableUpdateCellPayload` |
| `unique.magic-table.add-meta-data` | Triggered when a new question, question file, or source file is added | `MagicTableAddMetadataPayload` |
| `unique.magic-table.generate-artifact` | Triggered when a report generation button is clicked | `MagicTableGenerateArtifactPayload` |
| `unique.magic-table.sheet-completed` | Triggered when the sheet is marked as completed | `MagicTableSheetCompletedPayload` |
| `unique.magic-table.library-sheet-row.verified` | Triggered when a row in a "Library" sheet is verified | `MagicTableLibrarySheetRowVerifiedPayload` |
| `unique.magic-table.sheet-created` | Triggered when a new sheet is created | `MagicTableSheetCreatedPayload` |

## Components

## Service
::: unique_toolkit.agentic_table.service.AgenticTableService
    options:
      heading_level: 3

## Schemas

### Event Payload Schemas

The following payload schemas correspond to the events listed above:

::: unique_toolkit.agentic_table.schemas.MagicTableUpdateCellPayload
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableAddMetadataPayload
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableGenerateArtifactPayload
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableSheetCompletedPayload
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableLibrarySheetRowVerifiedPayload
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableSheetCreatedPayload
    options:
      heading_level: 4

### Supporting Schemas

::: unique_toolkit.agentic_table.schemas.MagicTableEvent
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableBasePayload
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.BaseMetadata
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.DDMetadata
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.SheetCompletedMetadata
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.SheetCreatedMetadata
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.LibrarySheetRowVerifiedMetadata
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.ArtifactData
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.ArtifactType
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableCell
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.MagicTableSheet
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.LogEntry
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.LogDetail
    options:
      heading_level: 4

::: unique_toolkit.agentic_table.schemas.RowMetadataEntry
    options:
      heading_level: 4

## Exceptions

::: unique_toolkit.agentic_table.service.LockedAgenticTableError
    options:
      heading_level: 3

