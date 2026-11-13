# API

`app.py` is the composition root. It builds the FastAPI app and runs it. Behaviour lives in a service class outside `app.py`. Read `service.md` before writing that class.

```python
import uvicorn
from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build the API. Wire metrics and traces here only when this API has them."""
    return FastAPI()


def main() -> None:
    """Run the API process."""
    uvicorn.run("package_name.app:create_app", factory=True, host="127.0.0.1", port=8000)
```

`uvicorn.run` with `factory=True` calls `create_app`. Add `fastapi` and `uvicorn` to the project dependencies.

Metrics: `unique_toolkit.monitoring.MetricNamespace` and the `monitoring` extra. Traces: `unique_toolkit.monitoring.configure_tracing` and the `otel` extra, only when this process should export them. Do not call `unique_mcp`'s logger. There is no shared log format for an API.
