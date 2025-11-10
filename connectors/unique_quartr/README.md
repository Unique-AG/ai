# Unique Quartr Connector

A Python connector library for the [Quartr API](https://quartr.com), providing easy access to company events, documents, and financial data.

## Features

- 🔍 Fetch company earnings calls and events
- 📄 Retrieve event documents (transcripts, reports, slides, etc.)
- 🎯 Type-safe API with Pydantic models
- 🔄 Automatic pagination handling
- 📊 Support for multiple document and event types
- 🔐 Secure API key authentication

## Installation

```bash
poetry add unique_quartr
```

Or using pip:

```bash
pip install unique_quartr
```

## Configuration

### Environment Variables

Create a `.env` file in your project root with your Quartr API credentials:

```env
QUARTR_API_CREDS='{"api_key": "your_api_key_here", "valid_to": "2025-12-31"}'
QUARTR_API_ACTIVATED_COMPANIES='["company_id_1", "company_id_2"]'
```

### Test Environment

For testing, create `tests/test.env`:

```env
QUARTR_API_CREDS='{"api_key": "test_api_key", "valid_to": "2025-12-31"}'
QUARTR_API_ACTIVATED_COMPANIES='["test_company"]'
```

## Quick Start

### Basic Usage

```python
from unique_quartr.service import QuartrService
from unique_quartr.constants.event_types import EventType
from unique_quartr.constants.document_types import DocumentType
from unique_toolkit._common.endpoint_requestor import RequestorType

# Initialize the service
service = QuartrService(
    company_id="your_company_id",
    requestor_type=RequestorType.REQUESTS,
)

# Define the event types you want to fetch
event_types = [EventType.EARNINGS_CALL]
event_ids = service.get_event_subtype_ids_from_event_types(event_types)

# Fetch company events
events = service.fetch_company_events(
    ticker="AAPL",
    exchange="NasdaqGS",
    country="US",
    event_ids=event_ids,
    start_date="2024-01-01",
    end_date="2024-12-31",
)

print(f"Found {len(events)} events")
for event in events:
    print(f"Event: {event['title']} - {event['date']}")
```

### Fetching Documents

```python
# Get event IDs from the events you fetched
event_ids = [event["id"] for event in events]

# Define document types you want
document_types = [DocumentType.TRANSCRIPT, DocumentType.SLIDES]
document_ids = service.get_document_ids_from_document_types(document_types)

# Fetch documents for these events
documents = service.fetch_event_documents(
    event_ids=event_ids,
    document_ids=document_ids,
)

print(f"Found {len(documents)} documents")
for doc in documents:
    print(f"Document: {doc['type_id']} - {doc['file_url']}")
```

## Event Types

The library supports the following event types:

- **Earnings Call**: Q1, Q2, Q3, Q4, H1, H2
- **Analyst Day**
- **Annual General Meeting**: AGM, Scheme Meeting
- **Business Combination**
- **C-level Sitdown**: C-level Sitdown, CEO Sitdown
- **Capital Markets Day**
- **Capital Raise**
- **Conference**
- **Extraordinary General Meeting**
- **FDA Announcement**
- **Fireside Chat**
- **Investor Day**
- **M&A Announcement**
- **Outlook / Guidance Update**
- **Partnerships / Collaborations**: Partnership, Collaboration
- **Product / Service Launch**: Product Launch, Service Launch
- **Slides**: Investor Presentation, Corporate Presentation, Company Presentation
- **Trading Update**
- **Update / Briefing**: Status Update, Investor Update, ESG Update, Study Update, Study Result, KOL Event

### Example: Getting Earnings Call Event IDs

```python
from unique_quartr.constants.event_types import EventType

event_types = [EventType.EARNINGS_CALL]
event_ids = QuartrService.get_event_subtype_ids_from_event_types(event_types)
# Returns: [26, 27, 28, 29, 35, 36] (Q1, Q2, Q3, Q4, H1, H2)
```

## Document Types

The library supports various document types:

- **Slides** 📊
- **Report** 📄
- **Quarterly Report (10-Q)** 📑
- **Earnings Release (8-K)** 📢
- **Annual Report (10-K)** 📘
- **Annual Report (20-F)** 📙
- **Annual Report (40-F)** 📕
- **Earnings Release (6-K)** 📣
- **Transcript** 🗒️
- **Interim Report** 📜
- **Press Release** 🗞️
- **Earnings Release** 💰
- **In-house Transcript** 🎤

### Example: Getting Document Type Information

```python
from unique_quartr.constants.document_types import DocumentType

doc_type = DocumentType.QUARTERLY_REPORT_10Q

print(doc_type.name)  # "Quarterly report"
print(doc_type.form)  # "10-Q"
print(doc_type.emoji)  # "📑"
print(doc_type.get_file_prefix())  # "Quarterly report (10-Q)"
```

## Advanced Usage

### Custom Pagination

Control pagination parameters for large datasets:

```python
events = service.fetch_company_events(
    ticker="AAPL",
    exchange="NasdaqGS",
    country="US",
    event_ids=event_ids,
    limit=100,  # Items per page (max 500)
    max_iteration=10,  # Maximum number of pages
)
```

### Filtering by Date Range

```python
events = service.fetch_company_events(
    ticker="AAPL",
    exchange="NasdaqGS",
    country="US",
    event_ids=event_ids,
    start_date="2024-01-01T00:00:00Z",  # ISO format
    end_date="2024-03-31T23:59:59Z",
)
```

### Fetching Multiple Event Types

```python
from unique_quartr.constants.event_types import EventType

# Combine multiple event types
event_types = [
    EventType.EARNINGS_CALL,
    EventType.ANALYST_DAY,
    EventType.INVESTOR_DAY,
]

event_ids = QuartrService.get_event_subtype_ids_from_event_types(event_types)

events = service.fetch_company_events(
    ticker="AAPL",
    exchange="NasdaqGS",
    country="US",
    event_ids=event_ids,
)
```

## API Reference

### QuartrService

```python
class QuartrService:
    def __init__(
        self,
        *,
        company_id: str,
        requestor_type: RequestorType,
    ):
        """
        Initialize the Quartr service.
        
        Args:
            company_id: Company identifier for API access
            requestor_type: Type of requestor (SYNC or ASYNC)
        """
```

#### Methods

##### fetch_company_events

```python
def fetch_company_events(
    self,
    ticker: str,
    exchange: str,
    country: str,
    event_ids: list[int],
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
    max_iteration: int = 20,
) -> list[EventDto]:
    """
    Retrieve events for a given company.
    
    Args:
        ticker: Company ticker symbol (e.g., 'AAPL', 'AMZN')
        exchange: Exchange code (e.g., 'NasdaqGS', 'NYSE')
        country: Country code (e.g., 'US', 'CA')
        event_ids: List of event type IDs to filter
        start_date: Optional start date in ISO format
        end_date: Optional end date in ISO format
        limit: Items per request (max 500)
        max_iteration: Maximum number of pagination iterations
    
    Returns:
        List of event dictionaries
    """
```

##### fetch_event_documents

```python
def fetch_event_documents(
    self,
    event_ids: list[int],
    document_ids: list[int],
    limit: int = 500,
    max_iteration: int = 20,
) -> list[DocumentDto]:
    """
    Retrieve documents for a list of events.
    
    Args:
        event_ids: List of event IDs
        document_ids: List of document type IDs to filter
        limit: Items per request (max 500)
        max_iteration: Maximum number of pagination iterations
    
    Returns:
        List of document dictionaries
    """
```

##### Static Methods

```python
@staticmethod
def get_event_subtype_ids_from_event_types(
    event_types: list[EventType],
) -> list[int]:
    """
    Convert EventType enums to Quartr API event subtype IDs.
    
    Args:
        event_types: List of EventType enums
    
    Returns:
        List of event subtype IDs
    """

@staticmethod
def get_document_ids_from_document_types(
    document_types: list[DocumentType],
) -> list[int]:
    """
    Convert DocumentType enums to Quartr API document type IDs.
    
    Args:
        document_types: List of DocumentType enums
    
    Returns:
        List of document type IDs
    """
```

## Response Models

### EventDto

```python
{
    "company_id": float,
    "date": datetime,
    "id": float,
    "title": str,
    "type_id": float,
    "fiscal_year": float | None,
    "fiscal_period": str | None,
    "backlink_url": str,
    "updated_at": datetime,
    "created_at": datetime,
}
```

### DocumentDto

```python
{
    "company_id": float | None,
    "event_id": float | None,
    "file_url": str,
    "id": float,
    "type_id": float,
    "updated_at": datetime,
    "created_at": datetime,
}
```

## Testing

Run the test suite:

```bash
poetry run pytest
```

Run with coverage:

```bash
poetry run pytest --cov=unique_quartr --cov-report=html
```

Run specific test files:

```bash
poetry run pytest tests/test_service.py
poetry run pytest tests/test_constants.py
```

## Error Handling

The library will raise exceptions in the following cases:

- **Missing API Credentials**: `ValueError` when `QUARTR_API_CREDS` is not set
- **Company Not Activated**: `ValueError` when the company_id is not in `QUARTR_API_ACTIVATED_COMPANIES`
- **API Errors**: Various HTTP errors from the Quartr API

### Example Error Handling

```python
from unique_quartr.service import QuartrService

try:
    service = QuartrService(
        company_id="invalid_company",
        requestor_type=RequestorType.SYNC,
    )
except ValueError as e:
    print(f"Configuration error: {e}")
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone <repository_url>
cd unique_quartr

# Install dependencies
poetry install

# Run linting
poetry run ruff check .

# Run formatting
poetry run ruff format .
```

### Project Structure

```
unique_quartr/
├── constants/
│   ├── document_types.py    # Document type enums and mappings
│   └── event_types.py        # Event type enums and mappings
├── endpoints/
│   ├── api.py                # API endpoint definitions
│   └── schemas.py            # Pydantic models for API requests/responses
├── helpers.py                # Helper utilities
├── service.py                # Main service class
└── settings.py               # Configuration and settings
```

## License

Proprietary

## Authors

- Rami Azouz <rami.ext@unique.ch>

## Support

For issues and questions, please contact the maintainers or refer to the [Quartr API documentation](https://quartr.com/api).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
