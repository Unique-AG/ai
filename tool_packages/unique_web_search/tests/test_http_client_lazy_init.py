"""HTTP client module must stay lazy — no egress client at import time."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.ai
def test_http_client_module_does_not_init_registry_on_import() -> None:
    module = importlib.import_module("unique_web_search.services.client.http_client")
    module = importlib.reload(module)

    assert module._registry is None
    assert not hasattr(module, "async_client")
