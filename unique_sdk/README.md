# Unique Python SDK

The official Python SDK for the [Unique AI Platform](https://unique.ch). Provides API resources for search, content management, chat completions, folder operations, webhooks, and more — plus an interactive CLI file explorer.

## Installation

```bash
pip install unique-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install unique-sdk
```

## Quick Start

```python
import unique_sdk

unique_sdk.api_key = "ukey_..."
unique_sdk.app_id = "app_..."

results = unique_sdk.Search.create(
    user_id="user_123",
    company_id="company_456",
    searchString="quarterly report",
    searchType="COMBINED",
    limit=10,
)
```

## CLI (Experimental)

The SDK ships with `unique-cli`, a Linux-like file explorer for the Unique knowledge base:

```bash
# Set required env vars
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
export UNIQUE_USER_ID="user_..."
export UNIQUE_COMPANY_ID="company_..."

# Interactive shell
unique-cli

# One-shot commands
unique-cli ls /Reports
unique-cli search "revenue growth" --limit 50
unique-cli upload ./report.pdf
```

## Documentation

Visit [https://unique-ag.github.io/ai/unique-sdk/](https://unique-ag.github.io/ai/unique-sdk/) for the full documentation.
