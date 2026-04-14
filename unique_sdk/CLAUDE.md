# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`unique_sdk` is the official Python SDK for the Unique AI Platform, published on PyPI as [`unique-sdk`](https://pypi.org/project/unique-sdk/). It provides API resources for search, content management, chat completions, folder operations, webhooks, and more. The package also ships an experimental CLI (`unique-cli`) for interactive file exploration.

## Commands

Run from the `unique_sdk/` directory:

```bash
uv run poe lint          # Lint with ruff
uv run poe lint-fix      # Auto-fix lint issues
uv run poe format        # Format with ruff
uv run poe test          # Run pytest
uv run poe typecheck     # Run basedpyright
uv run poe depcheck      # Check dependencies with deptry
uv run poe coverage      # Run tests with coverage
```

## Architecture

```
unique_sdk/
├── __init__.py              # Public API surface, global config (api_key, app_id, api_base)
├── _api_requestor.py        # HTTP request layer
├── _api_resource.py         # Base class for all API resources
├── _error.py                # Error hierarchy (APIError, AuthenticationError, etc.)
├── _http_client.py          # HTTP client implementations (requests, httpx, aiohttp)
├── _unique_ql.py            # UniqueQL operators and combinators
├── _webhook.py              # Webhook signature verification
├── api_resources/           # One file per API resource (Content, Folder, Search, etc.)
├── utils/                   # Utility modules (file_io, chat_history, token, sources)
└── cli/                     # CLI package (experimental)
    ├── cli.py               # Click entry point and command definitions
    ├── shell.py             # Interactive REPL (cmd.Cmd)
    ├── config.py            # Environment variable configuration
    ├── state.py             # Virtual filesystem state (cwd, scope_id)
    ├── formatting.py        # Output formatting (tables, search results)
    └── commands/            # Command implementations (navigation, files, folders, search)
```

**Naming conventions:**
- Internal modules are prefixed with `_` (e.g., `_api_resource.py`, `_error.py`)
- API resources live in `api_resources/` with `_` prefix (e.g., `_content.py`, `_folder.py`)
- Each API resource class inherits from `APIResource` and provides `create`, `get_info`, `update`, `delete` (and `*_async` variants)
- All API methods require `user_id` and `company_id` parameters

## SDK Configuration

```python
import unique_sdk

unique_sdk.api_key = "ukey_..."   # Required
unique_sdk.app_id = "app_..."     # Required
unique_sdk.api_base = "https://gateway.unique.app/public/chat-gen2"  # Default
```

## Key API Resources

| Resource | Purpose |
|----------|---------|
| `Search` | Vector, full-text, and combined search |
| `Content` | File/document management (CRUD, metadata) |
| `Folder` | Folder hierarchy management |
| `ChatCompletion` | LLM completions (streaming and non-streaming) |
| `Message` | Chat message CRUD |
| `Integrated` | Integrated chat completions with search |
| `AgenticTable` | Structured data tables |
| `Webhook` / `WebhookSignature` | Webhook event verification |

## CLI (Experimental)

The SDK ships an interactive file explorer CLI accessible via `unique-cli` or `python -m unique_sdk.cli`.

**Required environment variables:**

```bash
export UNIQUE_USER_ID="user_..."
export UNIQUE_COMPANY_ID="company_..."
```

**Optional environment variables** (not needed on localhost or in a secured cluster):

```bash
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
```

**CLI commands:**

| Command | Purpose |
|---------|---------|
| `pwd` | Print current directory |
| `cd <path>` | Change directory (supports `/`, `..`, `scope_*`, absolute/relative paths) |
| `ls [path]` | List folders and files |
| `mkdir <name>` | Create folder |
| `rmdir <target> [-r]` | Delete folder |
| `mvdir <old> <new>` | Rename folder |
| `upload <local> [dest]` | Upload file (cp-like destination resolution) |
| `download <name\|id> [local]` | Download file |
| `rm <name\|id>` | Delete file |
| `mv <old> <new>` | Rename file |
| `search <query> [--folder F] [--metadata K=V] [--limit N]` | Combined search |

**Two modes:** Interactive shell (`unique-cli`) or one-shot (`unique-cli ls /Reports`).

**CLI code conventions:**
- All command logic lives in `cli/commands/` as pure functions (`cmd_*`) that take `ShellState` and return `str`
- Both Click (one-shot) and cmd.Cmd (REPL) delegate to the same `cmd_*` functions
- `ShellState` tracks virtual cwd (path + scope_id); `Config` holds resolved env vars
- Imports within the CLI use `unique_sdk.cli.*` (not `unique_cli.*`)

## Code Style

- Python 3.11+, type hints everywhere
- Ruff for linting and formatting (`ruff check`, `ruff format`)
- basedpyright for type checking (standard mode)
- Import sorting via ruff `I` rules
- Private modules prefixed with `_`
- Never commit `.env` files or API keys
