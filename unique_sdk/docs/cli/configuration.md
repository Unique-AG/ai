# Configuration

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Unique CLI reads all configuration from environment variables. No config files are needed.

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `UNIQUE_USER_ID` | User ID used for all API requests | `user_12345` |
| `UNIQUE_COMPANY_ID` | Company ID used for all API requests | `company_67890` |

## Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UNIQUE_API_KEY` | API key for authenticating with the Unique platform. Not needed on localhost or in a secured cluster. | *(empty)* |
| `UNIQUE_APP_ID` | Application identifier. Not needed on localhost or in a secured cluster. | *(empty)* |
| `UNIQUE_API_BASE` | Base URL for the Unique API | `https://gateway.unique.app/public/chat-gen2` |

## Setup

### Using export

```bash
# Required
export UNIQUE_USER_ID="user_..."
export UNIQUE_COMPANY_ID="company_..."

# Optional (not needed on localhost or in a secured cluster)
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
```

### Using a .env file

Create a `.env` file and source it before running the CLI:

```bash
# .env
UNIQUE_USER_ID=user_...
UNIQUE_COMPANY_ID=company_...
# Optional — only needed when connecting to an external Unique platform
# UNIQUE_API_KEY=ukey_...
# UNIQUE_APP_ID=app_...
```

```bash
source .env
unique-cli
```

### Using direnv

If you use [direnv](https://direnv.net/), create a `.envrc` file:

```bash
# .envrc
export UNIQUE_USER_ID=user_...
export UNIQUE_COMPANY_ID=company_...
# Optional — only needed when connecting to an external Unique platform
# export UNIQUE_API_KEY=ukey_...
# export UNIQUE_APP_ID=app_...
```

## Error Handling

If any required variable is missing, the CLI exits immediately with a clear error:

```
$ unique-cli ls
Error: missing required environment variables: UNIQUE_USER_ID, UNIQUE_COMPANY_ID
```

## How Configuration is Wired

The CLI calls `load_config()` at startup, which:

1. Reads the two required environment variables (`UNIQUE_USER_ID`, `UNIQUE_COMPANY_ID`)
2. Reads optional `UNIQUE_API_KEY`, `UNIQUE_APP_ID`, and `UNIQUE_API_BASE`
3. Sets `unique_sdk.api_key`, `unique_sdk.app_id`, and `unique_sdk.api_base` globally
4. Returns a `Config` object that carries `user_id` and `company_id` for every API call

This means the underlying `unique_sdk` is fully configured before any command executes.
