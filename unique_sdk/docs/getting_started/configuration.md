# Configuration

Configure the Unique Python SDK with your credentials.

## Prerequisites

Before you begin, you'll need:

- Python 3.11 or higher
- Unique App ID and API Key (contact your Unique customer success manager)
- User ID and Company ID for API requests

## Basic Setup

Configure the SDK with your credentials:

```python
import unique_sdk

# Set your API credentials
unique_sdk.api_key = "ukey_..."
unique_sdk.app_id = "app_..."
```

## Environment Variables (Recommended)

For better security, use environment variables:

```bash
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
```

Then load them in your code:

```python
import os
import unique_sdk

unique_sdk.api_key = os.getenv("UNIQUE_API_KEY")
unique_sdk.app_id = os.getenv("UNIQUE_APP_ID")
```

## Using python-dotenv

Alternatively, use a `.env` file with `python-dotenv`:

```bash
pip install python-dotenv
```

Create a `.env` file:

```env
UNIQUE_API_KEY=ukey_...
UNIQUE_APP_ID=app_...
```

Load in your code:

```python
from dotenv import load_dotenv
import os
import unique_sdk

load_dotenv()

unique_sdk.api_key = os.getenv("UNIQUE_API_KEY")
unique_sdk.app_id = os.getenv("UNIQUE_APP_ID")
```

## Next Steps

Now that you've configured the SDK:

1. **[Try the Quickstart guide](quickstart.md)** - Make your first API call
2. **[Explore API Resources](../api_resources/index.md)** - Browse available APIs
3. **[Read the Architecture guide](../architecture.md)** - Understand SDK structure
4. **[Check out Tutorials](../tutorials/folder_updates.md)** - See step-by-step tutorials
5. **[View the full SDK documentation](../sdk.md)** - Complete API reference