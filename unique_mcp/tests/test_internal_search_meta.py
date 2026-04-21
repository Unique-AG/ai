from __future__ import annotations

import pytest

from unique_mcp.internal_search.meta import InternalSearchRequestMeta
from unique_mcp.meta_keys import MetaKeys


@pytest.mark.ai
def test_request_meta__parses_search_scoping_keys():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.CONTENT_IDS: ["c1", "c2"],
            MetaKeys.METADATA_FILTER: {"kind": "report"},
            MetaKeys.LANGUAGE_MODEL_MAX_INPUT_TOKENS: 128000,
        }
    )

    assert meta.content_ids == ["c1", "c2"]
    assert meta.metadata_filter == {"kind": "report"}
    assert meta.language_model_max_input_tokens == 128000


@pytest.mark.ai
def test_request_meta__ignores_unknown_and_identity_keys():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.CONTENT_IDS: ["c1"],
            MetaKeys.USER_ID: "user-1",  # identity — handled by get_unique_settings
            MetaKeys.CHAT_ID: "chat-1",  # identity — handled by get_unique_settings
            "custom.extra": "ignored",
        }
    )

    assert meta.content_ids == ["c1"]
    assert meta.model_extra is None


@pytest.mark.ai
def test_chat_content_ids_prefers_selected_uploaded_file_ids():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.SELECTED_UPLOADED_FILE_IDS: ["f1"],
            MetaKeys.CONTENT_IDS: ["c1"],
        }
    )

    assert meta.chat_content_ids == ["f1"]
    assert meta.knowledge_base_content_ids == ["c1"]


@pytest.mark.ai
def test_chat_content_ids_empty_list_does_not_fall_back_to_content_ids():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.SELECTED_UPLOADED_FILE_IDS: [],
            MetaKeys.CONTENT_IDS: ["c1"],
        }
    )

    assert meta.chat_content_ids == []
