"""Tests for deprecated streaming import path shims."""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest

from unique_toolkit._common.streaming_deprecation import (
    STREAMING_DEPRECATED_REMOVAL_DATE,
)


@pytest.mark.ai
def test_AI_deprecated_streaming_import_shims__emit_warning_and_reexport_symbols():
    """Deprecated experimental streaming imports still resolve with a warning.

    Purpose: Verify backward-compatible shims re-export stable streaming symbols.
    Why this matters: External callers may still import from experimental paths until
    the 2026-10-17 removal date.
    Setup summary: Import via deprecated paths under warnings capture; assert symbols
    and removal date appear in the warning message.
    """
    cases = [
        (
            "unique_toolkit.experimental._internal.streaming",
            "TextFlushed",
        ),
        (
            "unique_toolkit.experimental.integrations.openai.streaming.event_routing",
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
        assert len(caught) >= 1
        assert any(
            issubclass(w.category, DeprecationWarning)
            and STREAMING_DEPRECATED_REMOVAL_DATE in str(w.message)
            for w in caught
        ), f"Expected deprecation warning for {module_name}"
