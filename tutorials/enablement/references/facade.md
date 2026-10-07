# Facade

One object that forwards to other service classes and adds no logic. Callers use the same keyword-only shape as a service class.

```python
class Search:
    """Forwards to the service classes it holds."""

    def __init__(self, *, documents: DocumentSearch, web: WebSearch) -> None:
        self._documents = documents
        self._web = web

    def documents_for(self, *, query: str) -> str:
        """Forward one document query."""
        return self._documents.run(query=query)
```

A method that fans out, retries, or combines results is a service class. Read `service.md` and put that logic there.
