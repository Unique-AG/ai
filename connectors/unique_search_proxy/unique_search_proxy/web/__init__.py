"""FastAPI application layer (deployable service).

Not part of the HTTP SDK. Callers should use ``unique_search_proxy.sdk`` to talk
to this service over HTTP; they must not depend on ``web.core.client.HttpClientPool``
for tool execution.

Entrypoint: ``unique_search_proxy.web.app:create_app`` (or ``app``).
"""
