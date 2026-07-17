"""Tests for deprecated streaming import redirect."""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest

from unique_toolkit._common.streaming_deprecation import (
    STREAMING_DEPRECATED_REMOVAL_DATE,
)


@pytest.mark.ai
def test_AI_deprecated_streaming_import_redirect__warns_and_reexports_symbols():
    """Deprecated experimental streaming imports resolve via import redirect.

    Purpose: Verify the MetaPathFinder keeps old import paths working.
    Why this matters: Callers can migrate gradually before the 2026-10-17 removal date.
    Setup summary: Fresh-import deprecated modules and assert warning plus symbol access.
    """
    import unique_toolkit.experimental  # noqa: F401 - installs redirect

    cases = [
        (
            "unique_toolkit.experimental._internal.streaming",
            "TextFlushed",
        ),
        (
            "unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.complete_with_references",
            "ResponsesCompleteWithReferences",
        ),
    ]

    for module_name, symbol in cases:
        parts = module_name.split(".")
        for index in range(len(parts), 2, -1):
            sys.modules.pop(".".join(parts[:index]), None)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            module = importlib.import_module(module_name)
            value = getattr(module, symbol)

        assert value is not None
        assert any(
            issubclass(w.category, DeprecationWarning)
            and STREAMING_DEPRECATED_REMOVAL_DATE in str(w.message)
            for w in caught
        ), f"Expected deprecation warning for {module_name}"
