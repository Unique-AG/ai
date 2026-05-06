# MCP Server Multiplexer

A single-process service that multiplexes multiple [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) servers, each under its own URL path. New servers are added by creating a module folder and registering it in a YAML config file — no changes to the multiplexer itself.

## Motivation

Running a separate process per MCP server becomes unwieldy as the number of servers grows. This service solves that by dynamically loading any number of FastMCP server modules into a single Starlette/ASGI process, each isolated under its own HTTP path:

```
http://localhost:5032/hello/mcp      -> Hello Server (tools: hello)
http://localhost:5032/goodbye/mcp    -> Goodbye Server (tools: bye)
http://localhost:5032/weather/mcp    -> (add your own)
```

Clients connect to each URL independently and only see the tools belonging to that server.

## Architecture

The design mirrors the dynamic blueprint loader in `python/assistants/bundles/core/src/app.py`. That service reads a `modules.yaml` file, imports each module's Quart blueprint, and registers it on the main app. This service does the same thing but with FastMCP servers instead of Quart blueprints:

```
                  ┌─────────────────────┐
                  │  mcp-modules.yaml   │
                  │  - hello            │
                  │  - goodbye          │
                  └────────┬────────────┘
                           │ read
                  ┌────────▼────────────┐
                  │  app.py (loader)    │
                  │  register_mcp_      │
                  │  servers()          │
                  └──┬──────────────┬───┘
          import     │              │    import
       hello.app.mcp │              │ goodbye.app.mcp
                     ▼              ▼
            ┌──────────┐   ┌──────────────┐
            │ hello/   │   │ goodbye/     │
            │ app.py   │   │ app.py       │
            │ mcp=     │   │ mcp=         │
            │ FastMCP()│   │ FastMCP()    │
            └────┬─────┘   └──────┬───────┘
                 │  http_app()    │  http_app()
                 ▼                ▼
            ┌─────────────────────────────┐
            │   Starlette ASGI App        │
            │                             │
            │   Mount("/hello",  ...)     │
            │   Mount("/goodbye", ...)    │
            │   Route("/health", ...)     │
            └─────────────────────────────┘
                         │
                    uvicorn :5032
```

**Key concepts:**

- Each module exposes a `mcp` variable (a `FastMCP` instance) in its `app.py`.
- The loader calls `mcp.http_app()` to get a Starlette sub-application, then mounts it under `/{module_name}`. Since `http_app()` serves at `/mcp` by default, the full path becomes `/{module_name}/mcp`.
- ASGI lifespans from each sub-app are merged so all session managers initialise correctly within the single process.
- If a module fails to load, the error is logged and the remaining modules still start.

## Project Structure

```
mcp-server-multiplexer/
├── app.py               # Multiplexer entrypoint
├── mcp-modules.yaml     # List of module names to load
├── pyproject.toml       # uv/pip project config
├── uv.lock              # Locked dependency versions
├── client.py            # Test client for verifying the setup
├── hello/
│   ├── __init__.py
│   └── app.py           # FastMCP "Hello Server"
└── goodbye/
    ├── __init__.py
    └── app.py            # FastMCP "Goodbye Server"
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

## Getting Started

```bash
cd python/assistants/bundles/mcp-server-multiplexer

# Create isolated venv and install all dependencies
uv venv
uv sync

# Start the service
uv run python app.py
```

On startup you will see:

```
INFO:  Mounted MCP server: /hello/mcp
INFO:  Mounted MCP server: /goodbye/mcp
INFO:  ==================================================
INFO:  MCP Service started
INFO:    Health:  http://0.0.0.0:5032/health
INFO:    MCP:     http://0.0.0.0:5032/hello/mcp
INFO:    MCP:     http://0.0.0.0:5032/goodbye/mcp
INFO:  ==================================================
```

### Verifying with the Test Client

With the service running, open another terminal:

```bash
cd python/assistants/bundles/mcp-server-multiplexer
uv run python client.py
```

Expected output:

```
==================================================
Connecting to: Hello Server (http://localhost:5032/hello/mcp)
==================================================
Available tools: ['hello']
  hello('World') => Hello, World!

==================================================
Connecting to: Goodbye Server (http://localhost:5032/goodbye/mcp)
==================================================
Available tools: ['bye']
  bye('World') => Goodbye, World!
```

## Adding a New MCP Server

### Step 1: Create the Module

Create a new folder with an `__init__.py` and an `app.py`. The only requirement is that `app.py` exports a variable named `mcp` that is a `FastMCP` instance.

```bash
mkdir weather
touch weather/__init__.py
```

`weather/app.py`:

```python
from fastmcp import FastMCP

mcp = FastMCP("Weather Server")

@mcp.tool
def get_forecast(city: str) -> str:
    """Get the weather forecast for a city."""
    return f"Sunny, 22°C in {city}"

@mcp.tool
def get_alerts(region: str) -> str:
    """Get weather alerts for a region."""
    return f"No active alerts in {region}"
```

### Step 2: Register in the Config

Add the module name to `mcp-modules.yaml`:

```yaml
- hello
- goodbye
- weather
```

### Step 3: Restart

```bash
uv run python app.py
```

The new server is now available at `http://localhost:5032/weather/mcp`.

## Module Contract

Every module must follow this contract:

| Requirement | Detail |
|---|---|
| Folder | A Python package (directory with `__init__.py`) |
| Entry file | `app.py` inside the package |
| Export | A module-level variable named `mcp` of type `FastMCP` |
| Tools/Resources | Registered on the `mcp` instance via `@mcp.tool`, `@mcp.resource`, etc. |

The loader will skip any module that does not satisfy this contract and log an error with the full traceback.

## Configuration

| Constant | Default | Description |
|---|---|---|
| `CONFIG_FILE` | `mcp-modules.yaml` | Path to the YAML file listing modules |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5032` | Listen port |

These are defined at the top of `app.py` and can be changed there or overridden by extending `create_app()` to read from environment variables.

## Endpoints

| Path | Description |
|---|---|
| `/health` | Returns `{"status": "ok"}` — use for liveness probes |
| `/{module}/mcp` | Streamable HTTP MCP endpoint for the named module |

## Dependencies

Managed via `pyproject.toml` and locked in `uv.lock`:

| Package | Purpose |
|---|---|
| `fastmcp` | MCP server and client framework |
| `starlette` | ASGI framework for composing sub-apps |
| `uvicorn` | ASGI server |
| `pyyaml` | YAML config parsing |
