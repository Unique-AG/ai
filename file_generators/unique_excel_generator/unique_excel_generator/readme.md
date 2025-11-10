## Documentation for `ExcelGeneratorService`

### Overview

`ExcelGeneratorService` is a service class designed to generate Excel files (`.xlsx`) from Pandas DataFrames. It includes functionality to customize the Excel file format, add worksheets, and upload the generated file to a content management system, making it easy to automate the creation and sharing of Excel files.

### Constructor
```python
ExcelGeneratorService(
    event: ChatEvent,
    config: ExcelGeneratorConfig,
)
```

#### Parameters:
- `event`: An `ChatEvent` object containing event data (e.g., chat payload).
- `config`: Configuration object (`ExcelGeneratorConfig`) defining formatting, column renaming, and upload settings.

#### Example Usage:
```python
event = ChatEvent(payload={...})
config = ExcelGeneratorConfig(rename_col_map={"old_col": "new_col"}, upload_scope_id="1234")

excel_service = ExcelGeneratorService(event, config)
```

### Methods

#### 1. `init_workbook(save_dir: Path, file_name: str, suffix: Optional[str] = None)`
Initializes the Excel workbook and sets the file path where the Excel file will be saved.

##### Parameters:
- `save_dir`: The directory where the generated Excel file will be saved.
- `file_name`: The name of the file to be exported.
- `suffix`: An optional suffix to append to the file name. Defaults to `None`.

##### Example:
```python
save_dir = Path("/path/to/save")
file_name = "report"
excel_service.init_workbook(save_dir=save_dir, file_name=file_name, suffix="v1")
```

#### 2. `add_worksheet(dataframe: pd.DataFrame, worksheet_name: str)`
Adds a worksheet to the Excel workbook, based on the provided Pandas DataFrame.

##### Parameters:
- `dataframe`: A Pandas DataFrame containing the data to be written into the worksheet.
- `worksheet_name`: The name of the worksheet in the Excel file.

##### Example:
```python
df = pd.DataFrame({"Name": ["Alice", "Bob"], "Score": [85, 90]})
excel_service.add_worksheet(dataframe=df, worksheet_name="Scores")
```

> **Note**: Make sure to call `init_workbook()` before adding any worksheets.

#### 3. `reference_and_upload(sequence_number: int) -> ContentReference | None`
Closes the Excel workbook, uploads the file to the chat or other specified scope, and returns a reference to the uploaded content.

##### Parameters:
- `sequence_number`: Integer representing the sequence number of the content.

##### Returns:
- `ContentReference`: An object that contains details of the uploaded file (e.g., `id`, `sequence_number`, `name`, `url`). Returns `None` if the file is empty or the workbook was not initialized.

##### Example:
```python
reference = excel_service.reference_and_upload(sequence_number=1)
```

### Supporting Classes

#### `ExcelGeneratorConfig`
Represents the configuration for generating the Excel file. It includes formatting options, column renaming, and upload scope settings.

##### Attributes:
- `upload_scope_id`: (Optional) The scope ID for where the content will be uploaded.
- `rename_col_map`: (Optional) A dictionary for renaming columns in the DataFrame before they are added to the Excel file.
- `table_header_format`: A dictionary of formatting options for the table headers (e.g., background color, font).
- `table_data_format`: A dictionary of formatting options for the table data (e.g., text alignment, font color).

##### Example:
```python
config = ExcelGeneratorConfig(
    upload_scope_id="4567",
    rename_col_map={"old_column": "new_column"},
    table_header_format={
        "bg_color": "#333333",
        "bold": True,
        "font_color": "white"
    },
    table_data_format={
        "bg_color": "#FFFFFF",
        "bold": False,
        "font_color": "black",
        "border": 1
    }
)
```

### Error Handling

1. **Workbook Not Initialized**: If you attempt to add a worksheet or reference the file before calling `init_workbook()`, the service will log an error:
    ```plaintext
    "It seems that you forgot to initialize the workbook."
    ```
2. **Empty DataFrame**: If the DataFrame is empty, no worksheet will be added, and during upload, a warning will be logged:
    ```plaintext
    "The Excel file is empty. No content will be uploaded."
    ```

### Example Workflow

```python
# Initialize the service
event = ChatEvent(payload={...})
config = ExcelGeneratorConfig(rename_col_map={"Name": "Full Name"})
logger = Logger()

excel_service = ExcelGeneratorService(event, config, logger)

# Initialize the workbook
save_dir = Path("/save/directory")
excel_service.init_workbook(save_dir=save_dir, file_name="report")

# Add a worksheet with a DataFrame
df = pd.DataFrame({"Name": ["Alice", "Bob"], "Score": [85, 90]})
excel_service.add_worksheet(dataframe=df, worksheet_name="Scores")

# Upload and get reference
reference = excel_service.reference_and_upload(sequence_number=1)
```

---

`ExcelGeneratorService` allows for easy automation of Excel file generation, formatting, and uploading. It integrates seamlessly with other content management systems, providing a streamlined solution for exporting and distributing data in Excel format.