from __future__ import annotations

import pytest

from unique_mcp.internal_search.meta import InternalSearchRequestMeta
from unique_mcp.meta_keys import MetaKeys


@pytest.mark.ai
def test_request_meta__allows_extra_fields():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.CHAT_ID: "chat-1",
            MetaKeys.CONTENT_IDS: ["c1"],
            "custom.extra": "kept",
        }
    )

    assert meta.chat_id == "chat-1"
    assert meta.content_ids == ["c1"]
    assert meta.model_extra == {"custom.extra": "kept"}


@pytest.mark.ai
def test_request_meta__accepts_namespaced_keys():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.USER_ID: "user-1",
            MetaKeys.COMPANY_ID: "company-1",
            MetaKeys.CHAT_ID: "chat-1",
            MetaKeys.USER_MESSAGE_ID: "um-1",
            MetaKeys.CONTENT_IDS: ["c1", "c2"],
            MetaKeys.METADATA_FILTER: {"kind": "report"},
            MetaKeys.LANGUAGE_MODEL_MAX_INPUT_TOKENS: 128000,
        }
    )

    assert meta.user_id == "user-1"
    assert meta.company_id == "company-1"
    assert meta.chat_id == "chat-1"
    assert meta.last_user_message_id == "um-1"
    assert meta.content_ids == ["c1", "c2"]
    assert meta.metadata_filter == {"kind": "report"}
    assert meta.language_model_max_input_tokens == 128000


@pytest.mark.ai
def test_request_meta__accepts_flat_camel_case_aliases():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            "userId": "user-1",
            "companyId": "company-1",
            "chatId": "chat-1",
            "messageId": "um-1",
        }
    )

    assert meta.user_id == "user-1"
    assert meta.company_id == "company-1"
    assert meta.chat_id == "chat-1"
    assert meta.last_user_message_id == "um-1"


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
