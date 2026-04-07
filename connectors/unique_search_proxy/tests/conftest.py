from __future__ import annotations

import sys
from pathlib import Path

_web = Path(__file__).resolve().parent.parent / "web"
if _web.is_dir() and str(_web) not in sys.path:
    sys.path.insert(0, str(_web))

import pytest  # noqa: E402


@pytest.fixture
def google_search_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-api-key")
    monkeypatch.setenv("GOOGLE_SEARCH_API_ENDPOINT", "https://example.com/search")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-engine-id")
