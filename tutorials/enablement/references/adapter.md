# Adapter

Talks to one thing outside the package. A service class calls it. It imports `contract` and the outside client. It does not import `app` or a sibling adapter.

```python
class SearchClient:
    """Typed calls to one external system."""

    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url

    def fetch(self, *, query: str) -> str:
        """Fetch one result for a query."""
        del query
        raise NotImplementedError
```

Replace `fetch` with the real call. For Unique APIs, take the client `unique_mcp` already builds (`get_unique_service_factory`) instead of a new SDK wrapper.
