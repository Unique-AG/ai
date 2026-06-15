from __future__ import annotations

import base64
import json
from typing import Any


def json_safe_sdk_object(value: Any) -> Any:
    """Serialize agent-engine SDK models for JSON ``raw`` payloads.

    Plain ``model_dump()`` may include ``bytes`` (e.g. Google GenAI metadata)
    that break FastAPI response encoding. Prefer ``model_dump_json()`` or
    ``model_dump(mode="json")``.
    """
    dump_json = getattr(value, "model_dump_json", None)
    if callable(dump_json):
        return json.loads(dump_json())
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return _json_safe_value(value.model_dump())
    if hasattr(value, "as_dict"):
        return _json_safe_value(value.as_dict())
    return _json_safe_value(value)


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes_base64__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {key: _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    return value


__all__ = ["json_safe_sdk_object"]
