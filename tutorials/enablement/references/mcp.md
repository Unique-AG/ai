# MCP

Read the `unique_mcp` README sections "Usage" and "Platform helpers (logging + metrics)" before writing auth, settings, or metrics. Call those functions. Do not reimplement them.

`app.py` is the composition root. It starts the process. A tool calls a service class that lives outside `app.py`. Read `service.md` before writing that class. Read `adapter.md` when the class talks to something outside the package. Read `facade.md` when one object only forwards to other service classes.

```python
from fastmcp import FastMCP
from unique_mcp.logging import configure_logging
from unique_mcp.monitoring import setup_ops


def main() -> None:
    """Start the MCP server with pino-json logs, health, and Prometheus."""
    configure_logging()
    mcp = FastMCP("package-name")
    mcp.run(transport="http", middleware=[setup_ops(mcp)])
```

Call `unique_toolkit.monitoring.configure_tracing(service_name=...)` only when this server exports traces.

A tool that calls Unique takes `UniqueSettings` from `get_unique_settings` or `get_unique_settings_async` (`fastmcp.dependencies.Depends`) and passes it into the service class as a keyword argument. Profile fields come from `get_unique_userinfo`. A `UniqueServiceFactory` comes from `get_unique_service_factory`. Auth wiring is `create_zitadel_oauth_proxy` in the `unique_mcp` README, not a new OAuth proxy.
