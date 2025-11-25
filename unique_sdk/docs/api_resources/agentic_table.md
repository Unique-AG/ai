# Agentic Table API

The Agentic Table API (Magic Table) provides functionality for managing AI-powered interactive tables with activity tracking and metadata management.

## Overview

Work with intelligent tables that support:

- Cell-level operations and bulk updates
- Activity and status tracking
- Log history for changes
- Column and cell metadata
- Row verification workflows
- Artifact attachments

## Core Methods

??? example "`unique_sdk.AgenticTable.set_cell` - Set cell content"

    Set content of a specific cell with optional log entries.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `rowOrder` (int, required) - Row index (0-based)
    - `columnOrder` (int, required) - Column index (0-based)
    - `text` (str, required) - Cell content text
    - `logEntries` (List[LogEntry], optional) - Array of log entry objects. See [`LogEntry`](#logentry) for structure.

    **Returns:**

    Returns an [`AgenticTableCell`](#agentictablecell) object.

    **Example:**

    ```python
    cell = await unique_sdk.AgenticTable.set_cell(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        rowOrder=0,
        columnOrder=1,
        text="Updated cell content",
        logEntries=[
            {
                "text": "Cell updated by automation",
                "createdAt": "2024-01-01T00:00:00.000Z",
                "actorType": "SYSTEM",  # "USER", "SYSTEM", "ASSISTANT", "TOOL"
                "messageId": "msg_123",  # optional
                "details": [  # optional
                    {
                        "text": "Processing completed",
                        "messageId": "msg_456"
                    }
                ]
            }
        ]
    )
    ```

??? example "`unique_sdk.AgenticTable.get_cell` - Retrieve cell content"

    Retrieve content and metadata of a specific cell.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `rowOrder` (int, required) - Row index (0-based)
    - `columnOrder` (int, required) - Column index (0-based)

    **Returns:**

    Returns an [`AgenticTableCell`](#agentictablecell) object.

    **Example:**

    ```python
    cell = await unique_sdk.AgenticTable.get_cell(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        rowOrder=0,
        columnOrder=1
    )

    print(f"Text: {cell.text}")
    ```

??? example "`unique_sdk.AgenticTable.set_multiple_cells` - Bulk update cells"

    Bulk update multiple cells in a single operation for better performance.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `cells` (List[AgenticTableCell], required) - List of cell objects to update. Each cell should have `rowOrder`, `columnOrder`, and `text`.

    **Returns:**

    Returns a [`ColumnMetadataUpdateStatus`](#columnmetadataupdatestatus) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.set_multiple_cells(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        cells=[
            {
                "rowOrder": 0,
                "columnOrder": 0,
                "text": "Cell A1"
            },
            {
                "rowOrder": 0,
                "columnOrder": 1,
                "text": "Cell B1"
            },
            {
                "rowOrder": 1,
                "columnOrder": 0,
                "text": "Cell A2"
            }
        ]
    )
    ```

## Sheet Operations

??? example "`unique_sdk.AgenticTable.get_sheet_data` - Get sheet data"

    Retrieve comprehensive sheet data including cells, logs, and metadata.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `includeCells` (bool, optional) - Include cell data in response
    - `includeLogHistory` (bool, optional) - Include change logs
    - `includeRowCount` (bool, optional) - Include row count
    - `includeCellMetaData` (bool, optional) - Include cell metadata
    - `startRow` (int, optional) - Start row index for range (0-based)
    - `endRow` (int, optional) - End row index for range (0-based)

    **Returns:**

    Returns an [`AgenticTableSheet`](#agentictablesheet) object.

    **Example:**

    ```python
    sheet = await unique_sdk.AgenticTable.get_sheet_data(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        includeCells=True,
        includeLogHistory=True,
        includeRowCount=True,
        includeCellMetaData=True,
        startRow=0,
        endRow=10
    )
    ```

??? example "`unique_sdk.AgenticTable.get_sheet_state` - Get sheet state"

    Get the current processing state of a sheet.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID

    **Returns:**

    Returns an [`AgenticTableSheetState`](#agentictablesheetstate) enum value.

    **Example:**

    ```python
    state = await unique_sdk.AgenticTable.get_sheet_state(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123"
    )

    print(f"State: {state}")  # "PROCESSING", "IDLE", or "STOPPED_BY_USER"
    ```

??? example "`unique_sdk.AgenticTable.update_sheet_state` - Update sheet state"

    Update the name or state of a sheet.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `name` (str, optional) - New sheet name
    - `state` (AgenticTableSheetState, optional) - New state: `"PROCESSING"`, `"IDLE"`, or `"STOPPED_BY_USER"`

    **Returns:**

    Returns an [`UpdateSheetResponse`](#updatesheetresponse) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.update_sheet_state(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        name="Updated Sheet Name",  # optional
        state="IDLE"  # optional: "PROCESSING", "IDLE", "STOPPED_BY_USER"
    )
    ```

## Activity & Status Tracking

??? example "`unique_sdk.AgenticTable.set_activity` - Set activity status"

    Set activity status for tracking long-running operations.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `activity` (Literal["DeleteRow", "DeleteColumn", "UpdateCell", "AddQuestionText", "AddMetaData", "GenerateArtifact", "SheetCompleted", "LibrarySheetRowVerified"], required) - Activity type
    - `status` (Literal["IN_PROGRESS", "COMPLETED", "FAILED"], required) - Activity status
    - `text` (str, required) - Activity description text

    **Returns:**

    Returns an [`AgenticTableCell`](#agentictablecell) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.set_activity(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        activity="UpdateCell",
        status="IN_PROGRESS",
        text="Updating cells with AI-generated content"
    )
    ```

??? example "`unique_sdk.AgenticTable.set_artifact` - Attach artifact"

    Attach an artifact (document) to the sheet.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `name` (str, required) - Artifact name
    - `contentId` (str, required) - Content ID of the artifact document
    - `mimeType` (str, required) - MIME type (e.g., "application/pdf")
    - `artifactType` (Literal["QUESTIONS", "FULL_REPORT"], required) - Artifact type

    **Returns:**

    Returns an [`AgenticTableCell`](#agentictablecell) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.set_artifact(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        name="Generated Report",
        contentId="cont_xyz789",
        mimeType="application/pdf",
        artifactType="FULL_REPORT"
    )
    ```

## Metadata Management

??? example "`unique_sdk.AgenticTable.set_column_metadata` - Configure column properties"

    Configure column properties including width, filters, and renderers.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `columnOrder` (int, required) - Column index (0-based)
    - `columnWidth` (int, optional) - Column width in pixels
    - `filter` (FilterTypes, optional) - Filter type: `"ValueMatchFilter"`, `"PartialMatchFilter"`, `"ReferenceFilter"`, `"HallucinationFilter"`, `"ReviewStatusFilter"`, or `"AssigneeFilter"`
    - `cellRenderer` (str, optional) - Cell renderer type: `"CheckboxLockCellRenderer"`, `"CollaboratorDropdown"`, `"ReviewStatusDropdown"`, `"CustomCellRenderer"`, or `"SelectableCellRenderer"`
    - `editable` (bool, optional) - Whether column is editable

    **Returns:**

    Returns a [`ColumnMetadataUpdateStatus`](#columnmetadataupdatestatus) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.set_column_metadata(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        columnOrder=2,
        columnWidth=200,  # optional
        filter="ValueMatchFilter",  # optional
        cellRenderer="CheckboxLockCellRenderer",  # optional
        editable=True  # optional
    )
    ```

??? example "`unique_sdk.AgenticTable.set_cell_metadata` - Set cell metadata"

    Set metadata for a specific cell.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `rowOrder` (int, required) - Row index (0-based)
    - `columnOrder` (int, required) - Column index (0-based)
    - `selected` (bool, optional) - Whether cell is selected
    - `selectionMethod` (SelectionMethod, optional) - Selection method: `"DEFAULT"` or `"MANUAL"`
    - `agreementStatus` (AgreementStatus, optional) - Agreement status: `"MATCH"` or `"NO_MATCH"`

    **Returns:**

    Returns a [`ColumnMetadataUpdateStatus`](#columnmetadataupdatestatus) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.set_cell_metadata(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        rowOrder=0,
        columnOrder=1,
        selected=True,  # optional
        selectionMethod="MANUAL",  # optional
        agreementStatus="MATCH"  # optional
    )
    ```

## Bulk Operations

??? example "`unique_sdk.AgenticTable.bulk_update_status` - Bulk update status"

    Update verification status of multiple rows at once.

    **Parameters:**

    - `tableId` (str, required) - Table/sheet ID
    - `rowOrders` (List[int], required) - List of row indices to update (0-based)
    - `status` (RowVerificationStatus, required) - Verification status: `"NEED_REVIEW"`, `"READY_FOR_VERIFICATION"`, or `"VERIFIED"`

    **Returns:**

    Returns a [`ColumnMetadataUpdateStatus`](#columnmetadataupdatestatus) object.

    **Example:**

    ```python
    result = await unique_sdk.AgenticTable.bulk_update_status(
        user_id=user_id,
        company_id=company_id,
        tableId="sheet_abc123",
        rowOrders=[0, 1, 2, 3, 4],
        status="VERIFIED"
    )
    ```

## Use Cases

??? example "AI-Powered Table Processing"

    ```python
    async def process_table_with_ai(table_id):
        """Process table cells with AI."""
        
        # Set activity
        await unique_sdk.AgenticTable.set_activity(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            activity="UpdateCell",
            status="IN_PROGRESS",
            text="Processing cells with AI"
        )
        
        # Get table data
        sheet = await unique_sdk.AgenticTable.get_sheet_data(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            includeCells=True
        )
        
        # Process each cell
        for row_idx, row in enumerate(sheet.cells):
            for col_idx, cell in enumerate(row):
                if cell and cell.text:
                    # Process with AI
                    processed = await process_with_ai(cell.text)
                    
                    # Update cell
                    await unique_sdk.AgenticTable.set_cell(
                        user_id=user_id,
                        company_id=company_id,
                        tableId=table_id,
                        rowOrder=row_idx,
                        columnOrder=col_idx,
                        text=processed,
                        logEntries=[{
                            "text": "Processed by AI",
                            "createdAt": datetime.now().isoformat(),
                            "actorType": "SYSTEM"
                        }]
                    )
        
        # Complete activity
        await unique_sdk.AgenticTable.set_activity(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            activity="UpdateCell",
            status="COMPLETED",
            text="All cells processed"
        )
    ```

??? example "Bulk Populate Table"

    ```python
    async def populate_table(table_id, data):
        """Bulk populate table with data."""
        
        cells = []
        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                cells.append({
                    "rowOrder": row_idx,
                    "columnOrder": col_idx,
                    "text": str(value)
                })
        
        # Update all cells at once
        result = await unique_sdk.AgenticTable.set_multiple_cells(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            cells=cells
        )
        
        print(f"Populated {len(cells)} cells")
    ```

??? example "Review Workflow"

    ```python
    async def setup_review_workflow(table_id):
        """Configure table for review workflow."""
        
        # Configure review status column
        await unique_sdk.AgenticTable.set_column_metadata(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            columnOrder=0,
            columnWidth=150,
            filter="ReviewStatusFilter",
            cellRenderer="ReviewStatusDropdown",
            editable=True
        )
        
        # Configure assignee column
        await unique_sdk.AgenticTable.set_column_metadata(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            columnOrder=1,
            filter="AssigneeFilter",
            cellRenderer="CollaboratorDropdown",
            editable=True
        )
        
        # Mark rows for review
        await unique_sdk.AgenticTable.bulk_update_status(
            user_id=user_id,
            company_id=company_id,
            tableId=table_id,
            rowOrders=list(range(10)),  # First 10 rows
            status="NEED_REVIEW"
        )
    ```

??? example "Progress Tracking"

    ```python
    async def track_table_progress(table_id, total_rows):
        """Track processing progress."""
        
        await unique_sdk.AgenticTable.set_activity(
            tableId=table_id,
            activity="UpdateCell",
            status="IN_PROGRESS",
            text="Processing rows..."
            ...
        )
        
        for row in range(total_rows):
            # Process row
            process_row(row)
            
            # Update progress
            progress = int((row + 1) / total_rows * 100)
            await unique_sdk.AgenticTable.set_activity(
                tableId=table_id,
                activity="UpdateCell",
                status="IN_PROGRESS",
                text=f"Processing rows... {progress}%"
                ...
            )
        
        await unique_sdk.AgenticTable.set_activity(
            tableId=table_id,
            activity="SheetCompleted",
            status="COMPLETED",
            text="All rows processed"
            ...
        )
    ```

## Best Practices

??? example "Track Activities"

    ```python
    # Always set activity before long operations
    await unique_sdk.AgenticTable.set_activity(
        activity="UpdateCell",
        status="IN_PROGRESS",
        ...
    )

    try:
        # Process
        await process_table()
        
        # Mark completed
        await unique_sdk.AgenticTable.set_activity(
            activity="UpdateCell",
            status="COMPLETED",
            ...
        )
    except Exception as e:
        # Mark failed
        await unique_sdk.AgenticTable.set_activity(
            activity="UpdateCell",
            status="FAILED",
            text=f"Error: {str(e)}"
            ...
        )
    ```

??? example "Log Changes"

    ```python
    # Always log significant changes
    await unique_sdk.AgenticTable.set_cell(
        ...,
        logEntries=[{
            "text": "AI generated response based on source documents",
            "createdAt": datetime.now().isoformat(),
            "actorType": "ASSISTANT",
            "details": [{
                "text": f"Used {len(sources)} sources",
                "messageId": message_id
            }]
        }]
    )
    ```

## Input Types

#### LogEntry {#logentry}

??? note "The `LogEntry` type defines a log entry for cell changes"

    **Fields:**

    - `text` (str, required) - Log entry text
    - `createdAt` (str, required) - Creation timestamp (ISO 8601)
    - `actorType` (Literal["USER", "SYSTEM", "ASSISTANT", "TOOL"], required) - Actor type
    - `messageId` (str, optional) - Associated message ID
    - `details` (List[LogDetail], optional) - Additional log details

    **LogDetail Fields:**

    - `llmRequest` (List[Dict] | None) - LLM request data

    **Used in:** `AgenticTable.set_cell()` `logEntries` parameter

## Return Types

#### AgenticTableCell {#agentictablecell}

??? note "The `AgenticTableCell` object represents a cell in the table"

    **Fields:**

    - `sheetId` (str) - Sheet ID containing the cell
    - `rowOrder` (int) - Row index (0-based)
    - `columnOrder` (int) - Column index (0-based)
    - `rowLocked` (bool) - Whether row is locked
    - `text` (str) - Cell text content
    - `logEntries` (List[LogEntry]) - List of log entries. See [`LogEntry`](#logentry) for structure.

    **Returned by:** `AgenticTable.set_cell()`, `AgenticTable.get_cell()`, `AgenticTable.set_activity()`, `AgenticTable.set_artifact()`

#### AgenticTableSheet {#agentictablesheet}

??? note "The `AgenticTableSheet` object represents a complete sheet/table"

    **Fields:**

    - `sheetId` (str) - Unique sheet identifier
    - `name` (str) - Sheet name
    - `state` (AgenticTableSheetState) - Current state. See [`AgenticTableSheetState`](#agentictablesheetstate).
    - `chatId` (str) - Associated chat ID
    - `createdBy` (str) - Creator user ID
    - `companyId` (str) - Company ID
    - `createdAt` (str) - Creation timestamp (ISO 8601)
    - `magicTableRowCount` (int) - Total number of rows
    - `magicTableCells` (List[AgenticTableCell] | None) - List of cells (if `includeCells=True`)

    **Returned by:** `AgenticTable.get_sheet_data()`

#### AgenticTableSheetState {#agentictablesheetstate}

??? note "The `AgenticTableSheetState` enum represents sheet processing state"

    **Values:**

    - `PROCESSING` - Sheet is currently being processed
    - `IDLE` - Sheet is idle/ready
    - `STOPPED_BY_USER` - Processing stopped by user

    **Returned by:** `AgenticTable.get_sheet_state()`

#### ColumnMetadataUpdateStatus {#columnmetadataupdatestatus}

??? note "The `ColumnMetadataUpdateStatus` object indicates update operation status"

    **Fields:**

    - `status` (bool) - Whether update was successful
    - `message` (str | None) - Status message

    **Returned by:** `AgenticTable.set_column_metadata()`, `AgenticTable.set_cell_metadata()`, `AgenticTable.set_multiple_cells()`, `AgenticTable.bulk_update_status()`

#### UpdateSheetResponse {#updatesheetresponse}

??? note "The `UpdateSheetResponse` object indicates sheet update status"

    **Fields:**

    - `status` (bool) - Whether update was successful
    - `message` (str) - Status message

    **Returned by:** `AgenticTable.update_sheet_state()`

## Related Resources

- [Content API](content.md) - Manage artifacts and attachments
- [Message API](message.md) - Link table operations to messages

