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
