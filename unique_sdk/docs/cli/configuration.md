# Configuration

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Unique CLI reads all configuration from environment variables. No config files are needed.

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `UNIQUE_API_KEY` | API key for authenticating with the Unique platform | `ukey_abc123...` |
| `UNIQUE_APP_ID` | Application identifier | `app_xyz789...` |
| `UNIQUE_USER_ID` | User ID used for all API requests | `user_12345` |
| `UNIQUE_COMPANY_ID` | Company ID used for all API requests | `company_67890` |

## Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UNIQUE_API_BASE` | Base URL for the Unique API | `https://gateway.unique.app/public/chat-gen2` |

## Setup

### Using export

```bash
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
export UNIQUE_USER_ID="user_..."
export UNIQUE_COMPANY_ID="company_..."
```

### Using a .env file

Create a `.env` file and source it before running the CLI:

```bash
# .env
UNIQUE_API_KEY=ukey_...
UNIQUE_APP_ID=app_...
UNIQUE_USER_ID=user_...
UNIQUE_COMPANY_ID=company_...
```

```bash
source .env
unique-cli
```

### Using direnv

If you use [direnv](https://direnv.net/), create a `.envrc` file:

```bash
# .envrc
export UNIQUE_API_KEY=ukey_...
export UNIQUE_APP_ID=app_...
export UNIQUE_USER_ID=user_...
export UNIQUE_COMPANY_ID=company_...
```

## Error Handling

If any required variable is missing, the CLI exits immediately with a clear error:

```
$ unique-cli ls
Error: missing required environment variables: UNIQUE_API_KEY, UNIQUE_APP_ID
```

## How Configuration is Wired

The CLI calls `load_config()` at startup, which:

1. Reads the four required environment variables
2. Sets `unique_sdk.api_key`, `unique_sdk.app_id`, and `unique_sdk.api_base` globally
3. Returns a `Config` object that carries `user_id` and `company_id` for every API call

This means the underlying `unique_sdk` is fully configured before any command executes.
