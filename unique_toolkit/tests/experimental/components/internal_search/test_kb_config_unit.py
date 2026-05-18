"""Unit tests for KnowledgeBaseInternalSearchConfig.metadata_filter typing.

Covers:
- _parse_and_validate_uniqueql: None, empty string, valid dict, valid JSON string,
  invalid JSON string, invalid dict (non-UniqueQL), wrong type
- field_serializer: stored dict → JSON string, None → None
- JSON schema shape: anyOf [string, null], no $defs for UniqueQL types
- UI schema shape: anyOf with textarea on branch 0, no additionalProperties
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model
from unique_toolkit.experimental.components.internal_search.knowledge_base.config import (
    KnowledgeBaseInternalSearchConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_FILTER = {"operator": "equals", "value": "x", "path": ["fieldName"]}
_VALID_FILTER_JSON = json.dumps(_VALID_FILTER)
_ISNULL_FILTER = {"path": ["folderId"], "operator": "isNotNull", "value": ""}


# ---------------------------------------------------------------------------
# _parse_and_validate_uniqueql — via construction
# ---------------------------------------------------------------------------


class TestMetadataFilterParsing:
    def test_none_is_accepted(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=None)
        assert cfg.metadata_filter is None

    def test_empty_string_normalises_to_none(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter="")
        assert cfg.metadata_filter is None

    def test_whitespace_only_normalises_to_none(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter="   ")
        assert cfg.metadata_filter is None

    def test_valid_dict_is_stored_as_dict(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=_VALID_FILTER)
        assert cfg.metadata_filter == _VALID_FILTER
        assert isinstance(cfg.metadata_filter, dict)

    def test_valid_json_string_is_parsed_to_dict(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=_VALID_FILTER_JSON)
        assert cfg.metadata_filter == _VALID_FILTER
        assert isinstance(cfg.metadata_filter, dict)

    def test_isnull_operator_is_accepted(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=_ISNULL_FILTER)
        assert cfg.metadata_filter == _ISNULL_FILTER

    def test_invalid_json_string_raises(self):
        with pytest.raises(ValidationError, match="Invalid JSON"):
            KnowledgeBaseInternalSearchConfig(metadata_filter="not json")

    def test_invalid_dict_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseInternalSearchConfig(metadata_filter={"garbage": True})

    def test_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseInternalSearchConfig(metadata_filter=123)


# ---------------------------------------------------------------------------
# field_serializer — model_dump produces JSON string
# ---------------------------------------------------------------------------


class TestMetadataFilterSerializer:
    def test_dict_serialises_to_json_string(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=_VALID_FILTER)
        dumped = cfg.model_dump(mode="json")
        assert isinstance(dumped["metadata_filter"], str)
        assert json.loads(dumped["metadata_filter"]) == _VALID_FILTER

    def test_none_serialises_to_none(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=None)
        dumped = cfg.model_dump(mode="json")
        assert dumped["metadata_filter"] is None

    def test_empty_string_input_serialises_to_none(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter="")
        dumped = cfg.model_dump(mode="json")
        assert dumped["metadata_filter"] is None

    def test_json_string_input_round_trips_as_string(self):
        cfg = KnowledgeBaseInternalSearchConfig(metadata_filter=_VALID_FILTER_JSON)
        dumped = cfg.model_dump(mode="json")
        assert isinstance(dumped["metadata_filter"], str)
        assert json.loads(dumped["metadata_filter"]) == _VALID_FILTER


# ---------------------------------------------------------------------------
# JSON schema shape
# ---------------------------------------------------------------------------


class TestMetadataFilterJsonSchema:
    def setup_method(self):
        self.schema = KnowledgeBaseInternalSearchConfig.model_json_schema()
        self.mf = self.schema["properties"]["metadataFilter"]

    def test_anyof_has_string_and_null_branches(self):
        types = {b.get("type") for b in self.mf["anyOf"]}
        assert types == {"string", "null"}

    def test_no_defs_for_uniqueql_types(self):
        schema_str = json.dumps(self.mf)
        assert "Statement" not in schema_str
        assert "AndStatement" not in schema_str
        assert "OrStatement" not in schema_str

    def test_no_defs_at_field_level(self):
        assert "$defs" not in json.dumps(self.mf)

    def test_string_branch_has_title(self):
        string_branch = next(b for b in self.mf["anyOf"] if b.get("type") == "string")
        assert string_branch.get("title") == "UniqueQL (JSON)"

    def test_null_branch_has_deactivated_title(self):
        null_branch = next(b for b in self.mf["anyOf"] if b.get("type") == "null")
        assert null_branch.get("title") == "Deactivated"


# ---------------------------------------------------------------------------
# UI schema shape
# ---------------------------------------------------------------------------


class TestMetadataFilterUiSchema:
    def setup_method(self):
        self.ui = ui_schema_for_model(KnowledgeBaseInternalSearchConfig)
        self.mf_ui = self.ui["metadata_filter"]

    def test_no_additional_properties_at_field_level(self):
        assert "additionalProperties" not in self.mf_ui

    def test_no_widget_at_field_level(self):
        assert "ui:widget" not in self.mf_ui

    def test_anyof_has_two_branches(self):
        assert len(self.mf_ui["anyOf"]) == 2

    def test_string_branch_has_textarea_widget(self):
        string_branch = self.mf_ui["anyOf"][0]
        assert string_branch.get("ui:widget") == "textarea"

    def test_null_branch_is_empty(self):
        null_branch = self.mf_ui["anyOf"][1]
        assert null_branch == {}
