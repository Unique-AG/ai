# Content API Resource

The Content API resource provides methods for managing content operations in the Unique SDK v2. This resource implements all the content-related endpoints from the OpenAPI specification.

## Quick Start

1. Install dependencies:
   ```bash
   pip install python-dotenv
   ```

2. Set up environment variables:
   ```bash
   cp examples/env.sample examples/.env
   # Edit .env with your API credentials
   ```

3. Run the example:
   ```bash
   python examples/content_example.py
   ```

## Available Methods

### 1. Search Content
Search for content based on filters and criteria.

```python
from unique_client import UniqueClient, Content
from unique_client.model import SearchDto, ContentWhereInput, StringFilter

client = UniqueClient(api_key="your-api-key")

search_data = SearchDto(
    where=ContentWhereInput(
        title=StringFilter(contains="report")
    ),
    chat_id="chat_123"
)

results = Content.search(
    client=client,
    user_id="user_123",
    company_id="company_456",
    search_data=search_data
)
```

### 2. Get Content Information
Retrieve content information based on metadata filters.

```python
from unique_client.model import ContentInfoDto

info_request = ContentInfoDto(
    metadata_filter={"type": "document"},
    take=10,
    skip=0
)

content_info = Content.get_info(
    client=client,
    user_id="user_123",
    company_id="company_456",
    info_request=info_request
)
```

### 3. Upsert Content
Create or update content.

```python
from unique_client.model import ContentUpsertDto, ContentUpsertInputDto

upsert_data = ContentUpsertDto(
    input=ContentUpsertInputDto(
        key="document-key",
        title="Document Title",
        mime_type="application/pdf",
        byte_size=1024000,
        url="https://example.com/document.pdf",
        metadata={"category": "financial"}
    ),
    scope_id="scope_123",
    store_internally=True
)

result = Content.upsert(
    client=client,
    user_id="user_123",
    company_id="company_456",
    upsert_data=upsert_data
)
```

### 4. Query Table
Execute SQL queries on table data with configuration.

```python
from unique_client.model import QueryTableRequest, TableConfigDto, TableColumnDto

table_config = TableConfigDto(
    table_file_name="data.xlsx",
    columns=[
        TableColumnDto(name="id", type="string", identifying=True),
        TableColumnDto(name="value", type="number")
    ],
    row_filter="value > 0",
    repeating_table="data_table",
    header="Data Report",
    footer="End of Report",
    no_data_found="No data available"
)

query_request = QueryTableRequest(
    query="SELECT * FROM data WHERE year = 2024",
    table_config=table_config
)

results = Content.query_table(
    client=client,
    user_id="user_123",
    company_id="company_456",
    query_request=query_request
)
```

### 5. Export to Excel
Export data to Excel format using templates.

```python
from unique_client.model import ExcelExportRequestDto

export_request = ExcelExportRequestDto(
    template_name="financial_template",
    scope_id="scope_123",
    data={"year": 2024, "quarter": "Q1"},
    resulting_filename="report_q1_2024.xlsx"
)

export_result = Content.export_excel(
    client=client,
    user_id="user_123",
    company_id="company_456",
    export_request=export_request
)
```

### 6. Get Table Attributes
Retrieve table attributes based on configuration.

```python
from unique_client.model import TableConfigDto

table_config = TableConfigDto(
    table_file_name="config.xlsx",
    columns=[...],  # Table column definitions
    row_filter="active = true",
    repeating_table="config_table",
    header="Configuration",
    footer="End",
    no_data_found="No configuration found"
)

attributes = Content.get_table_attributes(
    client=client,
    user_id="user_123",
    company_id="company_456",
    table_config=table_config
)
```

### 7. Get File Content
Retrieve file content by ID.

```python
file_content = Content.get_file_content(
    client=client,
    user_id="user_123",
    company_id="company_456",
    content_id="content_123",
    chat_id="chat_789"
)
```

## Async Support

All methods have async counterparts with the `_async` suffix:

```python
import asyncio

async def main():
    # Async search example
    results = await Content.search_async(
        client=client,
        user_id="user_123",
        company_id="company_456",
        search_data=search_data
    )

asyncio.run(main())
```

## Error Handling

All methods can raise exceptions from the `unique_client._error` module:

```python
from unique_client._error import APIError, InvalidRequestError

try:
    results = Content.search(client, user_id, company_id, search_data)
except InvalidRequestError as e:
    print(f"Invalid request: {e}")
except APIError as e:
    print(f"API error: {e}")
```

## Models

The Content resource uses the following Pydantic models from `unique_client.model`:

- `SearchDto` - Search criteria and filters
- `ContentInfoDto` - Content information request
- `ContentUpsertDto` - Content upsert data
- `ContentUpsertInputDto` - Content input data
- `QueryTableRequest` - Table query request
- `TableConfigDto` - Table configuration
- `TableColumnDto` - Table column definition
- `ExcelExportRequestDto` - Excel export request
- `ContentWhereInput` - Content filter conditions
- `StringFilter` - String filtering options

For detailed model definitions and field descriptions, refer to the `model.py` file. 