"""Base class for LLM-facing parameter models.

``BaseSearchEngineConfig.exposed_params_model()`` returns a subclass of
:class:`ExposedParams` containing exactly the admin-exposed knobs. Tool-parameter
models graft those knobs on by ordinary inheritance::

    Exposed = config.exposed_params_model()
    class ToolParams(ToolParamsBase, Exposed): ...
    # or: create_model("ToolParams", __base__=(ToolParamsBase, Exposed))

The exposed field names are simply ``Exposed.model_fields`` — no stamped class
attributes, no field-definition plumbing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from unique_search_proxy_core.schema import camelized_model_config

# Schema-object maps whose *keys* are arbitrary user names (field names, $defs
# names). The noise-stripping walk must recurse into their values but never pop
# keys at the map level, or a field literally named "title" would be deleted.
_NAME_KEYED_MAPS = ("properties", "$defs", "definitions")


def _strip_llm_schema_noise(node: Any) -> None:
    """Remove ``title`` and ``default`` from every schema object, in place.

    LLM tool manifests treat both as noise: Pydantic auto-generates a ``title``
    per field/model, and ``"default": null`` (or an admin default) must not leak
    into what the model sees. Defaults are merged server-side at search time.
    """
    if isinstance(node, dict):
        node.pop("title", None)
        node.pop("default", None)
        for key, value in node.items():
            if key in _NAME_KEYED_MAPS and isinstance(value, dict):
                for sub_schema in value.values():
                    _strip_llm_schema_noise(sub_schema)
            else:
                _strip_llm_schema_noise(value)
    elif isinstance(node, list):
        for item in node:
            _strip_llm_schema_noise(item)


class ExposedParams(BaseModel):
    """Base for LLM-facing parameter models (camelCase aliases, populate_by_name).

    The single JSON-schema concern of the exposable-parameter feature lives
    here: ``model_json_schema`` strips ``title``/``default`` noise from the
    rendered schema. The override is inherited by any tool-parameter model that
    subclasses an ``exposed_params_model()`` result, so the combined tool schema
    is clean without markers or post-processing pipelines.
    """

    model_config = camelized_model_config

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        schema = super().model_json_schema(*args, **kwargs)
        _strip_llm_schema_noise(schema)
        return schema
