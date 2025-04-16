# Getting started

## Installation

Unique SDK is available on PyPI and can be installed using pip:

```bash
pip install unique_sdk
```

We recommend using a virtual environment to install Unique SDK.

```bash
python -m venv venv
source venv/bin/activate
pip install unique_sdk
```

## Requirements

- Python >=3.11 (Other Python versions 3.6+ might work but are not tested)
- requests (peer dependency. Other HTTP request libraries might be supported in the future)
- Unique App-ID & API Key

Please contact your customer success manager at Unique for your personal developer App-ID & API Key.

## Usage

```python
import unique_sdk
```

## Authentication

Unique SDK uses API keys to authenticate requests. This is an essential step to be able to use the SDK and communicate with the unique platform.

```python
unique_sdk.api_base = "https://gateway.<BASE_URL>/public/chat"
unique_sdk.api_key = "ukey_<your_api_key>"
unique_sdk.app_id = "app_<your_app_id>"
```

> [!NOTE] Base URL
> `<BASE_URL>` is the base URL of the unique platform you are using. For example, for the US region, the base URL is `us.unique.app`. If your url to the platform is `https://next.unique.app/chat`, then your base URL is `next.unique.app`.

