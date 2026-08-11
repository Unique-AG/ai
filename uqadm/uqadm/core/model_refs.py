"""Recursive find/replace of language-model references in config mappings.

Model names appear under many differently-named keys at arbitrary depth in
space/module/tool configurations and folder ingestion configs
(``languageModel``, ``fallbackLanguageModel``, ``hallucinationModel``, bare
``model`` / ``modelName``, …). A reference is rewritten only when BOTH hold:

1. the key name is model-bearing (ends in "model" / "model name" after
   camelCase/snake_case normalization) and is not in an explicit deny-set of
   known traps (``languageModelMaxInputTokens`` is an integer,
   ``allowModelSwitching`` / ``useOrchestratorLanguageModel`` are booleans);
2. the value matches the old model: a string equal to it, or a mapping whose
   ``name`` equals it (the ``LanguageModelInfo`` object form used for
   custom-provider models).

Prompt text, descriptions, and unrelated strings are untouched by construction.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

#: Keys that contain "model" but must never be rewritten (normalized form).
DENIED_MODEL_KEYS = frozenset(
    {
        "language_model_max_input_tokens",
        "allow_model_switching",
        "use_orchestrator_language_model",
        "model_switching",
    }
)

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_MODEL_KEY_RE = re.compile(r"(?:^|_)model(?:_name)?$")


@dataclass(frozen=True)
class ModelRef:
    """One matched model reference: dotted ``path`` and the old model name."""

    path: str
    value: str


def to_plain(node: Any) -> Any:
    """Return ``node`` rebuilt from plain ``dict`` / ``list`` containers.

    SDK payloads are ``unique_sdk`` ``UniqueObject`` instances — ``dict``
    subclasses whose ``__deepcopy__`` dereferences a ``user_id`` attribute that
    the SDK wipes when it refreshes an object from an API response, so
    ``copy.deepcopy`` raises on them. Rebuilding the structure sidesteps that
    and yields the independent copy the rewrite needs, with containers the API
    can serialize back.
    """
    if isinstance(node, Mapping):
        return {str(key): to_plain(value) for key, value in node.items()}
    if isinstance(node, (list, tuple)) or (
        isinstance(node, Sequence) and not isinstance(node, (str, bytes))
    ):
        return [to_plain(item) for item in node]
    return node


def _normalize_key(key: str) -> str:
    return _CAMEL_BOUNDARY_RE.sub("_", key).replace("-", "_").lower()


def is_model_key(key: str) -> bool:
    """Return True when ``key`` names a model reference (deny-set excluded)."""
    normalized = _normalize_key(key)
    if normalized in DENIED_MODEL_KEYS:
        return False
    return _MODEL_KEY_RE.search(normalized) is not None


def value_matches(value: Any, model_name: str) -> bool:
    """Return True when ``value`` references ``model_name``.

    Accepts the plain-string form (``"AZURE_GPT_4o_2024_0806"``) and the
    ``LanguageModelInfo`` object form (a mapping whose ``name`` matches).
    """
    if isinstance(value, str):
        return value == model_name
    if isinstance(value, dict):
        return value.get("name") == model_name
    return False


def _child_path(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _walk(
    node: Any,
    from_model: str,
    path: str,
    matches: list[ModelRef],
    *,
    to_value: str | dict[str, Any] | None,
    replace: bool,
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            child = _child_path(path, str(key))
            if is_model_key(str(key)) and value_matches(value, from_model):
                matches.append(ModelRef(path=child, value=from_model))
                if replace:
                    node[key] = to_plain(to_value)
            else:
                _walk(
                    value,
                    from_model,
                    child,
                    matches,
                    to_value=to_value,
                    replace=replace,
                )
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk(
                item,
                from_model,
                f"{path}[{index}]",
                matches,
                to_value=to_value,
                replace=replace,
            )


def find_model_refs(node: Any, from_model: str) -> list[ModelRef]:
    """Collect every model reference to ``from_model`` without modifying ``node``."""
    matches: list[ModelRef] = []
    _walk(node, from_model, "", matches, to_value=None, replace=False)
    return matches


def replace_model_refs(
    node: Any,
    from_model: str,
    to_value: str | dict[str, Any],
) -> tuple[Any, list[ModelRef]]:
    """Return a rewritten copy of ``node`` with ``from_model`` references replaced.

    ``to_value`` is written at each matched site: a model name string, or a
    full model-info mapping (copied per site so they stay independent).

    ``node`` itself is never mutated. The copy is rebuilt from plain ``dict`` /
    ``list`` containers (see :func:`to_plain`), so live SDK payloads are safe to
    pass in and the result is safe to send back to the API.
    """
    new_node = to_plain(node)
    matches: list[ModelRef] = []
    _walk(new_node, from_model, "", matches, to_value=to_value, replace=True)
    return new_node, matches


_PATH_PART_RE = re.compile(r"^([^\[\]]+)((?:\[\d+\])*)$")
_PATH_INDEX_RE = re.compile(r"\[(\d+)\]")

#: Sentinel returned by :func:`get_at_path` when the path does not resolve.
MISSING: Any = object()


def get_at_path(node: Any, path: str) -> Any:
    """Resolve a dotted ``ModelRef.path`` in ``node``; ``MISSING`` if absent."""
    current = node
    for part in path.split("."):
        match = _PATH_PART_RE.match(part)
        if match is None:
            return MISSING
        key = match.group(1)
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
        for raw_index in _PATH_INDEX_RE.findall(match.group(2)):
            index = int(raw_index)
            if not isinstance(current, list) or index >= len(current):
                return MISSING
            current = current[index]
    return current
