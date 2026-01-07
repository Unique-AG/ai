# Service

::: unique_toolkit.agentic_table.service.AgenticTableService


# Schemas

## Event

The primary event type is `MagicTableEvent`.

::: unique_toolkit.agentic_table.schemas.MagicTableEvent

## Event Payload Schemas

All event payloads inherit from the `MagicTableBasePayload` schema.

::: unique_toolkit.agentic_table.schemas.MagicTableBasePayload

The following payload schemas correspond to the events listed above:

::: unique_toolkit.agentic_table.schemas.MagicTableUpdateCellPayload
::: unique_toolkit.agentic_table.schemas.MagicTableAddMetadataPayload
::: unique_toolkit.agentic_table.schemas.MagicTableGenerateArtifactPayload
::: unique_toolkit.agentic_table.schemas.MagicTableSheetCompletedPayload
::: unique_toolkit.agentic_table.schemas.MagicTableLibrarySheetRowVerifiedPayload
::: unique_toolkit.agentic_table.schemas.MagicTableSheetCreatedPayload

## Supporting Schemas

::: unique_toolkit.agentic_table.schemas.BaseMetadata
::: unique_toolkit.agentic_table.schemas.DDMetadata
::: unique_toolkit.agentic_table.schemas.SheetCompletedMetadata

::: unique_toolkit.agentic_table.schemas.SheetCreatedMetadata
::: unique_toolkit.agentic_table.schemas.LibrarySheetRowVerifiedMetadata
::: unique_toolkit.agentic_table.schemas.ArtifactData
::: unique_toolkit.agentic_table.schemas.ArtifactType
::: unique_toolkit.agentic_table.schemas.MagicTableCell
::: unique_toolkit.agentic_table.schemas.MagicTableSheet
::: unique_toolkit.agentic_table.schemas.LogEntry
::: unique_toolkit.agentic_table.schemas.LogDetail
::: unique_toolkit.agentic_table.schemas.RowMetadataEntry

## Exceptions

::: unique_toolkit.agentic_table.service.LockedAgenticTableError
