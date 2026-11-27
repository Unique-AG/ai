"""Tests for the stable streaming import paths and their deprecated redirect."""

from __future__ import annotations

import importlib
import subprocess
import sys
import warnings

import pytest

import unique_toolkit.experimental as experimental  # installs the redirect

_REMOVAL_DATE = experimental._STREAMING_DEPRECATED_REMOVAL_DATE

_OLD_INTERNAL = "unique_toolkit.experimental._internal.streaming"
_NEW_INTERNAL = "unique_toolkit._internal.streaming"
_OLD_OPENAI = "unique_toolkit.experimental.integrations.openai.streaming"
_NEW_OPENAI = "unique_toolkit.integrations.openai.streaming"

# (deprecated module, stable module, symbol both must expose as the same object)
_REDIRECTED_MODULES = [
    (_OLD_INTERNAL, _NEW_INTERNAL, "TextFlushed"),
    (
        f"{_OLD_INTERNAL}.pattern_replacer",
        f"{_NEW_INTERNAL}.pattern_replacer",
        "normalize_citations_to_brackets",
    ),
    (
        f"{_OLD_OPENAI}.event_routing._async_bridge",
        f"{_NEW_OPENAI}.event_routing._async_bridge",
        "run_async_from_sync",
    ),
    (
        f"{_OLD_OPENAI}.event_routing.responses.complete_with_references",
        f"{_NEW_OPENAI}.event_routing.responses.complete_with_references",
        "ResponsesCompleteWithReferences",
    ),
    (
        f"{_OLD_OPENAI}.event_routing.chat_completions.complete_with_references",
        f"{_NEW_OPENAI}.event_routing.chat_completions.complete_with_references",
        "ChatCompletionsCompleteWithReferences",
    ),
]


def _forget_deprecated_modules(old_prefix: str) -> None:
    """Drop a deprecated module tree so the next import runs the redirect again."""
    for name in [
        name
        for name in sys.modules
        if name == old_prefix or name.startswith(f"{old_prefix}.")
    ]:
        del sys.modules[name]


def _import_with_warnings(
    module_name: str,
) -> tuple[object, list[warnings.WarningMessage]]:
    old_prefix = _OLD_INTERNAL if module_name.startswith(_OLD_INTERNAL) else _OLD_OPENAI
    _forget_deprecated_modules(old_prefix)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        # The builtin adds no Python frame, so the warning is attributed to this
        # file exactly as for an `import` statement in user code.
        __import__(module_name)
    module = sys.modules[module_name]
    return module, [w for w in caught if issubclass(w.category, DeprecationWarning)]


_STABLE_MODULES = [
    _NEW_INTERNAL,
    f"{_NEW_INTERNAL}.pattern_replacer",
    _NEW_OPENAI,
    f"{_NEW_OPENAI}.event_routing",
    f"{_NEW_OPENAI}.event_routing.responses.complete_with_references",
    f"{_NEW_OPENAI}.event_routing.chat_completions.complete_with_references",
    f"{_NEW_OPENAI}.event_routing._model_params",
]


@pytest.mark.ai
def test_stable_streaming_imports__resolve_without_warning() -> None:
    """
    Purpose: Verify the graduated streaming modules import from their stable paths.
    Why this matters: Callers migrating off `unique_toolkit.experimental` must not
        be nagged by a deprecation warning on the path they were told to use.
    Setup summary: Import every stable module in a fresh interpreter (other tests
        have already cached them in this one) with the redirect's warning turned
        into an error.
    """
    code = "import importlib\n" + "".join(
        f"importlib.import_module({name!r})\n" for name in _STABLE_MODULES
    )

    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error:Importing from 'unique_toolkit.experimental:DeprecationWarning",
            "-c",
            code,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.ai
@pytest.mark.parametrize(("old_name", "new_name", "symbol"), _REDIRECTED_MODULES)
def test_deprecated_streaming_import__warns_and_reexports_same_symbols(
    old_name: str, new_name: str, symbol: str
) -> None:
    """
    Purpose: Verify deprecated experimental streaming paths still resolve and warn.
    Why this matters: Callers can migrate gradually while the redirect remains.
    Setup summary: Fresh-import the deprecated module; assert the warning, that
        the symbol is the very same object as on the stable module (no second copy)
        and that `__package__` lets relative imports resolve under the old name.
    """
    old_module, deprecations = _import_with_warnings(old_name)
    new_module = importlib.import_module(new_name)

    assert any(
        old_name in str(w.message) and new_name in str(w.message) for w in deprecations
    ), f"Expected a deprecation warning naming {old_name} and {new_name}"
    assert getattr(old_module, symbol) is getattr(new_module, symbol)
    # A package is its own `__package__`; a plain module's is its parent.
    expected_package = (
        old_name if hasattr(new_module, "__path__") else old_name.rpartition(".")[0]
    )
    assert old_module.__package__ == expected_package


@pytest.mark.ai
def test_deprecated_streaming_import__warning_points_at_the_importer() -> None:
    """
    Purpose: Verify the DeprecationWarning is attributed to the importing code.
    Why this matters: Python only shows DeprecationWarning by default when it is
        attributed to `__main__`; attributing it to the toolkit's own redirect
        module would hide it from every user outside of pytest.
    Setup summary: Import a deprecated module from this test and check the
        warning's filename is this file, not the redirect helper.
    """
    _, deprecations = _import_with_warnings(f"{_OLD_INTERNAL}.common")

    assert deprecations
    assert {w.filename for w in deprecations} == {__file__}


@pytest.mark.ai
def test_deprecated_streaming_import__message_states_removal_date() -> None:
    """
    Purpose: Verify the warning tells callers when the old path goes away.
    Why this matters: The date in the message is the only migration deadline
        users see, so it must match the registered redirect.
    Setup summary: Import a deprecated module and look for the date in the message.
    """
    _, deprecations = _import_with_warnings(_OLD_INTERNAL)

    assert any(_REMOVAL_DATE in str(w.message) for w in deprecations)
