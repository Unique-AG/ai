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


@pytest.mark.ai
@pytest.mark.parametrize(
    ("deprecated_path", "stable_path", "symbol"),
    [
        (
            "unique_toolkit.experimental._internal.streaming",
            "unique_toolkit._internal.streaming",
            "TextFlushed",
        ),
        (
            "unique_toolkit.experimental._internal.streaming.pattern_replacer",
            "unique_toolkit._internal.streaming.pattern_replacer",
            "StreamingPatternReplacer",
        ),
        (
            "unique_toolkit.experimental.integrations.openai.streaming.event_routing",
            "unique_toolkit.integrations.openai.streaming.event_routing",
            "ResponsesCompleteWithReferences",
        ),
        (
            "unique_toolkit.experimental.integrations.openai.streaming.event_routing."
            "chat_completions.complete_with_references",
            "unique_toolkit.integrations.openai.streaming.event_routing."
            "chat_completions.complete_with_references",
            "ChatCompletionsCompleteWithReferences",
        ),
    ],
)
def test_AI_deprecated_streaming_import_identity__matches_stable_symbol(
    deprecated_path: str, stable_path: str, symbol: str
) -> None:
    """Deprecated nested imports must be the same object as the stable symbol.

    Purpose: Verify experimental shims re-export the stable class rather than
    loading a second copy via a copied package ``__path__``.
    Why this matters: Duplicate class objects break ``isinstance`` checks during
    the migration window.
    Setup summary: Import the same symbol from deprecated and stable paths and
    assert identity.
    """
    deprecated = importlib.import_module(deprecated_path)
    stable = importlib.import_module(stable_path)
    assert getattr(deprecated, symbol) is getattr(stable, symbol)
