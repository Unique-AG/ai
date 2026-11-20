# Service class

The object callers use. Public methods take keyword arguments only. Models inherit `contract.base.Model`.

An MCP or API constructs this class in `app.py` and keeps the behaviour here. A tool or a library puts this module at `src/<package>/service.py` and has no `app.py`.

```python
class Search:
    """Keyword-only service class. Callers use this."""

    def __init__(self, *, client: SearchClient) -> None:
        self._client = client

    def run(self, *, query: str) -> str:
        """Run one query."""
        return self._client.fetch(query=query)
```

`SearchClient` is an adapter. Read `adapter.md` when you add one. If this class only forwards to other service classes, it is a facade. Read `facade.md`.
