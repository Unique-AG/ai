# Event

Events are the building blocks of the Unique platform. They are used to trigger actions and to communicate between different parts of the platform.
Various actions in the platform trigger differnet events. Each of these events has a specific payload that is used to trigger the action.
So it is crucial to understand them to be able to build applications reactive to the platform.

You can find all events as a StrEnum in the `unique_toolkit.app.schemas.EventName` class.

### Chat

The chat interface triggers the following events:

| Event Name | Description | Event Type | Payload Type |
|------------|-------------|--------------|--------------|
| `unique.chat.user-message.created` | Triggered when a user sends a message to the chat | - | - |
| `unique.chat.external-module.chosen` | Triggered when a user chooses an external module to use in the chat | `ChatEvent` | `ChatEventPayload` |

### Ingestion

The knowledge base ingestion process triggers the following events:

| Event Name | Description | Payload Type |
|------------|-------------|--------------|
| `unique.ingestion.content.uploaded` | Triggered when a new file is uploaded to the knowledge base | - |
| `unique.ingestion.content.finished` | Triggered when the ingestion of a file is finished | - |

### Agentic Table

The Agentic Table interface triggers the following events:

| Event Name | Description | Event Type | Payload Type |
|------------|-------------|--------------|--------------|
| `unique.magic-table.update-cell` | Triggered when a cell is updated | `MagicTableEvent` | `MagicTableUpdateCellPayload` |
| `unique.magic-table.add-meta-data` | Triggered when a new question, question file, or source file is added | `MagicTableEvent` | `MagicTableAddMetadataPayload` |
| `unique.magic-table.generate-artifact` | Triggered when a report generation button is clicked | `MagicTableEvent` | `MagicTableGenerateArtifactPayload` |
| `unique.magic-table.sheet-completed` | Triggered when the sheet is marked as completed | `MagicTableEvent` | `MagicTableSheetCompletedPayload` |
| `unique.magic-table.library-sheet-row.verified` | Triggered when a row in a "Library" sheet is verified | `MagicTableEvent` | `MagicTableLibrarySheetRowVerifiedPayload` |
| `unique.magic-table.sheet-created` | Triggered when a new sheet is created | `MagicTableEvent` | `MagicTableSheetCreatedPayload` |

