# The Basics


The column styles provide a way to control the visual styling and behavior of the cells in a column.

You can see a list of all the column styles in the [Column Styling](column_styling.md) section.

## Markdown rendering

Here we specifically focus on `CellRendererTypes.CUSTOM_CELL_RENDERER`.
Any text entered as markdown is rendered accordingly in the cell when using this cell renderer.

Here are a few examples of markdown that can be rendered in the cell:

### Links
```markdown
[Link Text](https://www.example.com)
```
### Images
```markdown
![Image Description](https://www.example.com/image.png)
```
### Lists
```markdown
1. List Item 1
2. List Item 2
```
### Tables
```markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
```

## References

References are a special component in the unique platform. 
A set of references are associated with a message with an ID and are stored and maintained in the backend.
You might have seen these IDs when working with the chat service. When generating text and including references, you will need to use the following format:

![References](images/references.png)

```markdown
[X&msg_<message_id>]
```

An example of a reference in the text of a cell:

```markdown
- Here is a reference to an answer I have stated earlier: [0&msg_41mnbl14324ljkb143]
```

In the above example, the message refers to the first (0 indexed) reference in the message with the id `msg_41mnbl14324ljkb143`.

> **NOTE**: The rendering of references in chat is different from that in the agentic table.

## Cell Selection

Cell metadata allows you to control the visual styling and state of individual cells in the Agentic Table. This includes selection state, selection method, and agreement status.

![Cell Selection](images/selection.png)

```python
AgenticTableService.set_cell_metadata(
    row=row_index, 
    column=column_index, 
    selected=selected, 
    selection_method=selection_method, 
    agreement_status=agreement_status
)
```

### Parameters

- `row` (int, required)
The row index (0-based) of the cell to update.

- `column` (int, required)
The column index (0-based) of the cell to update.

- `selected` (bool | None, optional)
Whether the cell is selected. This controls the visual selection state of the cell.

- `True`: Cell is selected
- `False`: Cell is not selected
- `None`: No change to selection state

- `selection_method` (SelectionMethod | None, optional)
The method used to select the cell. This indicates how the selection was made.

**Possible values:**
- `SelectionMethod.DEFAULT`: Default selection method (typically automatic/programmatic)
- `SelectionMethod.MANUAL`: Manual selection by the user

**Example:**
```python
from unique_toolkit.agentic_table import SelectionMethod

await service.set_cell_metadata(
    row=0,
    column=1,
    selected=True,
    selection_method=SelectionMethod.MANUAL
)
```

- `agreement_status` (AgreementStatus | None, optional)
The agreement status of the cell. This is used to indicate whether the cell content matches expected values or has been verified.

**Possible values:**
- `AgreementStatus.MATCH`: Cell content matches expected values
- `AgreementStatus.NO_MATCH`: Cell content does not match expected values

**Example:**
```python
from unique_toolkit.agentic_table import AgreementStatus

await service.set_cell_metadata(
    row=0,
    column=1,
    agreement_status=AgreementStatus.MATCH
)
```

### Complete Example

```python
from unique_toolkit.agentic_table import (
    AgenticTableService,
    SelectionMethod,
    AgreementStatus
)

# Initialize the service
service = AgenticTableService(
    user_id="user_123",
    company_id="company_456",
    table_id="table_789"
)

# Set cell metadata with all parameters
await service.set_cell_metadata(
    row=0,
    column=1,
    selected=True,
    selection_method=SelectionMethod.MANUAL,
    agreement_status=AgreementStatus.MATCH
)

# Update only the agreement status
await service.set_cell_metadata(
    row=0,
    column=2,
    agreement_status=AgreementStatus.NO_MATCH
)

# Clear selection
await service.set_cell_metadata(
    row=1,
    column=0,
    selected=False
)
```

## Notes

- All parameters except `row` and `column` are optional. You can update any combination of metadata fields.
- Setting a parameter to `None` will not change that field's current value.
- Cell metadata is separate from row metadata and sheet metadata. It is specifically used for cell-level styling and state management.
- When retrieving sheet data, you can include cell metadata by setting `include_cell_meta_data=True` in the `get_sheet()` method.

## Row verification status

The row verification status is used to indicate whether the row has been verified.
Once a row is marked as verified, it will be locked and not editable by the user until the verification status is reverted.

```python
AgenticTableService.update_row_verification_status(
    row_orders=row_orders,
    status=status
)
```