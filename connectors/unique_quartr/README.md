# Unique Quartr Connector

A Python connector library for the [Quartr API](https://quartr.com), providing easy access to company events, documents, and financial data.

## Features

- 🔍 Fetch company earnings calls and events
- 📄 Retrieve event documents (transcripts, reports, slides, etc.)
- 📝 Parse and export earnings call transcripts to markdown
- 🎯 Type-safe API with Pydantic models
- 🔄 Automatic pagination handling
- 📊 Support for multiple document and event types
- 🔐 Secure API key authentication with base64 encoding

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
# Base64-encoded JSON credentials
QUARTR_API_CREDS='xxxxxxxxxxx'
QUARTR_API_ACTIVATED_COMPANIES='["company_id_1", "company_id_2"]'
```

**Note**: The `QUARTR_API_CREDS` should be a base64-encoded JSON string containing:
```json
{"api_key": "your_api_key_here", "valid_to": "2025-12-31"}
```

You can encode your credentials using:
```python
import base64
import json

creds = {"api_key": "your_api_key_here", "valid_to": "2025-12-31"}
encoded = base64.b64encode(json.dumps(creds).encode()).decode()
print(encoded)
```

### Test Environment

For testing, create `tests/test.env`:

```env
QUARTR_API_CREDS='xxxxxxxxxxx'
QUARTR_API_ACTIVATED_COMPANIES='["test_company"]'
```

## Quick Start

### Basic Usage

```python
from unique_quartr.service import QuartrService
from unique_quartr.constants.event_types import EventType
from unique_quartr.constants.document_types import DocumentType
from unique_toolkit._common.experimental.endpoint_requestor import RequestorType

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

print(f"Found {len(events.data)} events")
for event in events.data:
    print(f"Event: {event.title} - {event.date}")
```

### Fetching Documents

```python
# Get event IDs from the events you fetched
event_ids = [event.id for event in events.data]

# Define document types you want
document_types = [DocumentType.TRANSCRIPT, DocumentType.SLIDES]
document_ids = service.get_document_ids_from_document_types(document_types)

# Fetch documents for these events
documents = service.fetch_event_documents(
    event_ids=event_ids,
    document_ids=document_ids,
)

print(f"Found {len(documents.data)} documents")
for doc in documents.data:
    print(f"Document: {doc.type_id} - {doc.file_url}")
```

### Working with Earnings Call Transcripts

```python
from unique_quartr.transcripts.earnings_call import QuartrEarningsCallTranscript

# Fetch transcript from Quartr URL
transcript_url = "https://quartr.com/transcript/12345.json"
transcript = QuartrEarningsCallTranscript.from_quartr_transcript_url(transcript_url)

# Or use async version
transcript = await QuartrEarningsCallTranscript.from_quartr_transcript_url_async(transcript_url)

# Export to markdown
markdown_content = transcript.to_markdown()
print(markdown_content)

# Access transcript data
print(f"Event ID: {transcript.event_id}")
print(f"Company ID: {transcript.company_id}")
print(f"Number of speakers: {transcript.transcript.number_of_speakers}")

# Iterate through paragraphs
for paragraph in transcript.transcript.paragraphs:
    speaker_name = transcript._get_speaker_name(paragraph.speaker)
    print(f"{speaker_name}: {paragraph.text[:100]}...")
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
# Method signature (overloaded)
def fetch_company_events(
    self,
    *,
    company_ids: list[int | float] | None = None,
    ticker: str | None = None,
    exchange: str | None = None,
    country: str | None = None,
    event_ids: list[int] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
    max_iteration: int = 20,
) -> EventResults:
    """
    Retrieve events for a given company.
    
    Args:
        company_ids: List of company IDs (alternative to ticker/exchange/country)
        ticker: Company ticker symbol (e.g., 'AAPL', 'AMZN')
        exchange: Exchange code (e.g., 'NasdaqGS', 'NYSE')
        country: Country code (e.g., 'US', 'CA')
        event_ids: List of event type IDs to filter
        start_date: Optional start date in ISO format
        end_date: Optional end date in ISO format
        limit: Items per request (max 500)
        max_iteration: Maximum number of pagination iterations
    
    Returns:
        EventResults object with .data containing list of EventDto objects
        
    Note:
        Either company_ids OR (ticker, exchange, country) must be provided
    """
```

**Example with company IDs:**
```python
events = service.fetch_company_events(
    company_ids=[4742, 5025],
    event_ids=event_ids,
    start_date="2024-01-01",
)
```

**Example with ticker/exchange:**
```python
events = service.fetch_company_events(
    ticker="AAPL",
    exchange="NasdaqGS",
    country="US",
    event_ids=event_ids,
)
```

##### fetch_event_documents

```python
def fetch_event_documents(
    self,
    event_ids: list[int],
    document_ids: list[int],
    limit: int = 500,
    max_iteration: int = 20,
) -> DocumentResults:
    """
    Retrieve documents for a list of events.
    
    Args:
        event_ids: List of event IDs
        document_ids: List of document type IDs to filter
        limit: Items per request (max 500)
        max_iteration: Maximum number of pagination iterations
    
    Returns:
        DocumentResults object with .data containing list of DocumentDto objects
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

### EventResults

Wrapper object returned by `fetch_company_events`:

```python
class EventResults:
    data: list[EventDto]  # Access events via .data attribute
```

### EventDto

```python
class EventDto:
    company_id: float
    date: datetime
    id: float
    title: str
    type_id: float
    fiscal_year: float | None
    fiscal_period: str | None
    backlink_url: str
    updated_at: datetime
    created_at: datetime
```

### DocumentResults

Wrapper object returned by `fetch_event_documents`:

```python
class DocumentResults:
    data: list[DocumentDto]  # Access documents via .data attribute
```

### DocumentDto

```python
class DocumentDto:
    company_id: float | None
    event_id: float | None
    file_url: str
    id: float
    type_id: float
    updated_at: datetime
    created_at: datetime
```

### QuartrEarningsCallTranscript

Complete earnings call transcript with speaker mapping:

```python
class QuartrEarningsCallTranscript:
    version: str
    event_id: int
    company_id: int
    transcript: Transcript
    speaker_mapping: list[SpeakerMapping]
    
    # Methods
    def to_markdown(self) -> str
    @classmethod
    def from_quartr_transcript_url(cls, url: str) -> Self
    @classmethod
    async def from_quartr_transcript_url_async(cls, url: str) -> Self
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
├── transcripts/
│   └── earnings_call/
│       ├── __init__.py       # Transcript module exports
│       ├── schema.py          # Transcript data models
│       └── transcript_template.j2  # Jinja2 template for markdown export
├── service.py                # Main service class
└── settings.py               # Configuration and settings
```

## License

Proprietary

## Authors

- Rami Azouz <rami.ext@unique.ch>

## Support

For issues and questions, please contact the maintainers or refer to the [Quartr API documentation](https://quartr.dev/api-reference).
